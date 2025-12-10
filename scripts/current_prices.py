import logging
import typing as t
from pathlib import Path

from marketdata import config
from marketdata.shared import http_utils
from marketdata.constants import CURRENT_MARKET_PRICES_URL, HOME_URL
from marketdata import shared
from marketdata import setup

from bs4 import BeautifulSoup
import httpx

log = logging.getLogger(__name__)


def check_online() -> bool:
    req = httpx.Request("GET", HOME_URL)
    maintenance_keywords = ["Server Reset", "will be right back"]

    try:
        html = send_request(req, use_cache=False)
    except Exception:
        return False

    if any(kw in html.text for kw in maintenance_keywords):
        log.warning("FarmRPG maintenance mode detected")
        return False

    return True


def send_request(req: httpx.Request, use_cache: bool = True) -> httpx.Response:
    client = shared.http_utils.get_client(use_cache=use_cache)

    try:
        with client as http:
            res: httpx.Response = http.send(req)
            res.raise_for_status()

            return res
    except httpx.HTTPError as exc:
        log.error(f"HTTP request failed for {req.url}: {exc}")
        raise


def extract_steak_kabob_prices(html: str) -> dict[str, t.Optional[int]]:
    def _normalize_price(price_text: str) -> int:
        cleaned = (
            price_text.replace(",", "")
            .replace("Silver", "")
            .replace("G", "")
            .replace("g", "")
            .strip()
        )

        return int(cleaned)

    soup = BeautifulSoup(html, "html.parser")
    results: dict[str, t.Optional[int]] = {
        "steak": None,
        "kabob": None,
    }

    ## Find all "Current Market Price:" elements by searching text anywhere
    price_containers = soup.find_all(
        string=lambda text: text and "Current Market Price:" in text
    )

    for container in price_containers:
        ## Get the parent card-content-inner
        parent = container.parent
        if not parent:
            continue

        ## Find the <strong> tag within this parent
        strong_el = parent.find("strong")
        if strong_el:
            raw_price = strong_el.get_text(strip=True)
            price = _normalize_price(raw_price)

            ## Determine steak vs kabob by looking at surrounding context
            #  Check the full page content before/after this price block
            full_page_text = soup.get_text().lower()
            parent_text = parent.get_text().lower()

            ## Look for section headers nearby
            prev_section = parent.find_previous("div", class_="content-block-title")
            next_section = parent.find_next("div", class_="content-block-title")

            section_context = ""
            if prev_section:
                section_context += prev_section.get_text().lower()
            if next_section:
                section_context += next_section.get_text().lower()

            section_context += parent_text

            if any(word in section_context for word in ["kabob", "kabobs"]):
                results["kabob"] = price
            elif results["steak"] is None:
                ## First price is steak (appears first in HTML)
                results["steak"] = price

    ## Fallback: if context detection fails, assign first price to steak, second to kabob
    if results["steak"] is None and len(price_containers) >= 1:
        first_strong = price_containers[0].parent.find("strong")
        if first_strong:
            results["steak"] = _normalize_price(first_strong.get_text(strip=True))

    if results["kabob"] is None and len(price_containers) >= 2:
        second_strong = price_containers[1].parent.find("strong")
        if second_strong:
            results["kabob"] = _normalize_price(second_strong.get_text(strip=True))

    return results


def main():
    DATA_DIR = config.APP_SETTINGS.get("data_dir", ".data")
    if not Path(f"{DATA_DIR}").parent.exists():
        Path(f"{DATA_DIR}").parent.mkdir(parents=True, exist_ok=True)
    if not check_online():
        raise Exception("FarmRPG is down or undergoing maintenance")
    log.info("FarmRPG is online")

    current_prices_req = httpx.Request("GET", CURRENT_MARKET_PRICES_URL)

    log.info("Requesting current prices")
    log.debug(f"URL: {current_prices_req.url}")
    try:
        current_prices_res = send_request(current_prices_req)
    except Exception as exc:
        log.error(
            f"({type(exc).__name__}) Failed requesting current steak/kebob prices: {exc}"
        )
        raise

    log.info("Fetched current prices")

    current_prices_html = current_prices_res.text

    log.info("Saving results")
    with open(f"{DATA_DIR}/current_prices.html", "w") as f:
        f.write(current_prices_html)

    ## Parse response
    prices = extract_steak_kabob_prices(current_prices_html)
    log.info(f"Parsed prices: {prices}")

    steak_price = prices["steak"]
    kabob_price = prices["kabob"]

    if steak_price is None or kabob_price is None:
        raise RuntimeError(f"Failed to locate steak/kabob price in HTML: {prices}")


if __name__ == "__main__":
    setup.setup_logging(level=config.LOGGING_SETTINGS.get("LEVEL", "INFO"))
    main()
