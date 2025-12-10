import logging
import time

from marketdata.scheduler.schedules import MarketScraperScheduler
from marketdata.setup import setup_logging
from marketdata import config
from marketdata import db

log = logging.getLogger(__name__)


def main():
    setup_logging(
        level=config.LOGGING_SETTINGS.get("LEVEL", "INFO"),
        file=config.LOGGING_SETTINGS.get("FILE_PATH", ""),
    )

    try:
        db.init_db()
    except Exception as exc:
        log.error(f"({type(exc).__name__}) Error initializing database: {exc}")
        raise

    scheduler = MarketScraperScheduler(
        cron_expr=config.PRICES_SETTINGS.get("SCHEDULE", "0 * * * *"),
        use_cache=config.HTTP_SETTINGS.get("USE_CACHE", False),
        save_html=config.PRICES_SETTINGS.get("SAVE_HTML", False),
        save_to_db=config.PRICES_SETTINGS.get("SAVE_TO_DB", False),
    )
    scheduler.start()

    ## Keep the script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":

    main()
