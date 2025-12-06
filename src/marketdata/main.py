"""Scrape historic steak market prices from the FarmRPG page.

Steak price history: https://farmrpg.com/steakhistory.php
Kebab price history: https://farmrpg.com/steakhistoryk.php
"""

import logging
import sys

from marketdata import constants

import httpx

from marketdata import shared
from marketdata import setup
from marketdata.classes import MarketPricesRaw

log = logging.getLogger(__name__)

__all__ = ["run_scraper", "main"]


def check_online(use_cache: bool = True) -> bool:
    """Check if FarmRPG is online and not in maintenance mode.

    Params:
        use_cache (bool): Whether to use the shared caching transport.

    Returns:
        bool: True if the server is online and active, False otherwise.
    """
    url = "https://farmrpg.com/index.php"
    maintenance_keywords = ["Server Reset", "will be right back"]

    try:
        request = httpx.Request(method="GET", url=url)
        response: httpx.Response = shared.http_utils.send_request(
            request, use_cache=use_cache
        )
    except Exception as exc:
        log.error(f"[check_online] Request failed: {exc}")
        return False

    if response.status_code != 200:
        log.warning(
            f"[check_online] Server returned status code {response.status_code}"
        )
        return False

    html = response.text

    if any(kw in html for kw in maintenance_keywords):
        log.warning("[check_online] FarmRPG appears to be in maintenance mode.")
        return False

    log.info("[check_online] FarmRPG is online and not in maintenance mode.")

    return True


def request_market_prices() -> MarketPricesRaw:
    steak_url: str = constants.STEAK_HISTORY_URL
    kebab_url: str = constants.KEBAB_HISTORY_URL
    log.debug(f"Steak URL: {steak_url}")
    log.debug(f"Kebab URL: {kebab_url}")

    steak_prices_req: httpx.Request = httpx.Request(method="GET", url=steak_url)
    kebab_prices_req: httpx.Request = httpx.Request(method="GET", url=kebab_url)

    log.info("Requesting steak prices HTML")
    steak_prices_res: httpx.Response = shared.http_utils.send_request(steak_prices_req)
    steak_prices_html = steak_prices_res.content.decode("utf-8")
    # log.debug(f"Steak prices HTML raw:\n{steak_prices_html}")

    log.info("Requesting kebab prices HTML")
    kebab_prices_res: httpx.Response = shared.http_utils.send_request(kebab_prices_req)
    kebab_prices_html = kebab_prices_res.content.decode("utf-8")
    # log.debug(f"Kebab prices HTML raw:\n{kebab_prices_html}")

    return MarketPricesRaw(steak_html=steak_prices_html, kebab_html=kebab_prices_html)


def run_scraper(save_prices_html: bool = False):
    ## Ensure website is up/not in maintenance mode
    if not check_online(use_cache=True):
        log.error("FarmRPG is offline or undergoing maintenance")

        return

    log.info("Requesting market prices for steak & kebabs")
    try:
        market_prices: MarketPricesRaw = request_market_prices()
    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed requesting current steak prices: {exc}"
        )
        raise

    ## Parse steak prices
    log.info("Parsing steak market price history")
    try:
        steak_soup = market_prices.steak_soup()
    except Exception as exc:
        raise

    ## Parse kebab steak prices
    log.info("Parsing kebab market price history")
    try:
        kebab_soup = market_prices.kebab_soup()
    except Exception as exc:
        raise

    if save_prices_html:
        market_prices.save_steak_html()
        market_prices.save_kebab_html()

    ## Parse price data
    steak_prices_parsed: list[dict] = market_prices.parse_steak_prices()
    log.debug(f"Parsed steak prices:\n{steak_prices_parsed}")

    kebab_prices_parsed: list[dict] = market_prices.parse_kebab_prices()
    log.debug(f"Parsed kebab prices:\n{kebab_prices_parsed}")


def main(
    save_prices_html: bool = False,
    log_level: str = "INFO",
    enable_file_logging: bool = False,
):
    log_file = None

    if enable_file_logging:
        log_file = "logs/steak_market.log"

    setup.setup_logging(level=log_level, file=log_file)
    log.debug("Debug logging enabled")

    try:
        run_scraper(save_prices=save_prices_html)
    except Exception as exc:
        raise


if __name__ == "__main__":
    try:
        main(save_prices_html=True, log_level="DEBUG", enable_file_logging=True)
    except Exception as exc:
        print(f"[ERROR] ({type(exc).__name__}) Failed to scrape current market prices")
        sys.exit(1)
