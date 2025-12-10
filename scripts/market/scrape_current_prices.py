import logging
import typing as t
from pathlib import Path
from datetime import datetime

from marketdata import config
from marketdata.shared import http_utils
from marketdata.constants import CURRENT_MARKET_PRICES_URL, HOME_URL
from marketdata import shared, setup
from marketdata.classes import CurrentPricesRaw, CurrentPrices  # New import

import httpx

log = logging.getLogger(__name__)


def check_online() -> bool:
    req = httpx.Request("GET", HOME_URL)
    maintenance_keywords = ["Server Reset", "will be right back"]

    try:
        html = send_request(req, use_cache=False)
    except Exception:
        return False

    if any(kw in html.text for kw in maintenance_keywords):
        log.warning("FarmRPG maintenance mode detected")
        return False

    return True


def send_request(req, use_cache: bool = True):
    client = shared.http_utils.get_client(use_cache=use_cache)

    try:
        with client as http:
            res: httpx.Response = http.send(req)
            res.raise_for_status()

            return res
    except httpx.HTTPError as exc:
        log.error(f"HTTP request failed for {req.url}: {exc}")
        raise


def main():
    DATA_DIR = config.APP_SETTINGS.get("data_dir", ".data")
    if not Path(f"{DATA_DIR}").parent.exists():
        Path(f"{DATA_DIR}").parent.mkdir(parents=True, exist_ok=True)

    if not check_online():
        raise Exception("FarmRPG is down or undergoing maintenance")

    log.info("FarmRPG is online")

    current_prices_req = httpx.Request("GET", CURRENT_MARKET_PRICES_URL)

    log.info("Requesting current prices")
    log.debug(f"URL: {current_prices_req.url}")

    try:
        current_prices_res = send_request(current_prices_req)
    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed requesting current steak/kebob prices: {exc}"
        )
        raise

    log.info("Fetched current prices")
    current_prices_html = current_prices_res.text

    ## Use CurrentPricesRaw class
    raw_prices = CurrentPricesRaw(html=current_prices_html)
    raw_prices.save_html(output_dir=DATA_DIR)

    log.info("Saved raw HTML")

    steak_price = raw_prices.steak_price()
    kabob_price = raw_prices.kabob_price()

    log.info(f"Parsed prices: steak={steak_price}, kabob={kabob_price}")

    if steak_price is None or kabob_price is None:
        raise RuntimeError(
            f"Failed to locate steak/kabob price: steak={steak_price}, kabob={kabob_price}"
        )

    ## Now create the CurrentPrices object
    prices = CurrentPrices.from_raw(raw_prices, steak_price, kabob_price)

    log.info(f"Scraped prices: {prices}")


if __name__ == "__main__":
    setup.setup_logging(level=config.LOGGING_SETTINGS.get("LEVEL", "INFO"))
    main()
