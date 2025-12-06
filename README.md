# FarmRPG Market Scrapers

Scrape market prices from the FarmRPG [steak market](https://farmrpg.com/steakhistory.php) and [kebab market](https://farmrpg.com/steakhistoryk.php).

## Setup

### Run on Host

- Copy [`settings.toml`](settings.toml) to `settings.local.toml`
  - Edit to your liking
- Run `uv sync --all-extras`
- Run `uv build`
- Run `uv pip install -e .`
- Run [one of the entrypoint scripts](./scripts/market/)
  - i.e. to start a scheduled run, use `uv run scripts/market/scheduled_scrape.py`

## Run in Docker

- `cd` into [`containers/scraper`](./containers/scraper/)
- Copy the [example `.env` file](./containers/scraper/.env.example) to `.env` and edit to your liking
  - If you want to mount logs or the database on your host (instead of in the volumes defined in [the `compose.yml` file](./containers/scraper/compose.yml)), edit the following env vars:
    - `LOGS_DIR=/absolute/path/on/host/to/logs/`
    - `DB_DIR=/absolute/path/on/host/to/db/`
    - Where you see `/absolute/path/on/host`, use a full/absolute path to a directory, starting with `/`.
    - Relative paths, i.e. `../container_data/logs`, do not work.
- Run `docker compose build`
- Run `docker compose up -d --force-recreate`
- To check the app's logs, use `docker compose logs -f scraper`
