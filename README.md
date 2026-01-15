# Sector Rotation Strategy Implementation Plan (v2)

## Goal Description
Enhance the sector rotation strategy to invest in at least 5 sectors, incorporating RSI and Macro factors to improve risk-adjusted returns. Backtest period is strictly the last 5 years.

## User Review Required
> [!NOTE]
> **Data & Factors**: "Valuation" (P/E) is difficult to source correctly. I will use **RSI** (Relative Strength Index) as a mean-reversion/timing factor and **Macro Correlation** (e.g., USDINR trend for IT/Pharma) as a "Macro" factor.

## Proposed Changes

### Data Loader (`data_loader.py`)
- Ensure data fetch start date allows for warmup (e.g., start 2019).

### Strategy Logic (`strategy.py`)
- **Universe**: 6 Sectors.
- **Selection**: Select top 5 sectors.
- **Factors**:
    1. **Valuation (Proxy)**: 
        - Since historical P/E is unavailable, use **Price vs 5-Year SMA**.
        - Logic: If Current Price < 5-Year SMA, Sector is "Undervalued".
        - Implementation: Calculate Z-score of (Price - 5ySMA). Lower is better (more value).
    2. **Momentum**: 12-month return.
    3. **Volatility**: 6-month vol.
    4. **RSI**: 14-day RSI (check for < 70).
    5. **Macro**: USDINR / Crude regime.
- **Weighting**: Multi-Factor Score:
    - `Score = 0.3 * Momentum + 0.3 * Valuation_Score + 0.2 * RSI_Score + 0.2 * Volatility_Score`

### Backtest Engine (`main.py`)
- Set start date strictly to 5 years ago from today.

## Verification Plan

### Automated Tests
- Run `main.py` and check the "Performance Report".
- Verify that `Strategy` invests in ~5 assets (check logs).

### Manual Verification
- Review the plot.
- Ensure the start date of the curve is exactly 5 years ago.
