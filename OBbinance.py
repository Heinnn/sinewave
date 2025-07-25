import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from binance.client import Client  # Assuming you have imported the Binance client
from binance.enums import HistoricalKlinesType
from highcharts_stock.chart import Chart
from orderblockdetector import *
import pprint
    
client = Client()


# Use full browser width (or centered layout as desired)
st.set_page_config(layout="wide")
placeholder = st.empty()
# --- Sidebar Inputs ---
# selected_ticker = st.sidebar.selectbox("Ticker Symbol", options=["BTCUSDT", "SOLUSDT", "ETHUSDT", "SUIUSDT"], index=0)
ticker_list = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "SUIUSDT"]
# Provide a text input for a custom ticker
custom_ticker = st.sidebar.text_input("Enter a ticker (optional):")
# If a custom ticker is entered, use that; otherwise, let the user select from the list.
if custom_ticker:
    selected_ticker = custom_ticker
else:
    selected_ticker = st.sidebar.selectbox("Ticker Symbol", options=ticker_list, index=0)

selected_timeframe = st.sidebar.selectbox("Timeframe", ["1w","1d", "8h", "4h", "1h", "30m"], index=2)
n_bars = st.sidebar.number_input("Number of Bars", value=360, min_value=10, max_value=1000, step=10)

selected_intervals = st.sidebar.multiselect(
    "Select Timeframes", options=["1d", "8h", "4h", "1h", "30m"], default=["1d", "8h", "4h"]
)
selected_ob_length = st.sidebar.multiselect(
    "OB Length", options =[1,2,3,4,5,6,7], default=[1,2,3,4,5,6,7])

# --- Define Variables based on inputs ---
symbols = [selected_ticker]
intervals = [selected_timeframe]

# --- Retrieve Data ---
def get_historical_data(symbols, intervals, limit=180, save_path=None):
    """
    Retrieve historical data for a list of symbols from Binance API.
    """
    client = Client()  # Initialize the Binance client with your API credentials
    data = {}
    for symbol in symbols:
        placeholder.write(f"Fetching data for {symbol}...")
        for inter in intervals:
            klines = client.get_historical_klines(symbol, inter, klines_type=HistoricalKlinesType.SPOT, limit=limit)
            df = pd.DataFrame(klines, columns=['datetime', 'open', 'high', 'low', 'close', 'volume',
                                                'close_time', 'qav', 'num_trades', 'taker_base_vol',
                                                'taker_quote_vol', 'ignore'])
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
            df.set_index('datetime', inplace=True)
            data[symbol] = df

            # Save the DataFrame to a pickle file if save_path is provided
            if save_path:
                df.to_pickle(f"{save_path}/{symbol}_{inter}_data.pkl")
    return data

