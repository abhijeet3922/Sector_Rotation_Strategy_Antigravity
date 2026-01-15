import pandas as pd
import numpy as np

class Backtest:
    def __init__(self, prices, weights, benchmark_prices=None, initial_capital=100000):
        """
        prices: DataFrame of asset prices.
        weights: DataFrame of asset weights (same index as prices).
        benchmark_prices: Series/DataFrame of benchmark prices.
        """
        self.prices = prices
        self.weights = weights
        self.benchmark_prices = benchmark_prices
        self.initial_capital = initial_capital
        
        # Align indices
        common_index = self.prices.index.intersection(self.weights.index)
        self.prices = self.prices.loc[common_index]
        self.weights = self.weights.loc[common_index]
        
        if self.benchmark_prices is not None:
             self.benchmark_prices = self.benchmark_prices.loc[self.benchmark_prices.index.intersection(common_index)]

    def run(self):
        """
        Calculates portfolio returns.
        """
        # Daily returns of assets
        asset_returns = self.prices.pct_change()
        
        # Portfolio return = sum(weight * asset_return)
        # Using self.weights.shift(1) if we assume weights are determined at close of T, active T+1
        # But strategy.py already shifted the weights, so we use them as is (assuming they align with the day they are active).
        # Let's verify: strategy.py says "weights reindexed to daily... and shift(1)".
        # So weights at index T are the weights to be held for day T return.
        
        self.portfolio_returns = (self.weights * asset_returns).sum(axis=1)
        
        # Calculate Equity Curve
        self.equity_curve = (1 + self.portfolio_returns).cumprod() * self.initial_capital
        
        return self.portfolio_returns, self.equity_curve

    def calculate_metrics(self, returns):
        """
        Calculates performance metrics.
        """
        # Annualized Return
        days = len(returns)
        if days < 1: return {}
        
        total_return = (returns + 1).prod() - 1
        annualized_return = (1 + total_return) ** (252 / days) - 1
        
        # Annualized Volatility
        annualized_vol = returns.std() * np.sqrt(252)
        
        # Sharpe Ratio (assuming 0 risk-free rate for simplicity, or 6% roughly)
        rf = 0.06
        daily_rf = (1 + rf) ** (1/252) - 1
        sharpe = (returns.mean() - daily_rf) / returns.std() * np.sqrt(252)
        
        # Max Drawdown
        cum_returns = (1 + returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        max_drawdown = drawdown.min()
        
        return {
            "Total Return": total_return,
            "Annualized Return": annualized_return,
            "Volatility": annualized_vol,
            "Sharpe Ratio": sharpe,
            "Max Drawdown": max_drawdown
        }

    def get_benchmark_returns(self):
        if self.benchmark_prices is None:
            return None
        return self.benchmark_prices.pct_change()

    def generate_report(self):
        port_metrics = self.calculate_metrics(self.portfolio_returns)
        
        report = pd.DataFrame(port_metrics, index=["Strategy"]).T
        
        if self.benchmark_prices is not None:
            bench_rets = self.get_benchmark_returns()
            # Handle if benchmark is DataFrame
            if isinstance(bench_rets, pd.DataFrame):
                 bench_rets = bench_rets.iloc[:, 0]
                 
            bench_metrics = self.calculate_metrics(bench_rets)
            report["Benchmark"] = pd.Series(bench_metrics)
            
        return report
