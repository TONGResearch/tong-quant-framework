import json
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
from time import monotonic, sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

import certifi

from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.calibration.models import (
    CalibrationRecord,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.providers.cninfo import CNINFO_DISCLOSURES_DATASET
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderArtifact,
    ProviderArtifactObservation,
    ProviderArtifactStatus,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_artifact_observation_id,
    provider_evidence_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

CNINFO_DIRECT_PROVIDER_ID = "cninfo_direct"
CNINFO_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STOCK_DIRECTORY_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_STATIC_ROOT = "https://static.cninfo.com.cn/"
_ALLOWED_ARTIFACT_HOSTS = {"static.cninfo.com.cn"}


@dataclass(frozen=True, slots=True)
class CnInfoQueryResult:
    announcements: tuple[dict[str, object], ...]
    raw_data_hash: str
    total_announcements: int
    total_pages: int
    pages_fetched: int
    truncated: bool

    def __post_init__(self) -> None:
        if len(self.raw_data_hash) != 64:
            raise ValueError("CNInfo query hash must be a SHA-256 digest")
        if min(self.total_announcements, self.total_pages, self.pages_fetched) < 0:
            raise ValueError("CNInfo query counts cannot be negative")


@dataclass(frozen=True, slots=True)
class CnInfoArtifactDownload:
    status: ProviderArtifactStatus
    requested_url: str
    resolved_url: str
    media_type: str
    content: bytes
    error_code: str

    def __post_init__(self) -> None:
        if self.status is ProviderArtifactStatus.CAPTURED:
            if not self.content or self.error_code:
                raise ValueError("captured CNInfo documents require bytes and no error")
        elif self.content or not self.error_code:
            raise ValueError("uncaptured CNInfo documents require an error and no bytes")


class CnInfoDirectClient(Protocol):
    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category_code: str = "",
    ) -> CnInfoQueryResult: ...

    def download_artifact(self, url: str) -> CnInfoArtifactDownload: ...


class _CnInfoRequestError(RuntimeError):
    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


