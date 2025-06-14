import pandas as pd
import numpy as np

def is_pivot_high(series, idx, left, right):
    """
    Returns True if series[idx] is a pivot high compared to the 'left' bars before
    and 'right' bars after. (This mimics TradingView's ta.pivothigh.)
    """
    # Make sure indices are in range
    if idx - left < 0 or idx + right >= len(series):
        return False
    pivot_val = series.iloc[idx]
    # Check left side: every value must be strictly lower
    if (series.iloc[idx - left:idx] >= pivot_val).any():
        return False
    # Check right side: every value must be lower (note: right side uses > to mimic Pine’s behavior)
    if (series.iloc[idx+1: idx+right+1] > pivot_val).any():
        return False
    return True

def detect_order_blocks(df, length=5, bull_ext_last=3, bear_ext_last=3, mitigation='Wick'):
    """
    Detects bullish and bearish order blocks in a DataFrame (which must include 
    'time', 'open', 'high', 'low', 'close', and 'volume' columns). 
    The logic mimics the provided Pine script: it uses a pivot-high on volume and 
    a state (os) that is updated based on rolling high/low windows.
    
    Parameters:
      df             : pandas DataFrame with OHLCV data.
      length         : Volume pivot length (default=5)
      bull_ext_last  : Number of bullish OB boxes to “extend” (for drawing; not used in DF output)
      bear_ext_last  : Number of bearish OB boxes to “extend” 
      mitigation     : Either 'Wick' or 'Close'. When 'Close', target values are computed from the close.
    
    Returns:
      A copy of df with extra columns:
         - 'bull_ob'       : bullish OB value (plotted with an offset, as in Pine)
         - 'bear_ob'       : bearish OB value 
         - 'bull_mitigated': Boolean flag that is set to True when a bullish OB is removed
         - 'bear_mitigated': Boolean flag for bearish OB mitigation
    """
    
    # Verify required columns exist
    for col in ['time', 'open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")
    
    # Work on a copy and initialize output columns
    df = df.copy()
    df['bull_ob'] = np.nan
    df['bear_ob'] = np.nan
    df['bull_mitigated'] = False
    df['bear_mitigated'] = False

    # This state variable (os_state) is used to decide if a new OB is bullish (os==1)
    # or bearish (os==0). (Initial value 0.)
    os_state = 0  
    active_bull_OB = []  # will hold active bullish OB details (dictionaries)
    active_bear_OB = []  # similar for bearish OB

    # Loop over bars. We use an index i that represents the current bar at which we update our
    # rolling window. Note: Pine’s code refers to bar[i-length] (via the [length] offset).
    for i in range(length, len(df)):
        # Rolling window (last 'length' bars including current bar)
        window = df.iloc[i - length + 1 : i + 1]
        upper = window['high'].max()
        lower = window['low'].min()
        if mitigation == 'Close':
            target_bull = window['close'].min()
            target_bear = window['close'].max()
        else:
            target_bull = lower
            target_bear = upper

        # The pivot bar is taken as "i - length" (this mimics the offset used in Pine)
        pivot_idx = i - length
        if pivot_idx < 0:
            continue
        
        pivot_row = df.iloc[pivot_idx]
        
        # Update the os_state based on the pivot bar compared to the current rolling window:
        if pivot_row['high'] > upper:
            os_state = 0
        elif pivot_row['low'] < lower:
            os_state = 1
        # else: keep os_state unchanged
        
        # Check for a volume pivot high at the pivot bar:
        if is_pivot_high(df['volume'], pivot_idx, length, length):
            if os_state == 1:
                # Bullish Order Block: use pivot_row values
                bull_ob_value = pivot_row['low']
                hl2 = (pivot_row['high'] + pivot_row['low']) / 2
                bull_top = hl2
                bull_btm = pivot_row['low']
                bull_avg = (bull_top + bull_btm) / 2
                # Save details (if you wish to use them for plotting later)
                active_bull_OB.append({
                    'index': pivot_idx,
                    'bull_top': bull_top,
                    'bull_btm': bull_btm,
                    'bull_avg': bull_avg,
                    'bull_left': pivot_row['time'],
                    'value': bull_ob_value
                })
                # In Pine the OB value is plotted with an offset; here we record it at bar i.
                df.at[df.index[i], 'bull_ob'] = bull_ob_value

            elif os_state == 0:
                # Bearish Order Block:
                bear_ob_value = pivot_row['high']
                hl2 = (pivot_row['high'] + pivot_row['low']) / 2
                bear_top = pivot_row['high']
                bear_btm = hl2
                bear_avg = (bear_top + bear_btm) / 2
                active_bear_OB.append({
                    'index': pivot_idx,
                    'bear_top': bear_top,
                    'bear_btm': bear_btm,
                    'bear_avg': bear_avg,
                    'bear_left': pivot_row['time'],
                    'value': bear_ob_value
                })
                df.at[df.index[i], 'bear_ob'] = bear_ob_value

        # Remove mitigated OBs (this mimics the remove_mitigated function in Pine)
        bull_mitigated_flag = False
        for ob in active_bull_OB.copy():
            if target_bull < ob['bull_btm']:
                active_bull_OB.remove(ob)
                bull_mitigated_flag = True
        if bull_mitigated_flag:
            df.at[df.index[i], 'bull_mitigated'] = True

        bear_mitigated_flag = False
        for ob in active_bear_OB.copy():
            if target_bear > ob['bear_top']:
                active_bear_OB.remove(ob)
                bear_mitigated_flag = True
        if bear_mitigated_flag:
            df.at[df.index[i], 'bear_mitigated'] = True

    return df, active_bull_OB, active_bear_OB

# --- Example usage ---

# Suppose you have a DataFrame 'data' with columns: 
# ['time', 'open', 'high', 'low', 'close', 'volume'].
# You can then run:
#
# df_with_ob, active_bull_OB, active_bear_OB = detect_order_blocks(data, length=3, bull_ext_last=3, bear_ext_last=3, mitigation='Wick')
#
# Now, df_with_ob will include the new columns that correspond to the Pine code’s output.




def find_all_stacked_points(resp):
    """
    Finds all vertical intervals (with their overlap counts and intercepts)
    where the polygon boxes overlap.

    The input, resp, is a list of dictionaries (each representing a polygon)
    with a 'data' key. The 'data' is a list of points, where each point is 
    a two-element list [x, y]. A y-value of None indicates a break between segments.
    
    For each contiguous segment, the vertical interval is defined as the minimum 
    and maximum y-values. Then, a sweep-line algorithm is used to compute the overlap
    count for every contiguous vertical interval.
    
    The function returns a list of tuples:
         (overlap_count, (start, end), intercept)
    
    The returned list is sorted in descending order first by overlap_count, and then
    by the intercept value.

    Parameters:
      resp (list): List of polygon dictionaries.
      
    Returns:
      list: Sorted list of tuples (overlap_count, interval, intercept). If no intervals
            are found, returns an empty list.
    """
    intervals = []
    
    # Extract vertical intervals from each polygon's data segments.
    for band in resp:
        segment_points = []
        for point in band.get('data', []):
            # A point with None indicates a break between segments.
            if point[1] is None:
                if segment_points:
                    ys = [pt[1] for pt in segment_points]
                    lower, upper = min(ys), max(ys)
                    intervals.append({'from': lower, 'to': upper})
                    segment_points = []
            else:
                segment_points.append(point)
        # Process any trailing segment if not terminated by a None.
        if segment_points:
            ys = [pt[1] for pt in segment_points]
            lower, upper = min(ys), max(ys)
            intervals.append({'from': lower, 'to': upper})
    
    if not intervals:
        return []
    
    # Build events for the sweep-line algorithm.
    # Each interval contributes a +1 event at its lower bound and a -1 event at its upper bound.
    events = []
    for interval in intervals:
        lower = min(interval['from'], interval['to'])
        upper = max(interval['from'], interval['to'])
        events.append((lower, 1))
        events.append((upper, -1))
    
    # Sort events by coordinate; for ties, start events (+1) come before end events (-1)
    events.sort(key=lambda x: (x[0], -x[1]))
    
    # Sweep-line: record every contiguous interval where the overlap count is constant.
    result = []
    current_count = 0
    prev_coordinate = events[0][0]
    
    for coordinate, delta in events:
        if coordinate != prev_coordinate:
            interval_segment = (prev_coordinate, coordinate)
            intercept = (prev_coordinate + coordinate) / 2
            result.append((current_count, interval_segment, intercept))
            prev_coordinate = coordinate
        current_count += delta
    
    # Sort the results:
    # First by overlap_count in descending order, then by intercept (also descending).
    result.sort(key=lambda x: (x[0], x[2]), reverse=True)
    
    return result


def create_bear_plotbands(bear_list):
    plotbands = []
    for bear in bear_list:
        plotband = {
            'color': '#f8cdcd',
            'borderColor': 'red',
            'borderWidth': 0.2,
            'from': bear['bear_top'],
            'to': bear['bear_btm'],
            'zIndex': 2,
            'label': {
                # 'text': "OB"
            }
        }
        plotbands.append(plotband)
    return {'plotBands': plotbands}

def create_bull_plotbands(bull_list):
    plotbands = []
    for bull in bull_list:
        plotband = {
            'color': '#cdf8d0',
            'borderColor': 'green',
            'borderWidth': 0.2,
            'from': bull['bull_top'],
            'to': bull['bull_btm'],
            'zIndex': 2,
            'label': {
                # 'text': "OB"
            }
        }
        plotbands.append(plotband)
    return {'plotBands': plotbands}

def create_bear_series(bear_list, last_candle, bar_interval=3600000):
    # Compute the common right boundary from the last bear's timestamp plus margin.
    right_boundary = int(last_candle.timestamp() * 1000)
    series_data = []
    for bear in bear_list:
        # Convert the bear_left timestamp to milliseconds for the left boundary.
        left = int(bear['bear_left'].timestamp() * 1000)
        
        # Build the polygon points:
        # 1. Bottom left, 2. Bottom right, 3. Top right, 4. Top left, 5. A break marker
        polygon = [
            [left, bear['bear_btm']],
            [right_boundary, bear['bear_btm']],
            [right_boundary, bear['bear_top']],
            [left, bear['bear_top']],
            [right_boundary, None]
        ]
        series_data.extend(polygon)
    
    return {
        'name': 'Polygons',
        'type': 'polygon',
        'data': series_data,
        'color': 'rgba(255, 145, 145, 0.35)',  # Fill color for the polygon
        'lineColor': '#f70b0b',
        'lineWidth': 1.5,     
        'enableMouseTracking': False,
        'tooltip': {
            'pointFormat': 'Polygon area'
        }
    }

def create_bull_series(bull_list, last_candle, bar_interval=3600000):
    # Compute the common right boundary from the last bull's timestamp plus margin.
    right_boundary = int(last_candle.timestamp() * 1000)
    
    series_data = []
    for bull in bull_list:
        # Convert the bull_left timestamp to milliseconds for the left boundary.
        left = int(bull['bull_left'].timestamp() * 1000)
        
        # Build the polygon points:
        # 1. Bottom left, 2. Bottom right, 3. Top right, 4. Top left, 5. A break marker
        polygon = [
            [left, bull['bull_btm']],
            [right_boundary, bull['bull_btm']],
            [right_boundary, bull['bull_top']],
            [left, bull['bull_top']],
            [right_boundary, None]
        ]
        series_data.extend(polygon)
    
    return {
        'name': 'Polygons',
        'type': 'polygon',
        'data': series_data,
        'color': 'rgba(104, 137, 255, 0.35)',  # Fill color for the polygon
        'lineColor': '#f70b0b',
        'lineWidth': 1.5,     
        'enableMouseTracking': False,
        'tooltip': {
            'pointFormat': 'Polygon area'
        }
    }