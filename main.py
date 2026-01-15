import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from data_loader import load_data
from strategy import SectorStrategy
from backtest import Backtest
import os
from datetime import datetime, timedelta

def main():
    # 1. Load Data
    print("Loading data...")
    sectors = load_data("sectors.csv")
    benchmark = load_data("benchmark.csv")
    macro = load_data("macro.csv")
    
    if sectors is None or benchmark is None:
        print("Error: content could not be loaded. Please run data_loader.py first.")
        return

    # Handle MultiIndex
    def clean_data(df):
        if isinstance(df.columns, pd.MultiIndex):
            try:
                return df.xs('Close', axis=1, level=0)
            except KeyError:
                try:
                    return df.xs('Adj Close', axis=1, level=0)
                except KeyError:
                    return df
        return df

    sectors = clean_data(sectors)
    benchmark = clean_data(benchmark)
    macro = clean_data(macro)
    
    # Ensure benchmark is series if needed
    if isinstance(benchmark, pd.DataFrame) and benchmark.shape[1] > 0:
        benchmark = benchmark.iloc[:, 0]

    # Align dates (Pre-strategy)
    # We need full history for strategy calculation
    common_index = sectors.index.intersection(benchmark.index)
    sectors = sectors.loc[common_index]
    benchmark = benchmark.loc[common_index]
    
    # 2. Run Strategy (Full History)
    print("Running strategy (calculating factors on full history)...")
    strategy = SectorStrategy(sectors, macro_data=macro, top_k=5)
    weights = strategy.get_signal_df()
    
    # 3. Slice for Backtest (Last 5 Years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    print(f"Backtesting Period: {start_date.date()} to {end_date.date()}")
    
    # Filter using string slicing or timestamp comparison
    mask = (weights.index >= start_date) & (weights.index <= end_date)
    bt_weights = weights.loc[mask]
    bt_prices = sectors.loc[mask]
    bt_benchmark = benchmark.loc[mask]
    
    # 3. Run Backtest
    print("Running backtest...")
    bt = Backtest(bt_prices, bt_weights, benchmark_prices=bt_benchmark)
    port_returns, equity_curve = bt.run()
    report = bt.generate_report()
    
    # 4. Reporting & Visualization
    print("\nPerformance Report:")
    print(report)
    
    # Plot Cumulative Returns
    plt.figure(figsize=(12, 6))
    
    if not equity_curve.empty:
        # Re-align benchmark for plotting
        bench_rets = bt_benchmark.pct_change().dropna()
        # Ensure alignment
        common_idx = equity_curve.index.intersection(bench_rets.index)
        equity_curve = equity_curve.loc[common_idx]
        bench_rets = bench_rets.loc[common_idx]
        
        bench_cum_rets = (1 + bench_rets).cumprod()
        bench_equity = bench_cum_rets * bt.initial_capital
        
        plt.plot(equity_curve, label='Multi-Factor Rotation (Top 5)')
        plt.plot(bench_equity, label='Benchmark (Nifty 50)', alpha=0.7)
        
        plt.title('Sector Rotation Strategy (Modified) vs Benchmark')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.legend()
        plt.grid(True)
        
        output_file = "performance_plot_v2.png"
        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")
    else:
        print("Equity curve is empty.")

if __name__ == "__main__":
    main()
