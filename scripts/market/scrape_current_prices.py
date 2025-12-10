import logging
from pathlib import Path

from marketdata.db import init_db
from marketdata import config, setup
from marketdata.controllers import FarmRPGMarketPricesController

log = logging.getLogger(__name__)


def main():
    with FarmRPGMarketPricesController(
        use_cache=True,
        save_html=True,
        save_to_db=True,
    ) as ctrl:

        if not ctrl.check_online():
            raise Exception("FarmRPG is down or undergoing maintenance")

        log.info("FarmRPG is online")

        prices = ctrl.get_current_prices()

        log.info(f"Scraped current prices: {prices}")


if __name__ == "__main__":
    setup.setup_logging(level=config.LOGGING_SETTINGS.get("LEVEL", "INFO"))
    try:
        init_db()
    except Exception as exc:
        log.error(f"({type(exc).__name__}) Failed to initialize database: {exc}")
        raise

    main()
