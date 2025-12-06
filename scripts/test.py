import sys
import logging

from marketdata import run_scraper
from marketdata.setup import setup_logging
from marketdata.db import init_db, get_session
from marketdata.models import SteakPriceModel, KebabPriceModel
from marketdata.classes import MarketPricesRaw, MarketPrices
from marketdata.controllers import FarmRPGMarketPricesController

import marketdata.shared as shared

log = logging.getLogger(__name__)


def main():
    price_controller: FarmRPGMarketPricesController = FarmRPGMarketPricesController(
        use_cache=True, save_html=True, save_to_db=True
    )

    if not price_controller.check_online():
        log.error("FarmRPG is offline or down for mainteance")

        return

    log.info("FarmRPG is online, proceeding")

    ## Run scraper
    try:
        market_prices: MarketPrices = price_controller.run()
    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed to scrape FarmRPG market prices. Details: {exc}"
        )
        raise


if __name__ == "__main__":
    setup_logging(level="DEBUG")
    log.debug("Debug logging enabled")

    try:
        init_db()
    except Exception as exc:
        log.error(f"({type(exc).__name__}) Failed to initialize database: {exc}")
        raise

    main()
