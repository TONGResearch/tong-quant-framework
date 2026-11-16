"""Conservative Yahoo symbol routing, not exchange or issuer qualification."""

import re

from tong_quant.domain.enums import Market

TIMEZONES = {Market.US: "America/New_York", Market.HONG_KONG: "Asia/Hong_Kong",
             Market.MALAYSIA: "Asia/Kuala_Lumpur"}


def validate_yahoo_equity_subject(market: Market, subject: str) -> None:
    patterns = {Market.US: r"[A-Z][A-Z0-9.-]{0,19}",
                Market.HONG_KONG: r"[0-9]{4,5}\.HK",
                Market.MALAYSIA: r"[A-Z0-9][A-Z0-9-]{0,15}\.KL"}
    if (market not in patterns
            or re.fullmatch(patterns[market], subject, flags=re.ASCII) is None):
        raise ValueError("unsupported global equity snapshot identity")
    if market is Market.US and subject.endswith((".HK", ".KL", ".SS", ".SZ")):
        raise ValueError("foreign suffix in US snapshot request")
