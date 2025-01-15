import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import json

# Highcharts / tvDatafeed imports
from tvDatafeed import TvDatafeed, Interval
from highcharts_stock.chart import Chart

# Use full browser width
st.set_page_config(layout="wide")

###############################################################################
# COLUMN LAYOUT
###############################################################################
col_inputs, col_plots = st.columns([1, 3])

###############################################################################
# LEFT COLUMN: USER INPUTS
###############################################################################
with col_inputs:
    st.title("Sine Waves & Financial Data Plotter")

    # --- Sine Wave Inputs ---
    st.subheader("First Plot: Sine Wave Parameters")

    # Phase options
    phase_red_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]
    phase_green_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]
    phase_blue_options = [0, 1.57, 3.14, 4.72]
    phase_yellow_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]

    alpha_red = st.selectbox("Phase α_red (64 sin)", phase_red_options, index=0)
    alpha_green = st.selectbox("Phase α_green (32 sin)", phase_green_options, index=0)
    alpha_blue = st.selectbox("Phase α_blue (16 sin)", phase_blue_options, index=0)
    alpha_yellow = st.selectbox("Phase α_yellow (8 sin)", phase_yellow_options, index=0)

    pi_multiplier = st.slider(
        "π-Multiplier (e.g., 2 = 2π, 3 = 3π, etc.)",
        min_value=1,
        max_value=10,
        value=2,
        step=1
    )
    st.write(f"**Current π-multiplier**: {pi_multiplier} → effectively using {pi_multiplier}π in each term.")

    # NEW: Checkbox to show/hide sub-waves
    show_subwaves = st.checkbox("Show sub waves", value=True, help="Uncheck to hide individual sub-waves.")

    st.markdown("---")

    # --- Second Plot (tvDatafeed) Settings ---
    st.subheader("Second Plot: tvDatafeed Parameters")

    # Symbol & Exchange
    symbol = st.text_input("Symbol", value="BTCUSDT")
    exchange = st.text_input("Exchange", value="BINANCE")

    # Interval mapping
    interval_map = {
        # "1 minute": Interval.in_1_minute,
        # "5 minutes": Interval.in_5_minute,
        # "15 minutes": Interval.in_15_minute,
        # "30 minutes": Interval.in_30_minute,
        # "1 hour": Interval.in_1_hour,
        # "2 hours": Interval.in_2_hour,
        "4H": Interval.in_4_hour,
        "Day": Interval.in_daily,
        "Week": Interval.in_weekly,
        "Month": Interval.in_monthly
    }
    intervals_list = list(interval_map.keys())

    # Let user select the desired interval
    user_interval = st.selectbox("Select Interval", intervals_list, index=3)  # default: '1 day'
    selected_interval = interval_map[user_interval]

    # Number of bars
    n_bars = st.number_input(
        "Number of Bars",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )

###############################################################################
# RIGHT COLUMN: PLOTS
###############################################################################
with col_plots:
    #
    # -------------------------- FIRST PLOT (Sine Waves) -------------------------
    #
    # Create x range
    x = np.linspace(0, 64, 2000)

    # Build each wave
    wave1 = 64 * np.sin(alpha_red    + pi_multiplier*np.pi*(x/64))
    wave2 = 32 * np.sin(alpha_green  + pi_multiplier*np.pi*(x/32))
    wave3 = 16 * np.sin(alpha_blue   + pi_multiplier*np.pi*(x/16))
    wave4 =  8 * np.sin(alpha_yellow + pi_multiplier*np.pi*(x/8))

    # Sum them
    merged_wave = wave1 + wave2 + wave3 + wave4

    # Plot with matplotlib
    fig, ax = plt.subplots(figsize=(8, 5))

    # Only plot sub-waves if user wants to see them
    if show_subwaves:
        ax.plot(x, wave1, label="64 sin(α_red + mπ·x/64)",   alpha=0.4, color="red")
        ax.plot(x, wave2, label="32 sin(α_green + mπ·x/32)", alpha=0.4, color="green")
        ax.plot(x, wave3, label="16 sin(α_blue + mπ·x/16)",  alpha=0.4, color="blue")
        ax.plot(x, wave4, label="8 sin(α_yellow + mπ·x/8)",  alpha=0.4, color="orange")

    # Always plot the merged wave
    ax.plot(x, merged_wave, label="Sum of all waves", color="magenta", linewidth=2)

    ax.set_xlabel("x (0 to 64)")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"Sine Waves with {pi_multiplier}π Factor")
    ax.legend(loc="upper right")

    st.pyplot(fig)

    st.markdown("---")

    #
    # ------------------------ SECOND PLOT (tvDatafeed) -------------------------
    #
    st.subheader(f"Financial Chart: {symbol} / {exchange}, Interval = {user_interval}")

    # Initialize tvDatafeed (credentials not shown here; ensure your environment is set up)
    tv = TvDatafeed()

    # Retrieve data
    data = tv.get_hist(
        symbol=symbol,
        exchange=exchange,
        interval=selected_interval,
        n_bars=n_bars
    )

    # Build output list: [timestamp_millis, close]
    output_list = []
    for idx, row in data.iterrows():
        ts_millis = int(idx.timestamp() * 1000)
        close_val = row["close"]
        ohlc = [ts_millis, close_val]
        output_list.append(ohlc)

    # Convert to JSON string
    json_string = json.dumps(output_list)

    # Highcharts config
    as_dict = {
        'rangeSelector': {
            'selected': 4
        },
        'title': {
            'text': f'{symbol} {exchange} Chart'
        },
        'navigator': {
            'enabled': True
        },
        'series': [
            {
                'type': 'spline',
                'name': f'{symbol}',
                'data': json_string
            }
        ]
    }

    # Construct Highcharts object
    chart = Chart.from_options(as_dict)

    # Use to_js_literal and embed manually
    js_code = chart.to_js_literal()
    js_code = js_code.replace("Highcharts.stockChart(null", "Highcharts.stockChart('container'")

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <!-- Load Highcharts/Highstock from CDN or your own hosting -->
        <script src="https://code.highcharts.com/stock/highstock.js"></script>
    </head>
    <body>
        <div id="container" style="width: 100%; height: 600px;"></div>
        <script>
        {js_code}
        </script>
    </body>
    </html>
    """

    st.components.v1.html(html_template, height=700, scrolling=True)
