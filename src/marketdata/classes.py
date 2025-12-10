import typing as t
from pathlib import Path
import logging
from dataclasses import dataclass, field
import datetime as dt

from bs4 import BeautifulSoup
from marketdata.shared import time_utils

log = logging.getLogger(__name__)

__all__ = [
    "MarketPricesRaw",
    "MarketPrices",
    "SteakPriceIn",
    "KebabPriceIn",
    "CurrentPricesRaw",
    "CurrentPrices",
]


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
class SteakPriceIn:
    date: dt.date
    price: int
    market: str
    volume: int


@dataclass
class KebabPriceIn:
    timestamp: dt.datetime
    price: int


@dataclass
class CurrentPriceIn:
    """Current steak/kabob price snapshot"""

    timestamp: dt.datetime
    steak_price: int
    kabob_price: int


@dataclass
class CurrentPrices:
    """Current market prices DTO"""

    current: CurrentPriceIn
    init_timestamp: str = field(default_factory=generate_file_timestamp)

    @classmethod
    def from_raw(
        cls, raw: "CurrentPricesRaw", steak_price: int, kabob_price: int
    ) -> "CurrentPrices":
        """Create from raw HTML data + already-extracted prices"""
        return cls(
            current=CurrentPriceIn(
                timestamp=dt.datetime.now(),
                steak_price=steak_price,
                kabob_price=kabob_price,
            )
        )


@dataclass
class CurrentPricesRaw:
    """Raw HTML data for current steak/kabob prices"""

    html: str
    init_timestamp: str = field(default_factory=generate_file_timestamp)

    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.html, "html.parser")

    def save_html(self, output_dir: str = ".data/current"):
        save_html_to_file(
            self.soup(), f"{output_dir}/{self.init_timestamp}_current_prices.html"
        )

    def _normalize_price(self, price_text: str) -> t.Optional[int]:
        if not price_text:
            return None
        cleaned = (
            price_text.replace(",", "")
            .replace("Silver", "")
            .replace("G", "")
            .replace("g", "")
            .strip()
        )
        try:
            return int(cleaned)
        except ValueError:
            return None

    def steak_price(self) -> t.Optional[int]:
        """Extract current steak price"""
        soup = self.soup()
        results = {"steak": None, "kabob": None}

        price_containers = soup.find_all(
            string=lambda text: text and "Current Market Price:" in text
        )

        for container in price_containers:
            parent = container.parent

            if not parent:
                continue

            strong_el = parent.find("strong")

            if strong_el:
                raw_price = strong_el.get_text(strip=True)
                price = self._normalize_price(raw_price)

                ## Determine steak vs kabob by context
                parent_text = parent.get_text().lower()

                if "kabob" in parent_text:
                    results["kabob"] = price
                elif results["steak"] is None:
                    results["steak"] = price

        ## Fallback: first/second containers
        if results["steak"] is None and price_containers:
            first_strong = price_containers[0].parent.find("strong")

            if first_strong:
                results["steak"] = self._normalize_price(
                    first_strong.get_text(strip=True)
                )

        return results["steak"]

    def kabob_price(self) -> t.Optional[int]:
        """Extract current kabob price"""
        soup = self.soup()
        results = {"steak": None, "kabob": None}

        price_containers = soup.find_all(
            string=lambda text: text and "Current Market Price:" in text
        )

        for container in price_containers:
            parent = container.parent

            if not parent:
                continue

            strong_el = parent.find("strong")

            if strong_el:
                raw_price = strong_el.get_text(strip=True)
                price = self._normalize_price(raw_price)

                parent_text = parent.get_text().lower()

                if "kabob" in parent_text:
                    return price

        ## Fallback: second container
        if len(price_containers) >= 2:
            second_strong = price_containers[1].parent.find("strong")

            if second_strong:
                return self._normalize_price(second_strong.get_text(strip=True))

        return None

    @property
    def prices(self) -> dict[str, t.Optional[int]]:
        """Get both prices as dict for quick access"""
        return {"steak": self.steak_price(), "kabob": self.kabob_price()}


@dataclass
class MarketPrices:
    steak_prices: list[SteakPriceIn] = field(default_factory=list)
    kebab_prices: list[KebabPriceIn] = field(default_factory=list)

    def load_from_raw(self, raw: "MarketPricesRaw"):
        """
        Parses the raw HTML data and stores the results as dataclass objects.
        """
        ## Parse and convert steak prices
        self.steak_prices = [
            SteakPriceIn(
                date=row["Date"],
                price=int(row["Price"].replace(",", "")),
                market=row["Market"],
                volume=int(row["Volume"].replace(",", "")),
            )
            for row in raw.parse_steak_prices()
        ]

        # Parse and convert kebab prices
        self.kebab_prices = [
            KebabPriceIn(
                timestamp=row["Time"],
                price=int(row["Price"].replace(",", "")),
            )
            for row in raw.parse_kebab_prices()
        ]


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

    def get_parsed_market_prices_history(self) -> MarketPrices:
        """Return MarketPrices DTO with parsed steak & kebab market prices."""
        steak_prices = [
            SteakPriceIn(
                date=row["Date"],
                price=int(row["Price"].replace(",", "")),
                market=row["Market"],
                volume=int(row["Volume"].replace(",", "")),
            )
            for row in self.parse_steak_prices()
        ]

        kebab_prices = [
            KebabPriceIn(
                timestamp=row["Time"],
                price=int(row["Price"].replace(",", "")),
            )
            for row in self.parse_kebab_prices()
        ]

        return MarketPrices(steak_prices=steak_prices, kebab_prices=kebab_prices)

    def steak_soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.steak_html, "html.parser")

    def kebab_soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.kebab_html, "html.parser")

    def save_steak_html(self, output_dir: str = ".data/history"):
        save_html_to_file(
            self.steak_soup(), f"{output_dir}/{self.init_timestamp}_steak_prices.html"
        )

    def save_kebab_html(self, output_dir: str = ".data/history"):
        save_html_to_file(
            self.kebab_soup(), f"{output_dir}/{self.init_timestamp}_kebab_prices.html"
        )

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
