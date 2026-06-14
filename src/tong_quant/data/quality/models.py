from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    message: str
    severity: Severity
    row: int | None = None


@dataclass(frozen=True, slots=True)
class QualityReport:
    dataset: str
    rows: int
    issues: tuple[QualityIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity is Severity.ERROR for issue in self.issues)

    @property
    def rejected_rows(self) -> int:
        return len({issue.row for issue in self.issues if issue.row is not None})


class DataQualityError(ValueError):
    def __init__(self, report: QualityReport) -> None:
        self.report = report
        summary = "; ".join(issue.message for issue in report.issues[:5])
        super().__init__(f"{report.dataset} failed data quality checks: {summary}")