def get_combined_order_blocks(selected_ticker, intervals, n_bars):
    """
    Retrieves historical data for each selected timeframe (interval), applies order block detection,
    and then combines the bull and bear order block bands so that each interval’s order blocks are
    extended (merged) with those from every other timeframe but not with its own.

    Parameters:
        selected_ticker (str): The ticker symbol (e.g., "BTCUSDT").
        intervals (list): List of timeframes (e.g., ["1d", "8h", "4h", "1h"]).
        n_bars (int): Number of bars to retrieve for each timeframe.

    Returns:
        tuple: A tuple (bull_bands_combine, bear_bands_combine) where each is a dictionary with key 'plotBands'
            containing the combined bull or bear order block bands.
    """
    # First, compute order blocks for each unique interval
    OBs_by_interval = {}
    unique_intervals = list(set(intervals))
    for inter in unique_intervals:
        historical_data = get_historical_data([selected_ticker], [inter], limit=n_bars, save_path=None)
        data = historical_data[selected_ticker].astype(float)
        data['time'] = data.index
        
        # detect_order_blocks returns: (df_with_ob, bull_OB, bear_OB)
        _, bull_OB, bear_OB = detect_order_blocks(
            data, length=3, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'
        )
        OBs_by_interval[inter] = {"bull": bull_OB[-2:], "bear": bear_OB[-2:]}
        
    
    # Now, for each interval, extend its order blocks with order blocks from all other intervals
    merged_bull_OB = []
    merged_bear_OB = []
    for inter in unique_intervals:
        # Copy the current interval's OB lists (without merging with itself)
        bull_blocks = OBs_by_interval[inter]["bull"].copy()
        bear_blocks = OBs_by_interval[inter]["bear"].copy()
        # Extend with order blocks from other intervals
        for other_inter in unique_intervals:
            if other_inter == inter:
                continue  # skip same interval
            bull_blocks.extend(OBs_by_interval[other_inter]["bull"])
            bear_blocks.extend(OBs_by_interval[other_inter]["bear"])
        # Add the merged list to the final collection.
        merged_bull_OB.extend(bull_blocks)
        merged_bear_OB.extend(bear_blocks)
        
    
    # Optionally remove duplicate order blocks (if your OB objects are dicts, this is one approach)
    def remove_duplicates(ob_list):
        seen = {}
        for ob in ob_list:
            # Using a frozenset of the items as a simple (hashable) key. 
            key = frozenset(ob.items())
            seen[key] = ob
        return list(seen.values())
    
    merged_bull_OB = remove_duplicates(merged_bull_OB)
    merged_bear_OB = remove_duplicates(merged_bear_OB)
    
    # Create plotbands from the merged order blocks.
    bull_bands_combine = create_bull_plotbands(merged_bull_OB)
    bear_bands_combine = create_bear_plotbands(merged_bear_OB)
    
    return bull_bands_combine, bear_bands_combine



# --- Retrieve and preprocess historical data ---
# Assuming variables such as symbols, intervals, n_bars, selected_ticker,
# selected_timeframe, and selected_intervals are defined elsewhere.

# Fetch historical data only once.
historical_data = get_historical_data(symbols, intervals, limit=n_bars, save_path=None)
data = historical_data[selected_ticker].astype(float)
data['time'] = data.index

# # Detect order blocks on the fetched data.
df_with_ob, active_bull_OB, active_bear_OB = detect_order_blocks(
    data, length=3, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'
)

# # Determine the last candle time from the data.
last_candle = data['time'].iloc[-1]

# # --- Define interval mapping ---
# # Map timeframe strings to their respective bar interval in milliseconds.
interval_map = {
    '30m': 30 * 60 * 1000,
    '1h': 3600000,
    '4h': 4 * 3600000,
    '8h': 8 * 3600000,
    '1d': 24 * 3600000,
    '1w': 7 * 24 * 3600000,
}

# # --- Create default series for the selected timeframe ---
bear_bands_series = create_bear_series(active_bear_OB, last_candle, bar_interval=interval_map[selected_timeframe])
bull_bands_series = create_bull_series(active_bull_OB, last_candle, bar_interval=interval_map[selected_timeframe])

# # --- Build output list for candlestick chart ---
# # Each entry is [timestamp_millis, open, high, low, close, volume].
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
        for ob_length in selected_ob_length:
            # Get the corresponding bar interval value.
            bar_interval_val = interval_map[interval]
        
            # Optionally, if your application requires data re-aggregation per timeframe,
            # modify or aggregate 'data' here. Otherwise, you can reuse the same data.
            historical_data_tf = get_historical_data(symbols, [interval], limit=n_bars, save_path=None)
            data_tf = historical_data_tf[selected_ticker].astype(float)
            data_tf['time'] = data_tf.index
        
            # Recalculate the order blocks using the same data_tf for demonstration.
            df_with_ob_tf, active_bull_OB_tf, active_bear_OB_tf = detect_order_blocks(
                data_tf, length=ob_length, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'
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
                    'text': f'{round(interval[1],2)} ({interval[0]})',
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
                    'text': f'{round(interval[1],2)} ({interval[0]})',
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
        'selected': 3
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