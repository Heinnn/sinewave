import pickle
import logging
from typing import Dict

from binance.client import Client
from tqdm import tqdm

API_KEY = 'oMljnMnvrm4CsQIstONUiHbbhOdsWYjZRkiXMT1nZvP7LKl1kIymQMOq7TeFopkW'
API_SECRET = '9kK8TwSF7Q0t7qXxzjQThZZZwGd7IP0mDbuk5a4zg7pMGwQIsHwzZWxL3iWehD47'


def fetch_futures_brackets(client: Client) -> Dict[str, dict]:
    """
    Fetch leverage brackets for all futures symbols.
    """
    exchange_info = client.futures_exchange_info()
    symbols = [s["symbol"] for s in exchange_info["symbols"]]
    brackets: Dict[str, dict] = {}
    for symbol in tqdm(symbols, desc="Fetching leverage brackets"):
        try:
            bracket_data = client.futures_leverage_bracket(symbol=symbol)
            brackets[symbol] = bracket_data
        except Exception as e:
            logging.warning("Skipping symbol %s due to error: %s", symbol, e)
    return brackets


def fetch_token_info(client: Client) -> Dict[str, dict]:
    """
    Extract token info mapping from symbol to metadata.
    """
    exchange_info = client.futures_exchange_info()
    symbols_info = exchange_info["symbols"]
    return {s["symbol"]: s for s in symbols_info}


def save_to_pickle(obj: dict, filename: str) -> None:
    """
    Save an object to a pickle file.
    """
    with open(filename, "wb") as f:
        pickle.dump(obj, f)
    logging.info("Saved data to %s", filename)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    client = Client(API_KEY, API_SECRET)

    brackets = fetch_futures_brackets(client)
    save_to_pickle(brackets, "futures_bracket.pkl")

    token_info = fetch_token_info(client)
    save_to_pickle(token_info, "token_info.pkl")


if __name__ == "__main__":
    main()
