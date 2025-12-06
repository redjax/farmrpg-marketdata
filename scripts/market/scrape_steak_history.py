"""Scrape historic steak market prices from the FarmRPG page.

Steak price history: https://farmrpg.com/steakhistory.php
Kebab price history: https://farmrpg.com/steakhistoryk.php
"""

import logging
from shared import constants

from bs4 import BeautifulSoup
import httpx

import shared

log = logging.getLogger(__name__)


def main(log_level: str = "INFO", enable_file_logging: bool = False):
    log_file = None

    if enable_file_logging:
        log_file = "logs/steak_market.log"

    shared.setup_logging(level=log_level, file=log_file)
    log.debug("Debug logging enabled")

    client: httpx.Client = shared.http_utils.get_client(use_cache=True)

    steak_url: str = constants.STEAK_HISTORY_URL
    kebab_url: str = constants.KEBAB_HISTORY_URL
    log.debug(f"Steak URL: {steak_url}")
    log.debug(f"Kebab URL: {kebab_url}")

    steak_prices_req: httpx.Request = httpx.Request(method="GET", url=steak_url)
    kebab_prices_req: httpx.Request = httpx.Request(method="GET", url=kebab_url)

    log.info("Requesting steak prices HTML")
    steak_prices_res: httpx.Response = shared.http_utils.send_request(steak_prices_req)

    log.info("Requesting kebab prices HTML")
    kebab_prices_res: httpx.Response = shared.http_utils.send_request(kebab_prices_req)


if __name__ == "__main__":
    main(log_level="DEBUG", enable_file_logging=True)
