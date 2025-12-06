import logging
import time

from marketdata.scheduler.schedules import MarketScraperScheduler
from marketdata.setup import setup_logging

log = logging.getLogger(__name__)


def main():
    ## Run the scraper every hour
    scheduler = MarketScraperScheduler(
        cron_expr="*/1 * * * *", use_cache=True, save_html=True, save_to_db=True
    )
    scheduler.start()

    ## Keep the script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    setup_logging(level="DEBUG")

    main()
