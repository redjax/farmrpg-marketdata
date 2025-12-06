import sys
import logging

from marketdata import run_scraper
from marketdata.setup import setup_logging
from marketdata.db import init_db, get_session
from marketdata.models import SteakPriceModel, KebabPriceModel
from marketdata.classes import MarketPricesRaw

import marketdata.shared as shared

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

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
        init_db()
    except Exception as exc:
        log.error(f"({type(exc).__name__}) Failed to initialize database: {exc}")
        raise

    try:
        market_prices = run_scraper(save_prices_html=save_market_prices_html)
    except Exception as exc:
        raise

    log.info("Saving market prices to database")
    ## Save to database
    try:
        with get_session() as session:
            ## Save steak prices
            log.info("Saving steak prices")
            for s in market_prices.steak_prices:
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
            for k in market_prices.kebab_prices:
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


if __name__ == "__main__":
    try:
        main(save_market_prices_html=True, log_level="DEBUG", enable_file_logging=True)
    except Exception as exc:
        print(f"[ERROR] ({type(exc)}) Failed to scrape current market prices: {exc}")
        sys.exit(1)
