import logging
from contextlib import AbstractContextManager
import typing as t

from marketdata import constants
from marketdata import shared
from marketdata import db
from marketdata.classes import (
    SteakPriceIn,
    KebabPriceIn,
    MarketPrices,
    MarketPricesRaw,
    CurrentPriceIn,
    CurrentPrices,
    CurrentPricesRaw,
)
from marketdata.models import (
    KebabPriceModel,
    SteakPriceModel,
    SteakPriceCurrentModel,
    KebabPriceCurrentModel,
)

import sqlalchemy.orm as so
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import httpx

log = logging.getLogger(__name__)

__all__ = ["FarmRPGMarketPricesController"]


class FarmRPGMarketPricesController(AbstractContextManager):
    STEAK_PRICES_URL: str = constants.STEAK_HISTORY_URL
    KEBAB_PRICES_URL: str = constants.KEBAB_HISTORY_URL

    def __init__(
        self,
        use_cache: bool = False,
        cache_ttl: int = 3600,
        cache_db_file: str = ".cache/http_cache.db",
        save_html: bool = False,
        save_to_db: bool = False,
        session_factory=db.get_session,
        external_http_client: httpx.Client | None = None,
    ):
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.cache_db_file = cache_db_file
        self.save_html = save_html
        self.save_to_db = save_to_db
        self._external_client = external_http_client

        self.session_factory = session_factory
        self._session: so.Session | None = None

        self._http_client: httpx.Client | None = None

        if self._external_client:
            self._http_client = self._external_client

    def __enter__(self) -> t.Self:
        if self.save_to_db:
            ## Initialize session for context manager
            self._session = self.session_factory().__enter__()

        if self._http_client is None:
            self._http_client = shared.http_utils.get_client(
                use_cache=self.use_cache,
                cache_db_file=self.cache_db_file,
                cache_ttl=self.cache_ttl,
            )

        return self

    def __exit__(self, exc_type, exc, tb):
        if self._session is not None:
            if exc:
                log.error(
                    f"({exc_type}) Error inside controller context: {exc}. Rolling back DB."
                )
                self._session.rollback()
            else:
                self._session.commit()
                log.debug("Controller committed DB changes.")
            self._session.close()

        ## Only close if internal
        if self._http_client is not None and self._external_client is None:
            self._http_client.close()

        return False

    def _ensure_initialized(self):
        """Lazy init of HTTP client and DB session if needed."""
        if self._http_client is None:
            self._http_client = shared.http_utils.get_client(
                use_cache=self.use_cache,
                cache_db_file=self.cache_db_file,
                cache_ttl=self.cache_ttl,
            )

        if self.save_to_db and self._session is None:
            ## Use context manager to get a real session
            self._session = self.session_factory().__enter__()

    def save_current_prices(self, prices: CurrentPrices):
        """Save current prices to database if enabled."""
        if not self.save_to_db:
            return

        if self._session is None:
            with self.session_factory() as session:
                self._save_current_prices_in_session(session, prices)
            return

        self._save_current_prices_in_session(self._session, prices)

    def _send_request(self, req: httpx.Request) -> str:
        """Send HTTP request using internal client."""
        self._ensure_initialized()

        try:
            resp = self._http_client.send(req)
            resp.raise_for_status()

            return resp.text
        except httpx.HTTPError as exc:
            log.error(f"HTTP request failed for {req.url}: {exc}")
            raise

    def _save_to_db(self, prices: MarketPrices):
        """Save parsed prices to database if enabled."""
        if not self.save_to_db:
            return

        if self._session is None:
            ## Fallback for direct-call usage
            with self.session_factory() as session:
                self._save_prices_in_session(session, prices)

            return

        ## Inside context manager
        self._save_prices_in_session(self._session, prices)

    def _save_current_prices_in_session(
        self, session: so.Session, prices: CurrentPrices
    ):
        """Save current steak/kabob prices to database."""
        try:
            log.info("Saving current steak price")
            stmt = (
                sqlite_insert(SteakPriceCurrentModel)
                .values(
                    timestamp=prices.current.timestamp, price=prices.current.steak_price
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "timestamp": prices.current.timestamp,
                        "price": prices.current.steak_price,
                    },
                )
            )
            session.execute(stmt)

            log.info("Saving current kebab price")
            stmt = (
                sqlite_insert(KebabPriceCurrentModel)
                .values(
                    timestamp=prices.current.timestamp, price=prices.current.kabob_price
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "timestamp": prices.current.timestamp,
                        "price": prices.current.kabob_price,
                    },
                )
            )
            session.execute(stmt)

        except Exception as exc:
            log.error(f"Failed to save current prices: {exc}")
            raise

    def _save_prices_in_session(self, session: so.Session, prices: MarketPrices):
        try:
            log.info("Saving steak prices")
            for s in prices.steak_prices:
                stmt = (
                    sqlite_insert(SteakPriceModel)
                    .values(
                        date=s.date, price=s.price, market=s.market, volume=s.volume
                    )
                    .on_conflict_do_nothing()
                )

                session.execute(stmt)

            log.info("Saving kebab prices")
            for k in prices.kebab_prices:
                stmt = (
                    sqlite_insert(KebabPriceModel)
                    .values(timestamp=k.timestamp, price=k.price)
                    .on_conflict_do_nothing()
                )

                session.execute(stmt)

            session.commit()

        except Exception as exc:
            log.error(f"({type(exc).__name__}) Failed to save prices: {exc}")
            raise

    def check_online(self) -> bool:
        """Check if FarmRPG is online."""
        req = httpx.Request("GET", constants.HOME_URL)
        maintenance_keywords = ["Server Reset", "will be right back"]

        try:
            html = self._send_request(req)
        except Exception:
            return False

        if any(kw in html for kw in maintenance_keywords):
            log.warning("FarmRPG maintenance mode detected")
            return False

        return True

    def get_price_history(self) -> MarketPrices:
        """Scrape, parse, optionally save HTML and DB."""
        self._ensure_initialized()
        log.info("Requesting market price pages")

        steak_html: httpx.Response = self._send_request(
            httpx.Request("GET", self.STEAK_PRICES_URL)
        )
        kebab_html: httpx.Response = self._send_request(
            httpx.Request("GET", self.KEBAB_PRICES_URL)
        )

        raw: MarketPricesRaw = MarketPricesRaw(
            steak_html=steak_html, kebab_html=kebab_html
        )

        if self.save_html:
            raw.save_steak_html()
            raw.save_kebab_html()

        log.info("Parsing market prices")
        parsed: MarketPrices = raw.get_parsed_market_prices_history()

        if self.save_to_db:
            self._save_to_db(parsed)

        return parsed

    def get_current_prices(self) -> CurrentPrices:
        """Scrape, parse, optionally save current prices and DB."""
        self._ensure_initialized()
        log.info("Requesting current prices")

        current_html = self._send_request(
            httpx.Request("GET", constants.CURRENT_MARKET_PRICES_URL)
        )

        raw: CurrentPricesRaw = CurrentPricesRaw(html=current_html)

        if self.save_html:
            raw.save_html()

        log.info("Parsing current prices")
        steak_price = raw.steak_price()
        kabob_price = raw.kabob_price()

        if steak_price is None or kabob_price is None:
            raise RuntimeError(
                f"Failed to parse prices: steak={steak_price}, kabob={kabob_price}"
            )

        parsed: CurrentPrices = CurrentPrices.from_raw(raw, steak_price, kabob_price)

        if self.save_to_db:
            self.save_current_prices(parsed)

        return parsed
