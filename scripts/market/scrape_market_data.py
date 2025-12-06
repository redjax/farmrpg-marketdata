import sys
from marketdata import main
import marketdata.shared as shared

if __name__ == "__main__":
    print(shared.MarketPricesRaw)
    try:
        main(save_prices=True, log_level="DEBUG", enable_file_logging=True)
    except Exception as exc:
        print(f"[ERROR] ({type(exc)}) Failed to scrape current market prices")
        sys.exit(1)
