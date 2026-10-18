"""Transport-free, reviewed calendar-notice claims shared with read-side consumers."""

import re
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from tong_quant.domain.models import require_timezone
from tong_quant.version import SSE_CALENDAR_NOTICE_VERSION


def require_notice_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.sse.com.cn"
        or re.fullmatch(r"/disclosure/announcement/general/c/c_[0-9]{8}_[0-9]+\.shtml", parsed.path)
        is None
        or parsed.query
        or parsed.fragment
        or any(part in {".", ".."} for part in parsed.path.split("/"))
    ):
        raise ValueError("calendar evidence requires an approved official SSE notice URL")


@dataclass(frozen=True, slots=True)
class SSECalendarNoticeProfile:
    source_url: str
    content_sha256: str
    source_publication_date: date
    reviewed_at: datetime
    review_expires_at: datetime
    sessions: tuple[tuple[date, bool], ...]
    profile_sha256: str
    notice_scope: str = "partial_notice"
    calendar_year: int = 2026

    @classmethod
    def load(cls, path: Path) -> "SSECalendarNoticeProfile":
        content = path.read_bytes()
        raw = tomllib.loads(content.decode("utf-8"))
        if raw["profile_version"] != SSE_CALENDAR_NOTICE_VERSION:
            raise ValueError("unsupported calendar notice profile")
        require_notice_url(raw["source_url"])
        digest = raw["content_sha256"]
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("calendar notice requires a lowercase SHA-256 digest")
        reviewed, expires = raw["reviewed_at"], raw["review_expires_at"]
        require_timezone(reviewed, "calendar reviewed_at")
        require_timezone(expires, "calendar review_expires_at")
        if expires <= reviewed or expires - reviewed > timedelta(days=31):
            raise ValueError("calendar source review requires a bounded validity window")
        year = raw["year"]
        scope = raw.get("notice_scope", "partial_notice")
        if scope not in {"partial_notice", "annual_holidays"}:
            raise ValueError("unsupported calendar notice scope")
        if scope == "annual_holidays" and (
            len(raw["closed_intervals"]) != 7 or len(raw["open_dates"]) != 7
        ):
            raise ValueError("annual holidays require the full reviewed holiday mapping")
        publication = raw["source_publication_date"]
        if type(year) is not int or type(publication) is not date:
            raise ValueError("calendar year and publication date must be explicit")
        if publication > reviewed.date():
            raise ValueError("calendar publication cannot follow review")
        sessions: dict[date, bool] = {}

        def add(day: date, is_open: bool) -> None:
            if type(day) is not date or day.year != year or day in sessions:
                raise ValueError("calendar dates must be unique and belong to the reviewed year")
            sessions[day] = is_open

        for start, end in raw["closed_intervals"]:
            if (
                type(start) is not date
                or type(end) is not date
                or not 0 <= (end - start).days <= 31
            ):
                raise ValueError("notice closure interval is invalid or too broad")
            for offset in range((end - start).days + 1):
                add(start + timedelta(days=offset), False)
        for day in raw["closed_dates"]:
            add(day, False)
        for day in raw["open_dates"]:
            add(day, True)
        if not sessions:
            raise ValueError("calendar notice must contain explicit assertions")
        return cls(
            raw["source_url"],
            digest,
            publication,
            reviewed,
            expires,
            tuple(sorted(sessions.items())),
            sha256(content).hexdigest(),
            scope,
            year,
        )
