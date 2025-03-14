import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import plotly.express as px
import pandas as pd

# -----------------------
# 1) HELPER FUNCTIONS
# -----------------------
def ema(series: pd.Series, length: int) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA) using Pandas' ewm.
    """
    return series.ewm(span=length, adjust=False).mean()

def zlma(series: pd.Series, length: int) -> pd.Series:
    """
    Calculate the Zero-Lag Moving Average (ZLMA).
    
    Steps:
    1) ema_value   = EMA(close, length)
    2) correction  = close + (close - ema_value)
    3) zlma_value  = EMA(correction, length)
    """
    ema_value = ema(series, length)
    correction = series + (series - ema_value)
    zlma_value = ema(correction, length)
    return zlma_value

# -----------------------
# 2) INTERVAL MAPPING
# -----------------------
interval_map = {
    "5 Min": Interval.in_5_minute,
    "15 Min": Interval.in_15_minute,
    "30 Min": Interval.in_30_minute,
    "1 Hour": Interval.in_1_hour,
    "2 Hours": Interval.in_2_hour,
    "4 Hours": Interval.in_4_hour,
    "1 Day": Interval.in_daily,
    "1 Week": Interval.in_weekly
}

# -----------------------
# 3) STREAMLIT APP
# -----------------------
def main():
    st.title("Multiple Tickers: ZLMA vs. EMA % Difference")

    # Move all input controls to the sidebar
    with st.sidebar:
        st.header("Settings")
        
        # --- Symbol/Exchange Settings ---
        symbol1 = st.text_input("Symbol 1", value="BINANCE:BTCUSD")
        symbol2 = st.text_input("Symbol 2", value="OTHERS.D")
        symbol3 = st.text_input("Symbol 3", value="USDT.D")

        exchange = st.text_input("Exchange (e.g., BINANCE, NYSE, etc.)", value="CRYPTOCAP")

        # --- Interval and Bars Selection ---
        selected_interval = st.selectbox("Select Interval", list(interval_map.keys()))
        n_bars = st.number_input("Number of Bars to Fetch", min_value=1, max_value=5000, value=20)

        # --- ZLMA/EMA Length ---
        z_length = st.number_input("EMA / ZLMA Length", min_value=2, max_value=200, value=15)

        # --- Fetch Button ---
        fetch_button = st.button("Fetch Data")

    if fetch_button:
        tv = TvDatafeed()
        with st.spinner("Fetching data..."):
            # Fetch data for each symbol
            df1 = tv.get_hist(
                symbol=symbol1,
                exchange=exchange,
                interval=interval_map[selected_interval],
                n_bars=n_bars
            )
            df2 = tv.get_hist(
                symbol=symbol2,
                exchange=exchange,
                interval=interval_map[selected_interval],
                n_bars=n_bars
            )
            df3 = tv.get_hist(
                symbol=symbol3,
                exchange=exchange,
                interval=interval_map[selected_interval],
                n_bars=n_bars
            )

        # Check if all data is valid
        if any(d is None or d.empty for d in [df1, df2, df3]):
            st.warning("One or more tickers returned no data. Please check symbol/exchange/interval.")
        else:
            # Combine into a dict for convenience
            ticker_dfs = {
                symbol1: df1,
                symbol2: df2,
                symbol3: df3
            }

            # Compute EMA, ZLMA, and diff_pct for each symbol
            for symbol, df in ticker_dfs.items():
                df["EMA"] = ema(df["close"], z_length)
                df["ZLMA"] = zlma(df["close"], z_length)
                df["diff"] = df["ZLMA"] - df["EMA"]
                df["diff_pct"] = (df["diff"] / df["EMA"]) * 100
                df.rename(columns={"diff_pct": f"{symbol}_diff_pct"}, inplace=True)

            # Combine all diff_pct columns into one DataFrame
            combined_diff_pct = pd.concat(
                [
                    ticker_dfs[symbol1][f"{symbol1}_diff_pct"],
                    ticker_dfs[symbol2][f"{symbol2}_diff_pct"],
                    ticker_dfs[symbol3][f"{symbol3}_diff_pct"]
                ],
                axis=1
            )

            # Plot all diff_pct columns in a single chart
            fig = px.line(
                combined_diff_pct,
                x=combined_diff_pct.index,
                y=combined_diff_pct.columns,
                title="(ZLMA - EMA)% for Multiple Tickers"
            )
            st.plotly_chart(fig)

if __name__ == "__main__":
    main()
