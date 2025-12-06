from pathlib import Path
import logging
from dataclasses import dataclass, field
import datetime as dt

from bs4 import BeautifulSoup
from marketdata.shared import time_utils

log = logging.getLogger(__name__)

__all__ = ["MarketPricesRaw"]


def generate_file_timestamp(ts_fmt: str = "%Y-%m-%d") -> str:
    return time_utils.get_ts(fmt="str", custom=ts_fmt)


def save_html_to_file(soup: BeautifulSoup, output_file: str):
    log.info(f"Saving HTML to file: {output_file}")
    html = soup.prettify()

    output_path = Path(output_file)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write(html)


@dataclass
class MarketPricesRaw:
    steak_html: str
    kebab_html: str
    init_timestamp: str = field(default_factory=generate_file_timestamp)

    _steak_prices_dt_cache: list[dict] | None = field(
        default=None, init=False, repr=False
    )
    _kebab_prices_dt_cache: list[dict] | None = field(
        default=None, init=False, repr=False
    )

    # --- HTML parsing ---
    def steak_soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.steak_html, "html.parser")

    def kebab_soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.kebab_html, "html.parser")

    # --- HTML saving ---
    def save_steak_html(self, output_dir: str = ".data/history"):
        save_html_to_file(
            self.steak_soup(), f"{output_dir}/{self.init_timestamp}_steak_prices.html"
        )

    def save_kebab_html(self, output_dir: str = ".data/history"):
        save_html_to_file(
            self.kebab_soup(), f"{output_dir}/{self.init_timestamp}_kebab_prices.html"
        )

    # --- Parsing directly to datetimes ---
    def parse_steak_prices(self) -> list[dict]:
        try:
            rows = self.steak_soup().select("div.card-content-inner > div.row")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed extracting steak price table: {exc}"
            )
            raise

        data = []
        today = dt.date.today()
        for row in rows[1:]:
            cols = row.find_all("div", class_="col-auto")
            if len(cols) != 4:
                continue

            # Parse date string immediately
            date_str = cols[0].get_text(strip=True)
            dt_obj = dt.datetime.strptime(date_str, "%b %d").date()
            dt_obj = dt_obj.replace(year=today.year)
            if dt_obj > today:
                dt_obj = dt_obj.replace(year=today.year - 1)

            row_data = {
                "Date": dt_obj,
                "Price": cols[1].get_text(strip=True),
                "Market": cols[2].get_text(strip=True),
                "Volume": cols[3].get_text(strip=True),
            }
            data.append(row_data)
        return data

    def parse_kebab_prices(self) -> list[dict]:
        try:
            rows = self.kebab_soup().select("div.card-content-inner > div.row")
        except Exception as exc:
            log.error(
                f"({type(exc).__name__}) Failed extracting kebab price table: {exc}"
            )
            raise

        data = []
        now = dt.datetime.now()
        today = dt.date.today()
        current_year = today.year

        for row in rows[1:]:
            cols = row.find_all("div", class_="col-auto")
            if len(cols) != 2:
                continue

            time_str = cols[0].get_text(strip=True)
            dt_obj = dt.datetime.strptime(
                f"{time_str} {current_year}", "%b %d, %I %p %Y"
            )
            if dt_obj > now:
                dt_obj = dt.datetime.strptime(
                    f"{time_str} {current_year - 1}", "%b %d, %I %p %Y"
                )

            row_data = {
                "Time": dt_obj,
                "Price": cols[1].get_text(strip=True),
            }
            data.append(row_data)
        return data

    # --- Public access with caching ---
    def steak_prices_dt(self, use_cache: bool = True) -> list[dict]:
        if use_cache and self._steak_prices_dt_cache is not None:
            return self._steak_prices_dt_cache
        self._steak_prices_dt_cache = self.parse_steak_prices()
        return self._steak_prices_dt_cache

    def kebab_prices_dt(self, use_cache: bool = True) -> list[dict]:
        if use_cache and self._kebab_prices_dt_cache is not None:
            return self._kebab_prices_dt_cache
        self._kebab_prices_dt_cache = self.parse_kebab_prices()
        return self._kebab_prices_dt_cache
