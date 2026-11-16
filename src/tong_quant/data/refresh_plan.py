"""Offline explicit-scope planning; never collect, schedule or admit research inputs."""

import json
import re
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_fundamentals import (
    DATASET as FUNDAMENTALS,
)
from tong_quant.data.providers.yahoo_fundamentals import validate_fundamental_request
from tong_quant.data.providers.yahoo_identity import TIMEZONES
from tong_quant.data.providers.yahoo_snapshot import DATASET as PRICES
from tong_quant.data.providers.yahoo_snapshot import validate_snapshot_request
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    AKSHARE_DAILY_FETCH_VERSION,
    AKSHARE_MARKET_NORMALIZATION_VERSION,
    AKSHARE_SYMBOL_ROUTING_VERSION,
    DATA_REFRESH_PLAN_VERSION,
    DATABASE_SCHEMA_VERSION,
    FRAMEWORK_VERSION,
    GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION,
    GLOBAL_PRICE_SNAPSHOT_VERSION,
)

MAX_CONFIG_BYTES = 128 * 1024
MAX_SCOPES = 128
_FIELDS = {"provider", "dataset", "market", "subject", "currency", "exchange",
           "timezone", "start_date", "end_date"}
_TIMEZONES = {**TIMEZONES, Market.CHINA_A: "Asia/Shanghai"}


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: object) -> str:
    return sha256(_json(value).encode()).hexdigest()


def _label(value: object, pattern: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value, flags=re.ASCII):
        raise ValueError("invalid refresh scope label")
    return value


