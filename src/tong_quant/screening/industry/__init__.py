"""Industry growth, structure, and heat screening."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def industry_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.INDUSTRY,
        source_id="screening.industry",
    )


__all__ = ["industry_evaluator"]
