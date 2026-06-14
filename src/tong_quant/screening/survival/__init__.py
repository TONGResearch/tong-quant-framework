"""Fraud, debt, cash-flow, and business-viability screening."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def survival_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.SURVIVAL,
        source_id="screening.survival",
    )


__all__ = ["survival_evaluator"]