@dataclass(frozen=True, slots=True)
class RefreshScope:
    provider: str
    dataset: str
    market: Market
    subject: str
    currency: str
    exchange: str
    timezone: str
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        reject_sensitive_structure(asdict(self))
        _label(self.provider, r"[a-z][a-z0-9_]{0,63}")
        _label(self.dataset, r"[a-z][a-z0-9_]{0,63}")
        _label(self.subject, r"[A-Za-z0-9][A-Za-z0-9.-]{0,63}")
        _label(self.currency, r"[A-Z]{3}")
        _label(self.exchange, r"[A-Z0-9]{2,12}")
        if not isinstance(self.market, Market) or self.timezone != _TIMEZONES[self.market]:
            raise ValueError("explicit market timezone is required")
        for value in (self.start_date, self.end_date):
            _label(value, r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
        start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        if start > end or (end - start).days > 15000:
            raise ValueError("refresh window is reversed or exceeds bound")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return self.provider, self.dataset, self.market.value, self.subject


@dataclass(frozen=True, slots=True)
class RefreshWatchlist:
    version: str
    scopes: tuple[RefreshScope, ...]

    def __post_init__(self) -> None:
        _label(self.version, r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
        if not isinstance(self.scopes, tuple) or not 1 <= len(self.scopes) <= MAX_SCOPES:
            raise ValueError("refresh scope count exceeds bounds")
        for scope in self.scopes:
            if not isinstance(scope, RefreshScope):
                raise ValueError("invalid refresh scope")
            scope.__post_init__()
        if len({scope.identity for scope in self.scopes}) != len(self.scopes):
            raise ValueError("duplicate provider/dataset/market/subject scope")


def parse_refresh_watchlist(content: str) -> RefreshWatchlist:
    """Strict, bounded TOML with no URLs, credentials or implicit source selection."""
    if len(content.encode()) > MAX_CONFIG_BYTES:
        raise ValueError("refresh configuration exceeds byte bound")
    config = tomllib.loads(content)
    reject_sensitive_structure(config)
    if set(config) != {"version", "scopes"}:
        raise ValueError("unexpected refresh configuration fields")
    rows = config["scopes"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_SCOPES:
        raise ValueError("refresh scope count exceeds bounds")
    scopes = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != _FIELDS
                or not all(isinstance(value, str) for value in row.values())):
            raise ValueError("unexpected refresh scope fields or types")
        scopes.append(RefreshScope(**{**row, "market": Market(row["market"])}))
    return RefreshWatchlist(config["version"], tuple(scopes))


def _akshare_declared_equity_exchange(symbol: str) -> str | None:
    if not re.fullmatch(r"[0-9]{6}", symbol, flags=re.ASCII):
        return None
    if symbol.startswith(("000", "001", "002", "003", "300", "301")):
        return "SZSE"
    if symbol.startswith(("600", "601", "603", "605", "688", "689")):
        return "SSE"
    if symbol.startswith(("920", "4", "8")):
        return "BSE"
    return None


def akshare_daily_refresh_request(scope: RefreshScope) -> DailyBarRequest:
    """Convert a declared equity scope only; not listing, source or session approval."""
    scope.__post_init__()
    if (scope.provider, scope.dataset, scope.market) != (
        "akshare", "a_share_daily", Market.CHINA_A,
    ):
        raise ValueError("unsupported AKShare refresh scope")
    exchange = _akshare_declared_equity_exchange(scope.subject)
    if exchange is None or (scope.currency, scope.exchange) != ("CNY", exchange):
        raise ValueError("unsupported or mismatched AKShare equity routing declaration")
    return DailyBarRequest(
        symbol=scope.subject,
        start_date=scope.start_date.replace("-", ""),
        end_date=scope.end_date.replace("-", ""),
        asset_type=AssetType.EQUITY, market=Market.CHINA_A, adjustment=Adjustment.NONE,
    )


def _entry(scope: RefreshScope, as_of: datetime) -> dict[str, object]:
    if date.fromisoformat(scope.end_date) > as_of.astimezone(ZoneInfo(scope.timezone)).date():
        raise ValueError("refresh window extends beyond the planning instant's local date")
    params: dict[str, object] = {"start_date": scope.start_date, "end_date": scope.end_date}
    status = "UNSUPPORTED"
    reason = "no_offline_refresh_bridge"
    provider_version = None
    request_contract = None
    contract_versions: dict[str, str] = {}
    limitations = [
        "No fetch, database inspection, freshness/due calculation or calendar admission",
        "Declared routing/currency/exchange is not independently verified identity",
        "No publication/revision/continuity/adjustment or latest-filing qualification",
        "Planned time is not actual capture time or historical data availability",
    ]
    if (scope.provider == "yahoo_finance" and scope.market in TIMEZONES
            and scope.dataset in {PRICES, FUNDAMENTALS}):
        if scope.dataset == PRICES:
            params.update(currency=scope.currency, exchange=scope.exchange, timezone=scope.timezone)
            validator = validate_snapshot_request
            provider_version = GLOBAL_PRICE_SNAPSHOT_VERSION
        else:
            validator = validate_fundamental_request
            provider_version = GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION
        validator(ProviderDatasetRequest(scope.dataset, scope.market, scope.subject, as_of,
                                         {key: str(value) for key, value in params.items()}))
        status, reason = "REQUEST_SCOPE_VALIDATED", "static_contract_only"
        request_contract = "ProviderDatasetRequest"
    elif (scope.provider, scope.dataset, scope.market) == (
        "akshare", "a_share_daily", Market.CHINA_A,
    ):
        if _akshare_declared_equity_exchange(scope.subject) is None:
            reason = "akshare_equity_route_unrecognized"
        else:
            params = asdict(akshare_daily_refresh_request(scope))
            provider_version = AKSHARE_DAILY_FETCH_VERSION
            contract_versions = {"fetch": AKSHARE_DAILY_FETCH_VERSION,
                "routing": AKSHARE_SYMBOL_ROUTING_VERSION,
                "normalization": AKSHARE_MARKET_NORMALIZATION_VERSION}
            request_contract = "DailyBarRequest"
            status, reason = "REQUEST_SCOPE_VALIDATED", "static_legacy_contract_only"
            limitations.extend([
                "NONE requests no adjustment; delivered price basis still needs independent review",
                "Legacy downloader may fall back within AKShare; retain actual endpoint provenance",
                "BSE route does not prove upstream payload availability or provider coverage",
                "DailyBarRequest is not the captured-evidence adapter's ProviderDatasetRequest",
            ])
    return {
        "scope": asdict(scope), "scope_hash": _hash(asdict(scope)),
        "request_contract_status": status, "reason_code": reason,
        "request_parameters": params if status == "REQUEST_SCOPE_VALIDATED" else None,
        "request_contract": request_contract, "provider_contract_versions": contract_versions,
        "provider_model_version": provider_version,
        "provider_permission": "NOT_TESTED", "data_availability": "UNKNOWN",
        "data_trust_level": "UNKNOWN", "availability_precision": "UNKNOWN",
        "calendar_status": "UNKNOWN", "closed_bar_qualified": False,
        "limitations": limitations,
    }


def build_refresh_plan(watchlist: RefreshWatchlist, *, planned_as_of: datetime,
                       git_commit: str, git_dirty: bool) -> dict[str, object]:
    """Return JSON-safe diagnostics, not runnable jobs or a deployment approval."""
    watchlist.__post_init__()
    require_timezone(planned_as_of, "refresh plan")
    _label(git_commit, r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
    if type(git_dirty) is not bool:
        raise ValueError("Git dirty status must be explicit")
    cutoff = planned_as_of.astimezone(UTC)
    scopes = sorted(watchlist.scopes, key=lambda scope: scope.identity)
    config = {"version": watchlist.version, "scopes": [asdict(scope) for scope in scopes]}
    payload: dict[str, object] = {
        "model_version": DATA_REFRESH_PLAN_VERSION, "framework_version": FRAMEWORK_VERSION,
        "schema_version": DATABASE_SCHEMA_VERSION, "watchlist_version": watchlist.version,
        "config_hash": _hash(config), "watchlist_hash": _hash(config["scopes"]),
        "planned_as_of": cutoff.isoformat(), "git_commit": git_commit, "git_dirty": git_dirty,
        "collection_authorized": False, "schedule_enabled": False,
        "research_refresh_authorized": False,
        "entries": [_entry(scope, cutoff) for scope in scopes],
        "warnings": [
            "Offline request plan only; no provider availability or research-readiness conclusion",
            "Git revision/dirty flag is not a working-tree content hash or reviewed deployment",
            "Actual capture must use actual post-download time; never backdate to planned_as_of",
            "Static request bridges do not implement capture, raw evidence retention or a worker",
            "No durable attempts, leases, checkpoints, automatic updates or installed scheduler",
        ],
    }
    return {**payload, "plan_hash": _hash(payload)}
