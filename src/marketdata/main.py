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
from marketdata.classes import MarketPricesRaw, MarketPrices, SteakPriceIn, KebabPriceIn
from marketdata.models import SteakPriceModel, KebabPriceModel
from marketdata.db import get_session
from marketdata.config import (
    SETTINGS,
    DB_SETTINGS,
    HTTP_SETTINGS,
    LOGGING_SETTINGS,
    PRICES_SETTINGS,
)

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

log = logging.getLogger(__name__)

__all__ = ["run_scraper", "check_online", "save_market_prices_history_to_db", "main"]


def check_online(use_cache: bool = True) -> bool:
    """Check if FarmRPG is online and not in maintenance mode.

    Params:
        use_cache (bool): Whether to use the shared caching transport.

    Returns:
        bool: True if the server is online and active, False otherwise.
    """
    url: str = constants.HOME_URL
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


def request_market_prices_history_history() -> MarketPricesRaw:
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


def run_scraper(
    save_prices_html: bool = PRICES_SETTINGS.get("SAVE_HTML", False),
    save_prices_to_db: bool = PRICES_SETTINGS.get("SAVE_TO_DB", False),
):
    ## Ensure website is up/not in maintenance mode
    if not check_online(use_cache=True):
        log.error("FarmRPG is offline or undergoing maintenance")

        return

    log.info("Requesting market prices for steak & kebabs")
    try:
        market_prices_history: MarketPricesRaw = request_market_prices_history()
    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed requesting current steak prices: {exc}"
        )
        raise

    if save_prices_html:
        market_prices_history.save_steak_html()
        market_prices_history.save_kebab_html()

    ## Create object for passing price data around app
    prices_obj: MarketPrices = market_prices_history.get_parsed_market_prices_history()

    # log.debug(f"Market Prices: {prices_obj}")

    if save_prices_to_db:
        save_market_prices_to_db(market_prices_history=prices_obj)

    return prices_obj


def save_market_prices_history_to_db(market_prices_history: MarketPrices):
    log.info("Saving market prices to database")
    ## Save to database
    try:
        with get_session() as session:
            ## Save steak prices
            log.info("Saving steak prices")
            for s in market_prices_history.steak_prices:
                stmt = (
                    sqlite_insert(SteakPriceModel)
                    .values(
                        date=s.date,
                        price=s.price,
                        market=s.market,
                        volume=s.volume,
                    )
                    .on_conflict_do_nothing()
                )
                session.execute(stmt)

            ## Save kebab prices
            log.info("Saving kebab prices")
            for k in market_prices_history.kebab_prices:
                stmt = (
                    sqlite_insert(KebabPriceModel)
                    .values(
                        timestamp=k.timestamp,
                        price=k.price,
                    )
                    .on_conflict_do_nothing()
                )
                session.execute(stmt)

            session.commit()

    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed to save market prices to database: {exc}"
        )
        raise


def main(
    save_prices_html: bool = False,
    save_prices_to_db: bool = False,
    log_level: str = "INFO",
    log_file: str = "",
):
    setup.setup_logging(level=log_level, file=log_file)
    log.debug("Debug logging enabled")

    try:
        market_prices_history: MarketPrices = run_scraper(
            save_prices=save_prices_html, save_prices_to_db=save_prices_to_db
        )
    except Exception as exc:
        raise


if __name__ == "__main__":
    try:
        main(
            save_prices_html=PRICES_SETTINGS.get("SAVE_HTML", False),
            save_prices_to_db=PRICES_SETTINGS.get("SAVE_TO_DB", False),
            log_level=LOGGING_SETTINGS.get("LEVEL", "INFO"),
            log_file=LOGGING_SETTINGS.get("FILE_PATH", ""),
        )
    except Exception as exc:
        print(f"[ERROR] ({type(exc).__name__}) Failed to scrape current market prices")
        sys.exit(1)
