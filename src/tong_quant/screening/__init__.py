"""Explainable screening engine.

Every screening dimension emits universal Signals and never creates orders.
"""
from tong_quant.screening.engine import ScreeningEngine
from tong_quant.screening.models import (
    CompositeScore,
    DimensionAssessment,
    HardScreenObservation,
    InvestmentAssessment,
    OpportunityCandidate,
    ResearchOutcome,
    ResearchQueueEntry,
    ScreeningOutcome,
    ScreeningRequest,
    ScreeningRun,
    Watchlist,
)

__all__ = [
    "CompositeScore",
    "DimensionAssessment",
    "HardScreenObservation",
    "InvestmentAssessment",
    "OpportunityCandidate",
    "ResearchOutcome",
    "ResearchQueueEntry",
    "ScreeningEngine",
    "ScreeningOutcome",
    "ScreeningRequest",
    "ScreeningRun",
    "Watchlist",
]
