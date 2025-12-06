from pathlib import Path
import logging
from dataclasses import dataclass, field

from . import time_utils

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

__all__ = ["MarketPricesRaw"]


def generate_file_timestamp(ts_fmt: str = "%Y-%m-%d") -> str:
    ts = time_utils.get_ts(fmt="str", custom=ts_fmt)

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
