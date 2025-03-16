import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from highcharts_stock.chart import Chart
from orderblockdetector import *
import pprint
import time
    
tv = TvDatafeed()


# Use full browser width (or centered layout as desired)
st.set_page_config(layout="wide")
placeholder = st.empty()
# --- Sidebar Inputs ---
selected_ticker = st.sidebar.selectbox("Ticker Symbol", options=["BTCUSDT", "SOLUSDT", "ETHUSDT", "SUIUSDT"], index=0)
selected_timeframe = st.sidebar.selectbox("Timeframe", ["1w","1d", "8h", "4h", "1h", "30m"], index=5)
n_bars = st.sidebar.number_input("Number of Bars", value=360, min_value=10, max_value=1000, step=10)

selected_intervals = st.sidebar.multiselect(
    "Select Timeframes", options=["1d", "8h", "4h", "1h", "30m"], default=["4h", "1h", "30m"]
)

# --- Define Variables based on inputs ---
symbols = [selected_ticker]
intervals = [selected_timeframe]

interval_tvmap = {
    "30m": Interval.in_30_minute,
    "1h": Interval.in_1_hour,
    "4h": Interval.in_4_hour,
    "8h": Interval.in_8_hour,
    "1d": Interval.in_daily,
    "1w": Interval.in_weekly,
    "1M": Interval.in_monthly
}
    

# --- Retrieve and preprocess historical data ---
# Assuming variables such as symbols, intervals, n_bars, selected_ticker,
# selected_timeframe, and selected_intervals are defined elsewhere.

# Fetch historical data only once.
attempt = 0
historical_data = None
max_retries = 3
while attempt < max_retries:
    try:
        historical_data = tv.get_hist(
            symbol=selected_ticker,
            exchange="BINANCE",
            interval=interval_tvmap[selected_timeframe],
            n_bars=n_bars
        )
        historical_data['time'] = historical_data.index
        break
    except Exception as e:
        attempt += 1
        print(f"Attempt {attempt} for {selected_ticker} failed: {e}")
        time.sleep(1)

data = historical_data

# Detect order blocks on the fetched data.
df_with_ob, active_bull_OB, active_bear_OB = detect_order_blocks(
    data, length=3, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'
)

# Determine the last candle time from the data.
last_candle = data['time'].iloc[-1]

# --- Define interval mapping ---
# Map timeframe strings to their respective bar interval in milliseconds.
interval_map = {
    '30m': 30 * 60 * 1000,
    '1h': 3600000,
    '4h': 4 * 3600000,
    '8h': 8 * 3600000,
    '1d': 24 * 3600000,
    '1w': 7 * 24 * 3600000,
}

# --- Create default series for the selected timeframe ---
bear_bands_series = create_bear_series(active_bear_OB, last_candle, bar_interval=interval_map[selected_timeframe])
bull_bands_series = create_bull_series(active_bull_OB, last_candle, bar_interval=interval_map[selected_timeframe])
# pprint.pprint(bear_bands_series)

# --- Build output list for candlestick chart ---
# Each entry is [timestamp_millis, open, high, low, close, volume].
output_list = []
for idx, row in data.iterrows():
    ts_millis = int(idx.timestamp() * 1000)
    output_list.append([
        ts_millis, row["open"], row["high"], row["low"], row["close"], row["volume"]
    ])

