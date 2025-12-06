import datetime as dt

__all__ = ["get_ts"]


def get_ts(fmt: str = "datetime", custom: str | None = None, utc: bool = False):
    """Get the current timestamp in various formats.

    Params:
        fmt (str): Type/format of timestamp.
            - "datetime" (default) -> returns datetime.datetime object
            - "iso" -> returns ISO 8601 string
            - "str" -> returns formatted string using `custom` format
            - "epoch" -> returns UNIX timestamp as float
            - "date" -> returns date as yyyy-mm-dd string
            - "time" -> returns time as HH:MM:SS string
            - "file" -> returns time as YYYYmmdd_HHMMSS
        custom (str | None): If fmt="str", use this strftime format string
        utc (bool): If True, return UTC timestamp instead of local

    Returns:
        Timestamp in requested format/type
    """
    now = dt.datetime.now(tz=dt.timezone.utc) if utc else dt.datetime.now()

    match fmt:
        case "datetime":
            return now
        case "iso":
            return now.isoformat()
        case "str":
            if not custom:
                raise ValueError("`custom` format must be provided when fmt='str'")

            return now.strftime(custom)
        case "epoch":
            return now.timestamp()
        case "date":
            return now.strftime("%Y-%m-%d")
        case "time":
            return now.strftime("%H:%M:%S")
        case "file":
            return now.strftime("%Y%m%d_%H%M%S")
        case _:
            raise ValueError(f"Unknown fmt '{fmt}'")
