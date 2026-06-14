from dataclasses import dataclass
from decimal import Decimal

from tong_quant.domain.enums import SecurityStatus
from tong_quant.screening.models import HardScreenObservation, HardScreenResult


def _result(
    observation: HardScreenObservation,
    rule_id: str,
    passed: bool,
    reason: str,
    **features: float | int | str | bool | None,
) -> HardScreenResult:
    return HardScreenResult(
        rule_id=rule_id,
        passed=passed,
        evaluated_at=observation.as_of,
        available_at=observation.available_at,
        reasons=(reason,),
        features=features,
    )


@dataclass(frozen=True, slots=True)
class DataQualityRule:
    rule_id: str = "data_quality"

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult:
        return _result(
            observation,
            self.rule_id,
            observation.data_quality_passed,
            (
                "Required point-in-time data passed quality checks"
                if observation.data_quality_passed
                else "Required point-in-time data failed quality checks"
            ),
        )


@dataclass(frozen=True, slots=True)
class SecurityLifecycleRule:
    rejected_statuses: frozenset[SecurityStatus]
    require_tradable: bool = True
    rule_id: str = "security_lifecycle"

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult:
        status = observation.status
        if status is None:
            return _result(
                observation,
                self.rule_id,
                False,
                "Historical security status is unavailable",
            )
        rejected = status.status in self.rejected_statuses
        untradable = self.require_tradable and not status.is_tradable
        passed = not rejected and not untradable
        return _result(
            observation,
            self.rule_id,
            passed,
            (
                f"Security lifecycle status {status.status.value} is eligible"
                if passed
                else f"Security lifecycle status {status.status.value} is not eligible"
            ),
            security_status=status.status.value,
            is_tradable=status.is_tradable,
        )


@dataclass(frozen=True, slots=True)
class RiskFlagRule:
    rejected_flags: frozenset[str]
    rule_id: str = "risk_flags"

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult:
        failures = sorted(observation.risk_flags.intersection(self.rejected_flags))
        return _result(
            observation,
            self.rule_id,
            not failures,
            (
                "No configured hard risk flags were detected"
                if not failures
                else f"Hard risk flags detected: {', '.join(failures)}"
            ),
            failure_count=len(failures),
        )


@dataclass(frozen=True, slots=True)
class LiquidityRule:
    minimum_average_turnover: Decimal | None
    require_metric: bool = True
    rule_id: str = "liquidity"

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult:
        turnover = observation.average_daily_turnover
        if turnover is None:
            passed = not self.require_metric
            return _result(
                observation,
                self.rule_id,
                passed,
                (
                    "Liquidity metric is optional and unavailable"
                    if passed
                    else "Required historical liquidity metric is unavailable"
                ),
            )
        threshold = self.minimum_average_turnover
        passed = threshold is None or turnover >= threshold
        return _result(
            observation,
            self.rule_id,
            passed,
            (
                "Historical average turnover meets the configured market threshold"
                if passed
                else "Historical average turnover is below the configured market threshold"
            ),
            average_daily_turnover=str(turnover),
            minimum_average_turnover=None if threshold is None else str(threshold),
        )


@dataclass(frozen=True, slots=True)
class FinancialHealthRule:
    minimum_score: float | None
    require_metric: bool = True
    rule_id: str = "financial_health"

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult:
        score = observation.financial_health_score
        if score is None:
            passed = not self.require_metric
            return _result(
                observation,
                self.rule_id,
                passed,
                (
                    "Financial-health metric is optional and unavailable"
                    if passed
                    else "Required point-in-time financial-health metric is unavailable"
                ),
            )
        passed = self.minimum_score is None or score >= self.minimum_score
        return _result(
            observation,
            self.rule_id,
            passed,
            (
                "Financial health meets the configured minimum"
                if passed
                else "Extreme financial weakness failed the configured minimum"
            ),
            financial_health_score=score,
            minimum_score=self.minimum_score,
        )


@dataclass(frozen=True, slots=True)
class HardScreenPipeline:
    rules: tuple[
        DataQualityRule
        | SecurityLifecycleRule
        | RiskFlagRule
        | LiquidityRule
        | FinancialHealthRule,
        ...,
    ]

    def evaluate(
        self,
        observation: HardScreenObservation,
    ) -> tuple[HardScreenResult, ...]:
        results = []
        for rule in self.rules:
            result = rule.evaluate(observation)
            results.append(result)
            if not result.passed:
                break
        return tuple(results)
