from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def today():
    return datetime.now(BUSINESS_TIMEZONE).date()


def business_date(value: str):
    if "T" in value:
        return datetime.fromisoformat(value).astimezone(BUSINESS_TIMEZONE).date().isoformat()
    return value[:10]