# --- Process additional intervals if provided ---
if selected_intervals:
    bear_series_list = []
    bull_series_list = []
    
    # Define color mapping for each interval for bear and bull series.
    bear_color_map = {
        '1d': 'rgba(187, 187, 187, 0.3)',
        '8h': 'rgba(104, 137, 255, 0.3)',
        '4h': 'rgba(255, 0, 0, 0.15)',
        '1h': 'rgba(6, 108, 48, 0.3)', 
        '30m': 'rgba(139, 0, 0, 0.5)' 
    }
    bull_color_map = {
        '1d': 'rgba(187, 187, 187, 0.3)',
        '8h': 'rgba(104, 137, 255, 0.3)',
        '4h': 'rgba(255, 0, 0, 0.15)',
        '1h': 'rgba(6, 108, 48, 0.3)',
        '30m': 'rgba(139, 0, 0, 0.5)' 
    }
    
    # Loop over the selected intervals to create series with unique visual properties.
    for idx, interval in enumerate(selected_intervals):
        # Get the corresponding bar interval value.
        bar_interval_val = interval_map[interval]
        
        # Optionally, if your application requires data re-aggregation per timeframe,
        # modify or aggregate 'data' here. Otherwise, you can reuse the same data.
        attempt = 0
        data_tf = None
        while attempt < max_retries:
            try:
                data_tf = tv.get_hist(
                    symbol=selected_ticker,
                    exchange="BINANCE",
                    interval=interval_tvmap[interval],
                    n_bars=n_bars
                )
                data_tf['time'] = data_tf.index
                break
            except Exception as e:
                attempt += 1
                print(f"Attempt {attempt} for {selected_ticker} failed: {e}")
                time.sleep(1)

        # Recalculate the order blocks using the same data_tf for demonstration.
        df_with_ob_tf, active_bull_OB_tf, active_bear_OB_tf = detect_order_blocks(
            data_tf, length=3, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'
        )
        
        # Create bear and bull series for the current interval using the last 3 elements.
        bear_series = create_bear_series(active_bear_OB_tf[-3:], last_candle, bar_interval=bar_interval_val)
        bull_series = create_bull_series(active_bull_OB_tf[-3:], last_candle, bar_interval=bar_interval_val)
        
        # Set fill colors and line colors based on the interval.
        bear_series['color'] = bear_color_map.get(interval, 'rgba(0, 0, 0, 0)')
        bull_series['color'] = bull_color_map.get(interval, 'rgba(0, 0, 0, 0)')
        
        bear_series_list.append(bear_series)
        bull_series_list.append(bull_series)
        
    all_stacked_bull = find_all_stacked_points(bull_series_list)
    all_stacked_bull_1 = [(x, max(pair), c) for x, pair, c in all_stacked_bull]
    
    all_stacked_bear = find_all_stacked_points(bear_series_list)
    all_stacked_bear_1 = [(x, min(pair), c) for x, pair, c in all_stacked_bear]


    # Use the first 3 intervals.
    all_stacked_bear_1 = [item for item in all_stacked_bear_1 if item[0] > 1][:2]
    all_stacked_bull_1 = [item for item in all_stacked_bull_1 if item[0] > 1][:2]

    # Build the plotLines dictionary using a list comprehension.
    plotLines_bear = {
        'plotLines': [
            {
                'value': interval[1],      # The intercept value.
                'color': 'red',
                'dashStyle': 'Dash',
                'width': 1,
                'zIndex': 3,
                'label': {
                    # Use the start of the interval (first value in the tuple) for the label.
                    'text': f'{int(interval[1])} ({interval[0]})',
                    'align': 'left',
                    'x': 0
                }
            }
            for i, interval in enumerate(all_stacked_bear_1)
        ]
    }

    plotLines_bull = {
        'plotLines': [
            {
                'value': interval[1],      # The intercept value.
                'color': 'green',
                'dashStyle': 'Dash',
                'width': 1,
                'zIndex': 3,
                'label': {
                    # Use the start of the interval (first value in the tuple) for the label.
                    'text': f'{int(interval[1])} ({interval[0]})',
                    'align': 'left',
                    'x': 0
                }
            }
            for i, interval in enumerate(all_stacked_bull_1)
        ]
    }
        
    plotLines = {'plotLines': plotLines_bull['plotLines'] + plotLines_bear['plotLines']}
    plotLines.update({'offset': 30, 'startOnTick': False, 'endOnTick': False})
    
    # Build the series list using the candlestick series plus our multi-interval series.
    chart_series = [{
            'type': 'candlestick',
            'name': selected_ticker,
            'data': output_list,
            'enableMouseTracking': False,
            'dataGrouping': {
                'enabled': False 
            },
        }] + bear_series_list + bull_series_list
    
    
    
else:
    # Default series list if no selected intervals are provided.
    chart_series = [
        {
            'type': 'candlestick',
            'name': selected_ticker,
            'data': output_list,
            'enableMouseTracking': False,
            'dataGrouping': {
                'enabled': False 
            },
        },
        bear_bands_series,
        bull_bands_series
    ]
    

# --- Configure Highcharts ---
chart_options = {   
    'plotOptions': {
        'candlestick': {
            'color': 'rgba(0, 0, 0, 0.8)',  # Bearish candle color
            'upColor': 'rgba(255, 255, 255, 0.5)',  # Bullish candle color
            'lineColor': '#000000',  # Border color for bearish candles
            'upLineColor': '#000000',  # Border color for bullish candles
        }
    },
    'chart': {
        'zooming': {
            'type': 'xy',
        },
        # 'panning': True,
        # 'panKey': 'shift'
    },
    'rangeSelector': {
        'buttons': [{
            'type': 'day',
            'count': 3,
            'text': '3d'
        }, {
            'type': 'day',
            'count': 7,
            'text': '7d'
        }, {
            'type': 'month',
            'count': 1,
            'text': 'M'
        }, {
            'type': 'all',
            'count': 1,
            'text': 'All'
        }, {
        }],
        'selected': 1
    },
    'title': {
        'text': f'{selected_ticker}'
    },
    'xAxis': {
        'startOnTick': False,
        'endOnTick': False,
        'overscroll': interval_map[selected_timeframe] * 30,
    },
    'yAxis': plotLines if selected_intervals else {'offset': 30, 'startOnTick': False, 'endOnTick': False},
    
    'navigator': {
        'enabled': True
    },
    'series': chart_series
}

# Build the Highcharts chart object
# Build your chart object and generate its JS literal from your chart_options.
chart = Chart.from_options(chart_options)
js_code = chart.to_js_literal()

# Modify the JS code to bind the chart to the container div
js_code = js_code.replace("Highcharts.stockChart(null", "Highcharts.stockChart('container'")

html_template = f"""
                    <!DOCTYPE html>
                    <html>
                        <head>
                            <meta charset="utf-8" />
                            <!-- Load Highcharts, Highstock, and required modules from CDN -->
                            <script src="https://code.highcharts.com/stock/highstock.js"></script>
                            <script src="https://code.highcharts.com/highcharts.js"></script>
                            <script src="https://code.highcharts.com/highcharts-more.js"></script>
                        </head>
                            <body>
                                <div id="container" style="width: 100%; height: 600px;"></div>
                                <script>
                                {js_code}
                                </script>
                            </body>
                    </html>
"""

# Embed the chart in Streamlit
components.html(html_template, height=700, scrolling=False)


placeholder.empty()