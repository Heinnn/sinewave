import pickle

with open("futures_bracket.pkl", "rb") as f:
    futures_bracket = pickle.load(f)
    
with open("token_info.pkl", "rb") as f:
    token_info = pickle.load(f)
    
def binance_leverage_custom(
    liq_price: float,
    entry_price: float,
    wallet_balance: float,
    side: str = "BUY",
    symbol: str = "ERAUSDT",
    bracket_data: dict = None,
) -> float:
    """
    Calculate approximate leverage (positive for long, negative for short)
    using Binance’s tiered maintenance‐margin brackets.

    :param liq_price: Target liquidation price.
    :param entry_price: Entry price of the position.
    :param wallet_balance: Margin balance in USDC.
    :param side: "BUY" or "LONG" (long), "SELL" or "SHORT" (short).
    :param symbol: e.g. "ERAUSDT"
    :param bracket_data: dict loaded from your futures_bracket.pkl
    """

    if bracket_data is None:
        raise ValueError("You must pass in bracket_data (e.g. your futures_bracket dict).")

    # Fetch bracket list for this symbol
    symbol_entries = bracket_data.get(symbol)
    if not symbol_entries:
        raise ValueError(f"No bracket data found for symbol '{symbol}'")
    # assume the first dict in the list holds our brackets
    brackets = symbol_entries[0].get("brackets", [])
    if not brackets:
        raise ValueError(f"No 'brackets' key for symbol '{symbol}'")

    # normalize side
    s = side.upper()
    is_long  = s in ("BUY", "LONG", "LIMIT_LONG")
    is_short = s in ("SELL", "SHORT", "LIMIT_SHORT")
    if not (is_long or is_short):
        raise ValueError("side must be one of BUY, SELL, LONG, SHORT, LIMIT_LONG, LIMIT_SHORT")

    # Iterate tiers in order of increasing notionalCap
    for tier in brackets:
        max_notional       = tier["notionalCap"]
        tier_max_leverage  = tier["initialLeverage"]
        R                  = tier["maintMarginRatio"]  # already decimal, e.g. 0.01
        A                  = tier["cum"]                # maintenance-offset

        # compute candidate L
        if is_long:
            if liq_price >= entry_price:
                raise ValueError("For a long, liq_price must be < entry_price.")
            denom = entry_price - liq_price * (1 - R)
            if abs(denom) < 1e-14:
                raise ValueError("Denominator too small; check inputs.")
            L_cand = (entry_price * (wallet_balance + A)) / (wallet_balance * denom)

        else:  # is_short
            if liq_price <= entry_price:
                raise ValueError("For a short, liq_price must be > entry_price.")
            denom = liq_price * (1 + R) - entry_price
            if abs(denom) < 1e-14:
                raise ValueError("Denominator too small; check inputs.")
            L_cand = (entry_price * (wallet_balance + A)) / (wallet_balance * denom)
            L_cand = -abs(L_cand)  # negative to indicate a short

        notional = wallet_balance * abs(L_cand)

        # pick the first tier that can support this notional
        if notional <= max_notional:
            # cap leverage if it exceeds the tier’s max
            if abs(L_cand) > tier_max_leverage:
                L_cand =  tier_max_leverage  if is_long else -tier_max_leverage
            return L_cand

    raise ValueError("Your position size exceeds the max notional of all tiers.")
