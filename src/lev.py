# Maintenance table for USDC positions.
# Each tuple: (max_notional, max_leverage, maint_margin_rate %, maint_amount)
maint_btc = [
    (50_000,         125, 0.40,      0),
    (600_000,        100, 0.50,     50),
    (3_000_000,       75,  0.65,    950),
    (12_000_000,      50,  1.00,  11_450),
    (70_000_000,      25,  2.00, 131_450),
    (100_000_000,     20,  2.50, 481_450),
    (230_000_000,     10,  5.00,2_981_450),
    (480_000_000,      5, 10.00,14_481_450),
    (600_000_000,      4, 12.50,26_481_450),
    (800_000_000,      3, 15.00,41_481_450),
    (1_200_000_000,    2, 25.00,121_481_450),
    (1_800_000_000,    1, 50.00,421_481_450),
]

maint_sol = [
    (10_000,        100, 0.50,       0),
    (50_000,         75, 0.65,      15),
    (200_000,        50, 1.00,     190),
    (500_000,        40, 1.20,     590),
    (1_000_000,      25, 2.00,   4_590),
    (2_000_000,      20, 2.50,   9_590),
    (5_000_000,      10, 5.00,  59_590),
    (15_000_000,      5,10.00, 309_590),
    (20_000_000,      4,12.50, 684_590),
    (50_000_000,      2,25.00,3_184_590),
    (100_000_000,     1,50.00,15_684_590),
]

maint_table = {
    "BTCUSD": maint_btc,
    "BTCUSDC": maint_btc,
    "BTCUSDT": maint_btc,
    "SOLUSDC": maint_sol,
    "SOLUSDT": maint_sol,
}

def binance_leverage_custom(
    liq_price: float,
    entry_price: float,
    wallet_balance: float,
    side: str = "BUY",
    symbol: str = "BTCUSDC",
) -> float:
    """
    Calculate the approximate leverage (L) for a USDC futures position
    based on a desired liquidation price, using Binance’s tiered maintenance margin settings.

    Formulas used:

      For long (BUY) positions:
         L = [entry_price * (wallet_balance + A)] / [wallet_balance * (entry_price - liq_price*(1 - R))]
         
      For short (SELL) positions:
         L = [entry_price * (wallet_balance + A)] / [wallet_balance * (liq_price*(1 + R) - entry_price)]
         (returned as a negative number to indicate a short)

    Here:
      - R is the maintenance margin rate as a decimal (e.g. 0.005 for 0.50%),
      - A is the maintenance amount (offset),
      - The function iterates over tiers (ordered by increasing max notional)
        and selects the first tier where the notional value (wallet_balance * |L|) is within that tier’s bracket.
      - If the computed leverage exceeds the tier’s maximum, it is capped accordingly.

    :param liq_price: Target liquidation price.
    :param entry_price: Entry price of the position.
    :param wallet_balance: Margin balance in USDC.
    :param side: "BUY" for long or "SELL" for short.
    :return: Approximate leverage (positive for long, negative for short).
    """
    if side not in ["LONG", "SHORT", "LIMIT_LONG", "LIMIT_SHORT"]:
        raise ValueError("side must be [LONG, SHORT, LIMIT_LONG, LIMIT_SHORT]")

    for max_notional, tier_max_leverage, maint_margin_rate_pct, maint_amount in maint_table[symbol]:
        R = maint_margin_rate_pct / 100.0  # convert percentage to decimal
        A = maint_amount

        if side in ["LONG", "LIMIT_LONG"]:
            if liq_price >= entry_price:
                raise ValueError("For a long position, liq_price must be < entry_price.")
            denominator = entry_price - liq_price * (1 - R)
            if abs(denominator) < 1e-14:
                raise ValueError("Denominator is too close to zero; check your inputs.")
            L_candidate = (entry_price * (wallet_balance + A)) / (wallet_balance * denominator)
        elif side in ["SHORT", "LIMIT_SHORT"]:  # For short positions:
            if liq_price <= entry_price:
                raise ValueError("For a short position, liq_price must be > entry_price.")
            denominator = liq_price * (1 + R) - entry_price
            if abs(denominator) < 1e-14:
                raise ValueError("Denominator is too close to zero; check your inputs.")
            L_candidate = (entry_price * (wallet_balance + A)) / (wallet_balance * denominator)
            L_candidate = L_candidate  # Negative leverage indicates a short position
        else: raise ValueError("Invalid side. Must be 'LONG' or 'SHORT'.")


        # Calculate notional value for this candidate
        notional = wallet_balance * abs(L_candidate)

        # Check if the candidate's notional falls within the tier's bracket.
        if notional <= max_notional:
            # Cap the leverage if it exceeds the tier's maximum allowed leverage.
            if abs(L_candidate) > tier_max_leverage:
                L_candidate = tier_max_leverage if side in ["LONG", "LIMIT_LONG"] else -tier_max_leverage
            return L_candidate

    raise ValueError("No valid tier found for the given parameters.")

# Example usage:
# if __name__ == '__main__':
#     # Example for a long position:
#     try:
#         leverage_long = binance_leverage_from_liq_price_tiered_usdc(
#             liq_price=79956, entry_price=82419, wallet_balance=10, side="BUY", symbol="BTCUSDC"
#         )
#         print(f"Calculated leverage (long): {leverage_long:.2f}x")
#     except ValueError as e:
#         print("Error:", e)

#     # Example for a short position:
#     try:
#         leverage_short = binance_leverage_from_liq_price_tiered_usdc(
#             liq_price=110, entry_price=100, wallet_balance=1000, side="SELL", maint_table=maint_btc
#         )
#         print(f"Calculated leverage (short): {leverage_short:.2f}x")
#     except ValueError as e:
#         print("Error:", e)
