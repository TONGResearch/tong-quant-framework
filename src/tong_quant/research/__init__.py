"""Point-in-time-safe, explainable traditional investment research engine."""

from tong_quant.research.engine import ResearchEngine
from tong_quant.research.reporting import DefaultResearchReportBuilder

__all__ = ["DefaultResearchReportBuilder", "ResearchEngine"]
