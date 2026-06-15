from enum import StrEnum


class Market(StrEnum):
    CHINA_A = "china_a"
    US = "us"
    HONG_KONG = "hong_kong"
    MALAYSIA = "malaysia"


class AssetType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"


class SecurityStatus(StrEnum):
    LISTED = "listed"
    SUSPENDED = "suspended"
    SPECIAL_TREATMENT = "special_treatment"
    DELISTING = "delisting"
    DELISTED = "delisted"


class ScreeningDimensionName(StrEnum):
    NEWS = "news"
    INDUSTRY = "industry"
    SURVIVAL = "survival"
    GROWTH = "growth"
    VALUATION = "valuation"
    POSITIONING = "positioning"
    MACRO = "macro"


class ScoreType(StrEnum):
    RESEARCH = "research"
    INVESTMENT = "investment"


class ResearchQueueStatus(StrEnum):
    PENDING = "pending"
    IN_RESEARCH = "in_research"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ResearchModuleName(StrEnum):
    POLICY = "policy"
    FINANCIAL = "financial"
    INDUSTRY = "industry"
    VALUE = "value"
    TECHNICAL = "technical"
    TREND = "trend"
    PATTERN = "pattern"


class ResearchConclusion(StrEnum):
    SUPPORTIVE = "supportive"
    MIXED = "mixed"
    CAUTION = "caution"
    ADVERSE = "adverse"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"


class ResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    FAILED_POINT_IN_TIME_CHECK = "failed_point_in_time_check"


class ValidationModuleName(StrEnum):
    HISTORICAL = "historical"
    WALK_FORWARD = "walk_forward"
    OUT_OF_SAMPLE = "out_of_sample"
    MARKET_REGIME = "market_regime"
    THESIS = "thesis"
    FACTOR_CONTRIBUTION = "factor_contribution"
    RESEARCH_ACCURACY = "research_accuracy"
    DECISION_JOURNAL = "decision_journal"
    PORTFOLIO_RISK = "portfolio_risk"


class ValidationStatus(StrEnum):
    RELIABLE = "reliable"
    CONDITIONALLY_RELIABLE = "conditionally_reliable"
    INCONCLUSIVE = "inconclusive"
    UNRELIABLE = "unreliable"
    FAILED_INTEGRITY_CHECK = "failed_integrity_check"


class ValidationRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class ValidationSplitKind(StrEnum):
    TRAINING = "training"
    VALIDATION = "validation"
    OUT_OF_SAMPLE = "out_of_sample"


class ThesisOutcomeStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    INVALIDATED = "invalidated"
    UNRESOLVED = "unresolved"
    NOT_OBSERVABLE = "not_observable"


class DecisionDisposition(StrEnum):
    ADVANCE = "advance"
    DEFER = "defer"
    REJECT = "reject"
    NO_ACTION = "no_action"


class EvidenceQuality(StrEnum):
    PRIMARY = "primary"
    VERIFIED_SECONDARY = "verified_secondary"
    SECONDARY = "secondary"
    ESTIMATED = "estimated"


class Adjustment(StrEnum):
    NONE = "none"
    FORWARD = "forward"
    BACKWARD = "backward"


class SignalAction(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    WATCH = "watch"
    RESEARCH = "research"
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"
    HOLD = "hold"
    BLOCK = "block"
    REVIEW = "review"


class SignalStage(StrEnum):
    DISCOVERY = "discovery"
    SCREENING = "screening"
    RESEARCH = "research"
    STRATEGY = "strategy"
    MARKET_REGIME = "market_regime"
    RISK = "risk"
    AI = "ai"
    VALIDATION = "validation"


class Regime(StrEnum):
    BULL = "bull"
    TRANSITION_TO_BULL = "transition_to_bull"
    SIDEWAYS = "sideways"
    TRANSITION_TO_BEAR = "transition_to_bear"
    BEAR = "bear"


class ExecutionMode(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    SEMI_AUTOMATIC = "semi_automatic"
    AUTOMATIC = "automatic"
