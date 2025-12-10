import logging
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from marketdata.controllers import FarmRPGMarketPricesController

log = logging.getLogger(__name__)


class MarketScraperScheduler:
    def __init__(
        self, cron_expr="*/1 * * * *", use_cache=True, save_html=False, save_to_db=True
    ):
        from marketdata.shared import http_utils

        self.cron_expr = cron_expr
        self.scheduler = BlockingScheduler()
        self.controller_kwargs = dict(
            use_cache=use_cache, save_html=save_html, save_to_db=save_to_db
        )

        ## Initialize client in main thread to avoid SSL errors running in scheduler
        self._http_client = http_utils.get_client(use_cache=use_cache)

    def _run_scraper(self):
        try:
            log.info("Scheduled job starting: scraping FarmRPG market prices.")
            with FarmRPGMarketPricesController(
                **self.controller_kwargs, external_http_client=self._http_client
            ) as controller:
                ## Inject client into controller
                controller._http_client = self._http_client

                market_prices_history = controller.get_price_history()

                log.info(
                    f"Scraper run completed. Parsed {len(market_prices_history.steak_prices)} steak prices "
                    f"and {len(market_prices_history.kebab_prices)} kebab prices."
                )
        except Exception as exc:
            log.error(f"Scheduled job failed: ({type(exc).__name__}) {exc}")

    def start(self):
        """Start the APScheduler with the cron expression."""
        trigger = CronTrigger.from_crontab(self.cron_expr)
        self.scheduler.add_job(
            self._run_scraper, trigger, id="farmrpg_scraper", replace_existing=True
        )
        self.scheduler.start()
        log.info(f"Market scraper scheduler started with cron: '{self.cron_expr}'")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        log.info("Market scraper scheduler stopped.")
