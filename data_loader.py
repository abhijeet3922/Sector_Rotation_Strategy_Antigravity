import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

DATA_DIR = "data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

SECTORS = {
    "Bank": "^NSEBANK",
    "IT": "^CNXIT",
    "FMCG": "^CNXFMCG",
    "Auto": "^CNXAUTO",
    "Pharma": "^CNXPHARMA",
    "Metal": "^CNXMETAL"
}

BENCHMARK = {
    "Nifty50": "^NSEI"
}

MACRO = {
    "USDINR": "INR=X",
    "CrudeOil": "CL=F"
}

def fetch_data(tickers, start_date, end_date):
    """
    Fetches historical data for a list of tickers.
    """
    print(f"Fetching data for {tickers}...")
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
        # If multiple tickers, 'Close' is a MultiIndex. We want just Close prices if possible, 
        # but for strategy we might need Open/High/Low too.
        # For now, let's keep all data but typically we operate on Close.
        
        # yfinance return structure varies by number of tickers. 
        # If >1 ticker, columns are (Attribute, Ticker).
        # We'll handle this in strategy.
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def save_data(data, filename):
    """
    Saves dataframe to CSV.
    """
    filepath = os.path.join(DATA_DIR, filename)
    data.to_csv(filepath)
    print(f"Data saved to {filepath}")

def load_data(filename):
    """
    Loads data from CSV.
    """
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        # Check if it's likely a multi-ticker file (sectors or macro)
        is_multi = "sectors" in filename or "macro" in filename
        return pd.read_csv(filepath, header=[0, 1] if is_multi else 0, index_col=0, parse_dates=True)
    return None

def fetch_all_data(start_date=None, end_date=None, force_refresh=False):
    """
    Orchestrates fetching of all required data.
    """
    if start_date is None:
        # Need 5 years for backtest + 5 years for SMA warmup + buffer -> ~12 years
        start_date = (datetime.now() - timedelta(days=12*365)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # 1. Benchmark
    bench_file = "benchmark.csv"
    if not os.path.exists(os.path.join(DATA_DIR, bench_file)) or force_refresh:
        bench_data = fetch_data(list(BENCHMARK.values()), start_date, end_date)
        if bench_data is not None and not bench_data.empty:
             # Dropping multi-level column if single ticker
             if isinstance(bench_data.columns, pd.MultiIndex):
                 bench_data = bench_data.xs(list(BENCHMARK.values())[0], axis=1, level=1)
             save_data(bench_data, bench_file)
    
    # 2. Sectors
    sectors_file = "sectors.csv"
    if not os.path.exists(os.path.join(DATA_DIR, sectors_file)) or force_refresh:
        # yfinance download allows list
        sector_tickers = list(SECTORS.values())
        sector_data = fetch_data(sector_tickers, start_date, end_date)
        if sector_data is not None and not sector_data.empty:
            save_data(sector_data, sectors_file)

    # 3. Macro
    macro_file = "macro.csv"
    if not os.path.exists(os.path.join(DATA_DIR, macro_file)) or force_refresh:
        macro_tickers = list(MACRO.values())
        macro_data = fetch_data(macro_tickers, start_date, end_date)
        if macro_data is not None and not macro_data.empty:
            save_data(macro_data, macro_file)

if __name__ == "__main__":
    fetch_all_data(force_refresh=True)
