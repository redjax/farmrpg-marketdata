import logging
import httpx
import hishel
import hishel.httpx

log = logging.getLogger(__name__)


__all__ = ["get_cache_transport", "get_client", "send_request"]


def send_request(
    req: httpx.Request,
    client: httpx.Client | None = None,
    use_cache: bool = True,
    cache_db_file: str = "http_cache.db",
    cache_ttl: int = 3600,
) -> httpx.Response:
    if not req:
        raise ValueError("Missing httpx.Request object")

    if not client:
        client: httpx.Client = get_client(
            use_cache=use_cache, cache_db_file=cache_db_file, cache_ttl=cache_ttl
        )

    log.debug(f"Sending request to: {req.url}")
    try:
        with client as http:
            res: httpx.Response = http.send(req)
            res.raise_for_status()
    except Exception as exc:
        log.error(f"Failed sending request to '{req.url}': {exc}")
        raise

    return res


def get_cache_transport(
    cache_file: str = "http_cache.db", cache_ttl: int = 3600
) -> httpx.HTTPTransport:
    """Returns an httpx-compatible transport with Hishel caching."""
    storage: hishel.SyncSqliteStorage = hishel.SyncSqliteStorage(
        database_path=cache_file,
        default_ttl=cache_ttl,
    )

    transport: hishel.httpx.SyncCacheTransport = hishel.httpx.SyncCacheTransport(
        next_transport=httpx.HTTPTransport(), storage=storage
    )

    return transport


def get_client(
    use_cache: bool = False,
    cache_transport: hishel.httpx.SyncCacheTransport = None,
    cache_db_file: str = "http_cache.db",
    cache_ttl: int = 3600,
):
    if use_cache and not cache_transport:
        log.debug(
            "use_cache is True, but no cache_transport provided. Initializing a cache transport"
        )
        cache_transport = get_cache_transport(
            cache_file=cache_db_file, cache_ttl=cache_ttl
        )

        client: httpx.Client = httpx.Client(transport=cache_transport)
    else:
        client: httpx.Client = httpx.Client()

    return client