@dataclass(slots=True)
class CnInfoHttpClient:
    timeout_seconds: float = 20
    max_attempts: int = 3
    min_interval_seconds: float = 0.5
    page_size: int = 30
    max_pages: int = 10
    max_artifact_bytes: int = 50 * 1024 * 1024
    sleeper: Callable[[float], None] = sleep
    timer: Callable[[], float] = monotonic
    _last_request_at: float | None = None
    _directory_cache: dict[str, str] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.max_attempts < 1:
            raise ValueError("CNInfo timeout and attempts must be positive")
        if self.min_interval_seconds < 0.2:
            raise ValueError("CNInfo request interval must be at least 0.2 seconds")
        if not 1 <= self.page_size <= 30 or not 1 <= self.max_pages <= 100:
            raise ValueError("CNInfo page size/max pages exceed conservative bounds")
        if self.max_artifact_bytes < 1024:
            raise ValueError("CNInfo artifact limit must be at least 1 KiB")

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category_code: str = "",
    ) -> CnInfoQueryResult:
        _date_range(start_date, end_date)
        org_id = self._stock_directory().get(symbol)
        if org_id is None:
            raise DataProviderError("CNInfo stock directory does not contain the subject")
        pages: list[dict[str, object]] = []
        announcements: list[dict[str, object]] = []
        first = self._query_page(
            page_number=1,
            symbol=symbol,
            org_id=org_id,
            start_date=start_date,
            end_date=end_date,
            category_code=category_code,
        )
        pages.append(first)
        announcements.extend(_announcement_rows(first))
        total_pages = _integer(first.get("totalpages"), "totalpages")
        total_announcements = _integer(
            first.get("totalAnnouncement"),
            "totalAnnouncement",
        )
        pages_to_fetch = min(total_pages, self.max_pages)
        for page_number in range(2, pages_to_fetch + 1):
            page = self._query_page(
                page_number=page_number,
                symbol=symbol,
                org_id=org_id,
                start_date=start_date,
                end_date=end_date,
                category_code=category_code,
            )
            pages.append(page)
            announcements.extend(_announcement_rows(page))
        raw_data_hash = sha256(
            json.dumps(pages, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return CnInfoQueryResult(
            announcements=tuple(announcements),
            raw_data_hash=raw_data_hash,
            total_announcements=total_announcements,
            total_pages=total_pages,
            pages_fetched=len(pages),
            truncated=total_pages > self.max_pages,
        )

    def download_artifact(self, url: str) -> CnInfoArtifactDownload:
        _validate_artifact_url(url)
        request = Request(url, headers=_headers(accept="application/pdf,*/*"))
        try:
            content, media_type, resolved_url = self._request_bytes(
                request,
                max_bytes=self.max_artifact_bytes,
                final_url_validator=_validate_artifact_url,
            )
            is_pdf = (
                media_type.split(";", 1)[0].lower() == "application/pdf"
                or urlparse(resolved_url).path.lower().endswith(".pdf")
            )
            if is_pdf and not content.startswith(b"%PDF"):
                raise _CnInfoRequestError("invalid_pdf_payload")
            return CnInfoArtifactDownload(
                status=ProviderArtifactStatus.CAPTURED,
                requested_url=url,
                resolved_url=resolved_url,
                media_type=media_type or "application/octet-stream",
                content=content,
                error_code="",
            )
        except _CnInfoRequestError as error:
            status = (
                ProviderArtifactStatus.MISSING
                if error.error_code in {"http_404", "http_410"}
                else ProviderArtifactStatus.UNAVAILABLE
            )
            return CnInfoArtifactDownload(
                status=status,
                requested_url=url,
                resolved_url=url,
                media_type="application/octet-stream",
                content=b"",
                error_code=error.error_code,
            )

    def _stock_directory(self) -> dict[str, str]:
        if self._directory_cache is not None:
            return self._directory_cache
        request = Request(
            CNINFO_STOCK_DIRECTORY_URL,
            headers=_headers(accept="application/json"),
        )
        payload = self._request_json(request)
        stock_list = payload.get("stockList")
        if not isinstance(stock_list, list):
            raise DataProviderError("CNInfo stock directory is malformed")
        directory: dict[str, str] = {}
        for item in stock_list:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            org_id = str(item.get("orgId", "")).strip()
            if code and org_id:
                directory[code] = org_id
        self._directory_cache = directory
        return directory

    def _query_page(
        self,
        *,
        page_number: int,
        symbol: str,
        org_id: str,
        start_date: str,
        end_date: str,
        category_code: str,
    ) -> dict[str, object]:
        form = {
            "pageNum": str(page_number),
            "pageSize": str(self.page_size),
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{symbol},{org_id}",
            "searchkey": "",
            "secid": "",
            "category": category_code,
            "trade": "",
            "seDate": f"{start_date}~{end_date}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        request = Request(
            CNINFO_QUERY_URL,
            data=urlencode(form).encode("utf-8"),
            headers={
                **_headers(accept="application/json"),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return self._request_json(request)

    def _request_json(self, request: Request) -> dict[str, object]:
        try:
            content, _media_type, _resolved_url = self._request_bytes(
                request,
                max_bytes=20 * 1024 * 1024,
                final_url_validator=None,
            )
            payload = json.loads(content.decode("utf-8"))
        except (_CnInfoRequestError, UnicodeDecodeError, json.JSONDecodeError) as error:
            code = (
                error.error_code
                if isinstance(error, _CnInfoRequestError)
                else type(error).__name__
            )
            raise DataProviderError(f"CNInfo request failed ({code})") from error
        if not isinstance(payload, dict):
            raise DataProviderError("CNInfo response is not an object")
        return payload

    def _request_bytes(
        self,
        request: Request,
        *,
        max_bytes: int,
        final_url_validator: Callable[[str], None] | None,
    ) -> tuple[bytes, str, str]:
        context = ssl.create_default_context(cafile=certifi.where())
        last_code = "unknown_error"
        for attempt in range(1, self.max_attempts + 1):
            self._rate_limit()
            try:
                with urlopen(  # noqa: S310
                    request,
                    timeout=self.timeout_seconds,
                    context=context,
                ) as response:
                    resolved_url = response.geturl()
                    if final_url_validator is not None:
                        final_url_validator(resolved_url)
                    declared_length = response.headers.get("Content-Length")
                    if declared_length and int(declared_length) > max_bytes:
                        raise _CnInfoRequestError("artifact_size_limit_exceeded")
                    content = response.read(max_bytes + 1)
                    if len(content) > max_bytes:
                        raise _CnInfoRequestError("artifact_size_limit_exceeded")
                    media_type = response.headers.get("Content-Type", "")
                    return content, media_type, resolved_url
            except HTTPError as error:
                last_code = f"http_{error.code}"
                if error.code in {404, 410}:
                    raise _CnInfoRequestError(last_code) from error
            except (TimeoutError, URLError, OSError) as error:
                last_code = type(error).__name__
            except _CnInfoRequestError:
                raise
            if attempt < self.max_attempts:
                self.sleeper(float(attempt))
        raise _CnInfoRequestError(last_code)

    def _rate_limit(self) -> None:
        now = self.timer()
        if self._last_request_at is not None:
            remaining = self.min_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self.sleeper(remaining)
                now = self.timer()
        self._last_request_at = now


@dataclass(slots=True)
class CnInfoDirectEvidenceAdapter:
    client: CnInfoDirectClient
    clock: Callable[[], datetime]
    provider_id: str = field(init=False, default=CNINFO_DIRECT_PROVIDER_ID)

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset=CNINFO_DISCLOSURES_DATASET,
                markets=(Market.CHINA_A,),
                status=ProviderCapabilityStatus.DEGRADED,
                trust_level=DataTrustLevel.MEDIUM,
                availability_precision=AvailabilityPrecision.EXACT,
                historical_continuity=False,
                required_parameters=("start_date", "end_date", "capture_artifacts"),
                limitations=_direct_limitations(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != CNINFO_DISCLOSURES_DATASET:
            raise ValueError("direct CNInfo adapter only supports disclosure evidence")
        if request.market is not Market.CHINA_A:
            raise ValueError("direct CNInfo evidence is China A specific")
        start_date, end_date = _date_range(
            request.parameters["start_date"],
            request.parameters["end_date"],
        )
        capture_artifacts = _boolean(request.parameters["capture_artifacts"])
        max_artifacts = _bounded_integer(
            request.parameters.get("max_artifacts", "30"),
            name="max_artifacts",
            minimum=0,
            maximum=100,
        )
        query = self.client.search(
            request.subject,
            start_date=start_date,
            end_date=end_date,
            category_code=request.parameters.get("category_code", ""),
        )
        prepared: list[_PreparedAnnouncement] = []
        limitations = list(_direct_limitations())
        malformed = 0
        future = 0
        artifact_limit_reached = 0
        captured_attempts = 0
        for row in query.announcements:
            announcement = _prepare_announcement(row, fallback_subject=request.subject)
            if announcement is None:
                malformed += 1
                continue
            if announcement.published_at > request.as_of:
                future += 1
                continue
            download: CnInfoArtifactDownload | None = None
            if capture_artifacts:
                if captured_attempts < max_artifacts and announcement.artifact_url:
                    download = self.client.download_artifact(announcement.artifact_url)
                    captured_attempts += 1
                elif not announcement.artifact_url:
                    download = CnInfoArtifactDownload(
                        status=ProviderArtifactStatus.MISSING,
                        requested_url=announcement.detail_url,
                        resolved_url=announcement.detail_url,
                        media_type="application/octet-stream",
                        content=b"",
                        error_code="missing_artifact_url",
                    )
                else:
                    artifact_limit_reached += 1
                    download = CnInfoArtifactDownload(
                        status=ProviderArtifactStatus.UNAVAILABLE,
                        requested_url=announcement.artifact_url,
                        resolved_url=announcement.artifact_url,
                        media_type="application/octet-stream",
                        content=b"",
                        error_code="artifact_limit_reached",
                    )
            prepared.append(_PreparedAnnouncement(announcement, download))
        retrieved_at = self.clock()
        records: list[ProviderEvidenceRecord] = []
        artifacts: list[ProviderArtifact] = []
        observations: list[ProviderArtifactObservation] = []
        for item in prepared:
            record, artifact, observation = _build_record(
                item,
                request=request,
                retrieved_at=retrieved_at,
                raw_data_hash=query.raw_data_hash,
            )
            records.append(record)
            if artifact is not None:
                artifacts.append(artifact)
            if observation is not None:
                observations.append(observation)
        limitations.extend(
            _observed_limitations(
                query=query,
                malformed=malformed,
                future=future,
                artifact_limit_reached=artifact_limit_reached,
                observations=tuple(observations),
                capture_artifacts=capture_artifacts,
            )
        )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=retrieved_at,
            source="cninfo_direct:hisAnnouncement+static",
            parameters={"subject": request.subject, **request.parameters},
            raw_data_hash=query.raw_data_hash,
            raw_record_count=len(query.announcements),
            records=tuple(records),
            limitations=tuple(limitations),
            artifacts=tuple(artifacts),
            artifact_observations=tuple(observations),
        )


@dataclass(frozen=True, slots=True)
class _Announcement:
    announcement_id: str
    subject: str
    name: str
    title: str
    org_id: str
    published_at: datetime
    detail_url: str
    artifact_url: str
    related_source_identities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PreparedAnnouncement:
    announcement: _Announcement
    download: CnInfoArtifactDownload | None


def _build_record(
    prepared: _PreparedAnnouncement,
    *,
    request: ProviderDatasetRequest,
    retrieved_at: datetime,
    raw_data_hash: str,
) -> tuple[
    ProviderEvidenceRecord,
    ProviderArtifact | None,
    ProviderArtifactObservation | None,
]:
    announcement = prepared.announcement
    download = prepared.download
    artifact: ProviderArtifact | None = None
    observation: ProviderArtifactObservation | None = None
    artifact_status = "not_requested"
    artifact_hash = ""
    resolved_url = ""
    error_code = ""
    if download is not None:
        artifact_status = download.status.value
        resolved_url = download.resolved_url
        error_code = download.error_code
        artifact_identifier: str | None = None
        if download.status is ProviderArtifactStatus.CAPTURED:
            artifact_hash = sha256(download.content).hexdigest()
            artifact_identifier = provider_artifact_id(
                provider=CNINFO_DIRECT_PROVIDER_ID,
                dataset=request.dataset,
                market=request.market,
                subject=announcement.subject,
                source_identity=announcement.announcement_id,
                source_reference=download.requested_url,
                content_hash=artifact_hash,
            )
            artifact = ProviderArtifact(
                artifact_id=artifact_identifier,
                provider=CNINFO_DIRECT_PROVIDER_ID,
                dataset=request.dataset,
                market=request.market,
                subject=announcement.subject,
                source_identity=announcement.announcement_id,
                source_reference=download.requested_url,
                published_at=announcement.published_at,
                retrieved_at=retrieved_at,
                content_hash=artifact_hash,
                media_type=download.media_type,
                availability_precision=AvailabilityPrecision.EXACT,
                trust_level=DataTrustLevel.MEDIUM,
                content=download.content,
            )
        observation = ProviderArtifactObservation(
            observation_id=provider_artifact_observation_id(
                provider=CNINFO_DIRECT_PROVIDER_ID,
                dataset=request.dataset,
                market=request.market,
                subject=announcement.subject,
                source_identity=announcement.announcement_id,
                source_reference=download.requested_url,
                published_at=announcement.published_at,
                retrieved_at=retrieved_at,
                status=download.status,
                artifact_id=artifact_identifier,
                error_code=error_code,
                related_source_identities=announcement.related_source_identities,
            ),
            provider=CNINFO_DIRECT_PROVIDER_ID,
            dataset=request.dataset,
            market=request.market,
            subject=announcement.subject,
            source_identity=announcement.announcement_id,
            source_reference=download.requested_url,
            published_at=announcement.published_at,
            retrieved_at=retrieved_at,
            status=download.status,
            artifact_id=artifact_identifier,
            error_code=error_code,
            related_source_identities=announcement.related_source_identities,
        )
    payload: dict[str, object] = {
        "symbol": announcement.subject,
        "name": announcement.name,
        "title": announcement.title,
        "announcement_id": announcement.announcement_id,
        "org_id": announcement.org_id,
        "announcement_time": announcement.published_at.isoformat(),
        "detail_url": announcement.detail_url,
        "artifact_url": announcement.artifact_url,
        "resolved_artifact_url": resolved_url,
        "artifact_status": artifact_status,
        "artifact_content_hash": artifact_hash,
        "artifact_error_code": error_code,
        "related_announcement_ids": list(announcement.related_source_identities),
    }
    limitations = tuple(item.description for item in _direct_limitations())
    return (
        ProviderEvidenceRecord(
            evidence_id=provider_evidence_id(
                provider=CNINFO_DIRECT_PROVIDER_ID,
                dataset=request.dataset,
                market=request.market,
                subject=announcement.subject,
                available_at=announcement.published_at,
                source_reference=announcement.detail_url,
                payload=payload,
            ),
            provider=CNINFO_DIRECT_PROVIDER_ID,
            dataset=request.dataset,
            market=request.market,
            subject=announcement.subject,
            observed_at=announcement.published_at,
            published_at=announcement.published_at,
            available_at=announcement.published_at,
            retrieved_at=retrieved_at,
            source_reference=announcement.detail_url,
            payload=payload,
            raw_data_hash=raw_data_hash,
            availability_precision=AvailabilityPrecision.EXACT,
            trust_level=DataTrustLevel.MEDIUM,
            limitations=limitations,
        ),
        artifact,
        observation,
    )


def cninfo_calibration_snapshot(
    batch: ProviderEvidenceBatch,
    *,
    as_of: datetime,
) -> ProviderCalibrationSnapshot:
    if batch.dataset != CNINFO_DISCLOSURES_DATASET:
        raise ValueError("CNInfo calibration requires disclosure evidence")
    records: list[CalibrationRecord] = []
    future_records = 0
    for evidence in batch.records:
        if evidence.available_at > as_of:
            future_records += 1
            continue
        announcement_id = str(evidence.payload.get("announcement_id", "")).strip()
        if not announcement_id:
            continue
        records.append(
            CalibrationRecord(
                key=announcement_id,
                fields={
                    "symbol": evidence.subject,
                    "title": str(evidence.payload.get("title", "")),
                    "published_at": (
                        None
                        if evidence.published_at is None
                        else evidence.published_at.astimezone(UTC).isoformat()
                    ),
                },
            )
        )
    limitations = tuple(item.description for item in batch.limitations)
    if future_records:
        limitations = (
            *limitations,
            f"{future_records} disclosure records after calibration as_of were excluded",
        )
    return ProviderCalibrationSnapshot(
        provider=batch.provider,
        dataset=batch.dataset,
        as_of=as_of,
        records=tuple(sorted(records, key=lambda item: item.key)),
        limitations=limitations,
    )


def _prepare_announcement(
    row: dict[str, object],
    *,
    fallback_subject: str,
) -> _Announcement | None:
    announcement_id = str(row.get("announcementId", "")).strip()
    org_id = str(row.get("orgId", "")).strip()
    title = str(row.get("announcementTitle", "")).strip()
    published_at = _published_at(row.get("announcementTime"))
    if not announcement_id or not org_id or not title or published_at is None:
        return None
    subject = str(row.get("secCode", "")).strip() or fallback_subject
    name = str(row.get("secName", "")).strip()
    detail_url = "https://www.cninfo.com.cn/new/disclosure/detail?" + urlencode(
        {
            "stockCode": subject,
            "announcementId": announcement_id,
            "orgId": org_id,
            "announcementTime": published_at.isoformat(),
        }
    )
    adjunct = str(row.get("adjunctUrl", "")).strip()
    artifact_url = urljoin(CNINFO_STATIC_ROOT, adjunct) if adjunct else ""
    return _Announcement(
        announcement_id=announcement_id,
        subject=subject,
        name=name,
        title=title,
        org_id=org_id,
        published_at=published_at,
        detail_url=detail_url,
        artifact_url=artifact_url,
        related_source_identities=_related_ids(row.get("associateAnnouncement")),
    )


def _related_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return ()
    found: set[str] = set()

    def collect(item: object) -> None:
        if isinstance(item, dict):
            announcement_id = str(item.get("announcementId", "")).strip()
            if announcement_id:
                found.add(announcement_id)
            for nested in item.values():
                collect(nested)
        elif isinstance(item, list):
            for nested in item:
                collect(nested)

    collect(value)
    return tuple(sorted(found))


def _observed_limitations(
    *,
    query: CnInfoQueryResult,
    malformed: int,
    future: int,
    artifact_limit_reached: int,
    observations: tuple[ProviderArtifactObservation, ...],
    capture_artifacts: bool,
) -> tuple[EvidenceLimitation, ...]:
    limitations: list[EvidenceLimitation] = []
    values = (
        (
            query.truncated,
            "cninfo_direct_pagination_truncated",
            f"Only {query.pages_fetched} of {query.total_pages} CNInfo pages were fetched",
            DataTrustLevel.LOW,
        ),
        (
            not query.truncated
            and len(query.announcements) != query.total_announcements,
            "cninfo_direct_response_count_mismatch",
            (
                f"CNInfo declared {query.total_announcements} announcements but "
                f"returned {len(query.announcements)}"
            ),
            DataTrustLevel.LOW,
        ),
        (
            bool(malformed),
            "cninfo_direct_malformed_rows",
            f"{malformed} CNInfo rows lacked required identity or publication fields",
            DataTrustLevel.LOW,
        ),
        (
            bool(future),
            "cninfo_direct_future_rows_rejected",
            f"{future} CNInfo rows followed the request as_of and were rejected",
            DataTrustLevel.UNKNOWN,
        ),
        (
            bool(artifact_limit_reached),
            "cninfo_direct_artifact_limit_reached",
            f"{artifact_limit_reached} artifacts exceeded the per-request capture limit",
            DataTrustLevel.LOW,
        ),
        (
            not capture_artifacts,
            "cninfo_direct_metadata_only",
            "Artifact download was not requested; only direct CNInfo metadata was captured",
            DataTrustLevel.MEDIUM,
        ),
    )
    for include, code, description, trust in values:
        if include:
            limitations.append(EvidenceLimitation(code, description, trust))
    failed = sum(
        observation.status is not ProviderArtifactStatus.CAPTURED
        for observation in observations
    )
    if failed:
        limitations.append(
            EvidenceLimitation(
                "cninfo_direct_artifact_capture_incomplete",
                f"{failed} requested CNInfo artifacts were not captured",
                DataTrustLevel.LOW,
            )
        )
    return tuple(limitations)


def _direct_limitations() -> tuple[EvidenceLimitation, ...]:
    return (
        EvidenceLimitation(
            code="cninfo_direct_public_web_contract",
            description=(
                "CNInfo direct access uses a public website contract that may change; "
                "rate limits and bounded pagination are enforced"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        ),
        EvidenceLimitation(
            code="cninfo_direct_continuity_unverified",
            description=(
                "Direct capture does not prove complete historical disclosure or "
                "correction continuity"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        ),
    )


def _headers(*, accept: str) -> dict[str, str]:
    return {
        "Accept": accept,
        "Referer": "https://www.cninfo.com.cn/",
        "User-Agent": "TongQuant/0.8 research-data",
    }


def _validate_artifact_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _ALLOWED_ARTIFACT_HOSTS
        or not parsed.path.startswith("/finalpage/")
    ):
        raise ValueError("CNInfo artifact URL is outside the approved official scope")


def _announcement_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = payload.get("announcements")
    if rows is None:
        return []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise DataProviderError("CNInfo announcements payload is malformed")
    return rows


def _integer(value: object, field: str) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as error:
        raise DataProviderError(f"CNInfo {field} is malformed") from error
    if parsed < 0:
        raise DataProviderError(f"CNInfo {field} cannot be negative")
    return parsed


def _published_at(value: object) -> datetime | None:
    try:
        milliseconds = int(str(value))
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)


def _date_range(start_date: str, end_date: str) -> tuple[str, str]:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as error:
        raise ValueError("CNInfo dates must use YYYY-MM-DD") from error
    if end < start:
        raise ValueError("CNInfo end_date cannot precede start_date")
    return start.isoformat(), end.isoformat()


def _boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError("capture_artifacts must be true or false")
    return normalized == "true"


def _bounded_integer(value: str, *, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


__all__ = [
    "CNINFO_DIRECT_PROVIDER_ID",
    "CnInfoArtifactDownload",
    "CnInfoDirectClient",
    "CnInfoDirectEvidenceAdapter",
    "CnInfoHttpClient",
    "CnInfoQueryResult",
    "cninfo_calibration_snapshot",
]
