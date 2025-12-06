import sys
import logging

from marketdata import run_scraper
from marketdata.setup import setup_logging

import marketdata.shared as shared

log = logging.getLogger(__name__)


def main(
    save_market_prices_html: bool = False,
    log_level: str = "INFO",
    enable_file_logging: bool = False,
):
    log_file = None

    if enable_file_logging:
        log_file = "logs/steak_market.log"

    setup_logging(level=log_level, file=log_file)
    log.debug("Debug logging enabled")

    try:
        run_scraper(save_prices_html=save_market_prices_html)
    except Exception as exc:
        raise


if __name__ == "__main__":
    try:
        main(save_market_prices_html=True, log_level="DEBUG", enable_file_logging=True)
    except Exception as exc:
        print(f"[ERROR] ({type(exc)}) Failed to scrape current market prices: {exc}")
        sys.exit(1)
