import os
import json
import MetaTrader5 as mt5
from loguru import logger
from datetime import datetime
from datetime import timedelta

from collections import deque
import hashlib

# Configuration
CACHE_FILE = 'order_cache.json'  # File to persist the cache
_CACHE_MAX = 1000               # Maximum number of entries to keep in memory

# In-memory structures
_ORDER_KEY_CACHE = deque()
_SENT_KEYS = set()


def _load_cache():
    """
    Load existing cache from disk into memory.
    """
    global _ORDER_KEY_CACHE, _SENT_KEYS
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Keep only the most recent _CACHE_MAX entries
            trimmed = data[-_CACHE_MAX:]
            _ORDER_KEY_CACHE = deque(trimmed)
            _SENT_KEYS = set(trimmed)
        except (json.JSONDecodeError, IOError):
            # If the file is corrupted or unreadable, start fresh
            _ORDER_KEY_CACHE = deque()
            _SENT_KEYS = set()

def _save_cache():
    """
    Persist the current cache to disk as a JSON list.
    """
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(_ORDER_KEY_CACHE), f)
    except IOError:
        # Handle write errors if necessary
        pass

# Load cache when module is imported
_load_cache()


def remove_orders_by_comment(symbol: str, comment: str):
    """
    Remove all pending orders for `symbol` whose .comment matches `comment`.
    Assumes MT5 is already initialized elsewhere and will remain open.
    """
    # Fetch all pending orders for the symbol
    orders = mt5.orders_get(symbol=symbol)
    if orders is None:
        logger.error(f"[Error] orders_get failed for {symbol}: {mt5.last_error()}")
        return

    # Filter tickets by matching comment
    tickets = [o.ticket for o in orders if o.comment == comment]
    if not tickets:
        logger.info(f"No orders with comment '{comment}' found for {symbol}.")
        return

    logger.info(f"Removing tickets: {tickets}")
    # Send remove request for each ticket
    for ticket in tickets:
        req = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "symbol": symbol,
            "order": ticket,
        }
        res = mt5.order_send(req)
        if res is None:
            logger.error(f"[Ticket {ticket}] no response, error: {mt5.last_error()}")
        elif res.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[Ticket {ticket}] failed (retcode={res.retcode}): {res.comment}")
        else:
            logger.success(f"[Ticket {ticket}] removed successfully")


def close_positions_by_comment(symbol: str, comment: str, action: str):
    """
    Close all positions for `symbol` whose .comment == comment,
    filtered by action: either 'CLOSE_LONG' or 'CLOSE_SHORT'.
    """
    if action not in ("CLOSE_LONG", "CLOSE_SHORT"):
        raise ValueError("action must be 'CLOSE_LONG' or 'CLOSE_SHORT'")

    # map action → required pos.type (0 = long, 1 = short)
    target_type = 0 if action == "CLOSE_LONG" else 1

    # fetch positions for symbol
    positions = mt5.positions_get(symbol=symbol) or []
    # filter by side and comment
    to_close = [pos for pos in positions 
                if pos.type == target_type and pos.comment == comment]

    if not to_close:
        logger.info(f"No {action.lower()} positions with comment='{comment}' for {symbol}")
        return

    for pos in to_close:
        # use mt5.Close (or your wrapper) to close by ticket
        success = mt5.Close(symbol=symbol, ticket=pos.ticket)
        if success is not True:
            # result may be an object with .comment
            err = getattr(success, 'comment', success)
            logger.error(f"Failed to close position {pos.ticket}: {err}")
        else:
            logger.success(f"Position {pos.ticket} closed successfully")



def false_if_double_order(symbol: str, comment: str, action: str):
    # Determine the target position type based on action
    if action in ("LONG", "LIMIT_LONG"):
        target_type = [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT]
        opposite_type = mt5.ORDER_TYPE_SELL
    elif action in ("SHORT", "LIMIT_SHORT"):
        target_type = [mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT]
        opposite_type = mt5.ORDER_TYPE_BUY
    else:
        raise ValueError("Action must be 'LONG' or 'SHORT'")

    # Fetch existing positions for the symbol
    positions = mt5.positions_get(symbol=symbol) or []
    orders = mt5.orders_get(symbol=symbol) or []

    # Check positions and orders with matching comment
    matching_positions = [pos for pos in positions if pos.comment == comment]
    matching_orders = [order for order in orders if order.comment == comment]

    # Combine positions and orders
    existing = matching_positions + matching_orders

    if len(existing) >= 2:
        return False
    elif len(existing) == 1:
        existing_type = existing[0].type
        if existing_type in target_type:
            return False
        else:
            return True

    # If no existing positions or orders, allow opening
    return True


def is_duplicate_order(price_open, sl, tp, comment, from_date=None, to_date=None):
    if from_date is None:
        from_date = datetime.now() - timedelta(days=30)
    if to_date is None:
        to_date = datetime.now()
    sumnumber = sum([price_open, sl])
    history_orders = mt5.history_orders_get(from_date, to_date)
    orders_filtered = [order for order in history_orders if order.comment == comment]
    unique_n = [sum([order.price_open, order.sl]) for order in orders_filtered]

    return sumnumber in unique_n


def is_order_unique(symbol: str,
                    action: str,
                    price: float,
                    sl: float,
                    tp: float,
                    comment: str) -> bool:
    """
    Returns True if this (symbol, action, price, sl, tp, comment) tuple
    hasn't been sent in the last _CACHE_MAX calls. Records it if new,
    and persists the updated cache to disk.
    """
    # Construct a unique key string and hash it
    key_src = f"{symbol}|{price}|{sl}|{comment}"
    key = hashlib.sha256(key_src.encode('utf-8')).hexdigest()

    # Check for duplicates
    if key in _SENT_KEYS:
        return False

    # Prune oldest if at capacity
    if len(_ORDER_KEY_CACHE) >= _CACHE_MAX:
        oldest = _ORDER_KEY_CACHE.popleft()
        _SENT_KEYS.remove(oldest)

    # Record the new key
    _ORDER_KEY_CACHE.append(key)
    _SENT_KEYS.add(key)

    # Persist cache to disk
    _save_cache()

    return True