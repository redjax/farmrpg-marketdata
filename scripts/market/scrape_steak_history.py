"""Scrape historic steak market prices from the FarmRPG page.

Steak price history: https://farmrpg.com/steakhistory.php
Kebab price history: https://farmrpg.com/steakhistoryk.php
"""

import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field

from shared import constants

from bs4 import BeautifulSoup
import httpx

import shared

log = logging.getLogger(__name__)


def generate_file_timestamp(ts_fmt: str = "%Y-%m-%d") -> str:
    ts = shared.time_utils.get_ts(fmt="str", custom=ts_fmt)

    return ts


def save_html_to_file(soup: BeautifulSoup, output_file: str):
    log.info(f"Saving HTML to file: {output_file}")
    html = soup.prettify()

    if not Path(str(output_file)).parent.exists():
        Path(str(output_file)).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(html)


@dataclass
class MarketPricesRaw:
    steak_html: str
    kebab_html: str
    init_timestamp: str = field(default_factory=generate_file_timestamp)

    def steak_soup(self) -> BeautifulSoup:
        try:
            steak_soup: BeautifulSoup = BeautifulSoup(self.steak_html, "html.parser")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed parsing steak price history HTML: {exc}"
            )
            raise

        return steak_soup

    def kebab_soup(self) -> BeautifulSoup:
        try:
            kebab_soup: BeautifulSoup = BeautifulSoup(self.kebab_html, "html.parser")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed parsing kebab price history HTML: {exc}"
            )
            raise

        return kebab_soup

    def save_steak_html(self, output_dir: str = ".data/history"):
        output_filename: str = f"{self.init_timestamp}_steak_prices.html"

        try:
            save_html_to_file(
                soup=self.steak_soup(), output_file=f"{output_dir}/{output_filename}"
            )
        except Exception as exc:
            log.error(f"({type(exc).__name__}) Failed saving steak prices HTML: {exc}")
            raise

    def save_kebab_html(self, output_dir: str = ".data/history"):
        output_filename: str = f"{self.init_timestamp}_kebab_prices.html"

        try:
            save_html_to_file(
                soup=self.kebab_soup(), output_file=f"{output_dir}/{output_filename}"
            )
        except Exception as exc:
            log.error(f"({type(exc).__name__}) Failed saving kebab prices HTML: {exc}")
            raise

    def parse_steak_prices(self) -> list[dict]:
        ## Parse steak prices
        try:
            steak_rows = self.steak_soup().select("div.card-content-inner > div.row")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed to extract steak price history table from HTML: {exc}"
            )
            raise

        data: list = []

        ## iterate over rows, skipping header
        try:
            for row in steak_rows[1:]:
                cols = row.find_all("div", class_="col-auto")

                if len(cols) == 4:
                    date = cols[0].get_text(strip=True)
                    price = cols[1].get_text(strip=True)
                    market = cols[2].get_text(strip=True)
                    volume = cols[3].get_text(strip=True)

                    row_data = {
                        "Date": date,
                        "Price": price,
                        "Market": market,
                        "Volume": volume,
                    }
                    # log.debug(f"Steak price row data: {row_data}")

                    data.append(row_data)
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed extracting steak price history into dict: {exc}"
            )
            raise

        return data

    def parse_kebab_prices(self) -> list[dict]:
        try:
            kebab_rows = self.kebab_soup().select("div.card-content-inner > div.row")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed to extract kebab price history table from HTML: {exc}"
            )
            raise

        data: list = []

        # iterate over rows, skipping header
        for row in kebab_rows[1:]:
            cols = row.find_all("div", class_="col-auto")

            if len(cols) == 2:
                time = cols[0].get_text(strip=True)
                price = cols[1].get_text(strip=True)

                row_data = {
                    "Time": time,
                    "Price": price,
                }
                data.append(row_data)

        return data


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


def main(
    save_prices: bool = False,
    log_level: str = "INFO",
    enable_file_logging: bool = False,
):
    log_file = None

    if enable_file_logging:
        log_file = "logs/steak_market.log"

    shared.setup_logging(level=log_level, file=log_file)
    log.debug("Debug logging enabled")

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

    if save_prices:
        market_prices.save_steak_html()
        market_prices.save_kebab_html()

    ## Parse price data
    steak_prices_parsed: list[dict] = market_prices.parse_steak_prices()
    # log.debug(f"Parsed steak prices:\n{steak_prices_parsed}")

    kebab_prices_parsed: list[dict] = market_prices.parse_kebab_prices()
    log.debug(f"Parsed kebab prices:\n{kebab_prices_parsed}")


if __name__ == "__main__":
    try:
        main(save_prices=True, log_level="DEBUG", enable_file_logging=True)
    except Exception as exc:
        print(f"[ERROR] ({type(exc)}) Failed to scrape current market prices")
        sys.exit(1)
