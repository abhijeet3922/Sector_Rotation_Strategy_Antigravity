import pandas as pd
import numpy as np

class SectorStrategy:
    def __init__(self, prices, macro_data=None, top_k=5):
        """
        prices: DataFrame of sector close prices.
        macro_data: DataFrame of macro indicators (USDINR, CrudeOil).
        top_k: Number of top sectors to select.
        """
        self.prices = prices.ffill() # Forward fill to handle occasional NaNs in rolling window
        self.macro_data = macro_data
        self.top_k = top_k
        self.momentum_period = 252
        self.volatility_period = 126
        self.rsi_period = 14
        self.value_period = 252 * 5 # 5 Years

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-6)
        return 100 - (100 / (1 + rs))

    def calculate_factors(self):
        # 1. Momentum (12m return)
        momentum = self.prices.pct_change(self.momentum_period)
        
        # 2. Volatility (6m std dev)
        daily_rets = self.prices.pct_change()
        volatility = daily_rets.rolling(self.volatility_period).std()
        
        # 3. RSI (14d) - Lower is better (oversold) or Higher is better?
        # Typically for momentum strategy, RSI > 50 is good, but > 70 is overbought.
        # User asked for "Sector RSI". Let's use it as a momentum confirmation (Higher is better up to a point).
        # Or let's treat it as a mean-reversion factor: heavily overbought (>80) is bad, oversold (<30) is good?
        # Given "Sector Rotation" is usually trend-following, let's treat RSI as Momentum. Higher is better.
        rsi = self.prices.apply(lambda x: self.calculate_rsi(x, self.rsi_period))
        
        # 4. Value Proxy (Price vs 5y SMA)
        sma5y = self.prices.rolling(self.value_period).mean()
        value_proxy = (self.prices - sma5y) / (sma5y + 1e-6)
        
        return momentum, volatility, rsi, value_proxy

    def get_macro_regime(self):
        """
        Returns a DataFrame of regime multipliers or additives.
        """
        if self.macro_data is None:
            return None
        
        # Align macro to prices
        macro = self.macro_data.reindex(self.prices.index).ffill()
        
        # USDINR Trend (50 DMA)
        usd = macro.xs('INR=X', axis=1, level=1) if isinstance(macro.columns, pd.MultiIndex) else macro['INR=X']
        usd_ma = usd.rolling(50).mean()
        rupee_weak = usd > usd_ma # Good for IT, Pharma
        
        # Crude Trend (50 DMA)
        crude = macro.xs('CL=F', axis=1, level=1) if isinstance(macro.columns, pd.MultiIndex) else macro['CL=F']
        crude_ma = crude.rolling(50).mean()
        oil_high = crude > crude_ma # Bad for Auto, Paints (FMCG proxy sometimes)
        
        regime = pd.DataFrame(0.0, index=self.prices.index, columns=self.prices.columns)
        
        # Mapping tickers to sectors logic
        # IT: concept check if columns contain 'IT'
        it_col = [c for c in self.prices.columns if 'IT' in c]
        pharma_col = [c for c in self.prices.columns if 'PHARMA' in c]
        auto_col = [c for c in self.prices.columns if 'AUTO' in c]
        
        # Apply Boosts/Penalties to SCORE
        # If Rupee Weak: Boost IT, Pharma
        if it_col: regime.loc[rupee_weak, it_col] += 0.5
        if pharma_col: regime.loc[rupee_weak, pharma_col] += 0.5
        
        # If Oil High: Penalize Auto
        if auto_col: regime.loc[oil_high, auto_col] -= 0.5
        
        return regime

    def compute_scores(self):
        mom, vol, rsi, val = self.calculate_factors()
        
        # Normalize factors (Z-Score across sectors for each day)
        def zscore(df):
            return (df.sub(df.mean(axis=1), axis=0)).div(df.std(axis=1) + 1e-6, axis=0)
        
        z_mom = zscore(mom)
        z_vol = zscore(vol)
        z_rsi = zscore(rsi)
        z_val = zscore(val)
        
        # Composite Score
        # Strategy: High Momentum, Low Volatility, Low Value-Proxy (Undervalued), High RSI (Trend)
        # Weights: Mom 30%, Val 30%, RSI 20%, Vol 20%
        # Note: z_vol should be inverted (Lower vol is good -> Higher Score). z_val inverted (Lower Price/SMA is good).
        
        score = (0.3 * z_mom) + (0.3 * -z_val) + (0.2 * z_rsi) + (0.2 * -z_vol)
        
        # Add Macro Overlay
        macro_boost = self.get_macro_regime()
        if macro_boost is not None:
            score += macro_boost
            
        return score

    def get_signal_df(self):
        scores = self.compute_scores()
        
        # Monthly Rebalance
        monthly_scores = scores.resample('ME').last() # Using 'ME' as requested
        
        weights = pd.DataFrame(0.0, index=monthly_scores.index, columns=self.prices.columns)
        
        for date, row in monthly_scores.iterrows():
            valid_scores = row.dropna()
            if len(valid_scores) < self.top_k:
                continue
                
            # Top K
            top_sectors = valid_scores.nlargest(self.top_k).index
            
            # Equal Weight
            w = 1.0 / self.top_k
            weights.loc[date, top_sectors] = w
            
        # Daily weights
        daily_weights = weights.reindex(self.prices.index).ffill().shift(1).fillna(0)
        return daily_weights
