"""Revenue, profit, ROE, and ROIC growth screening."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def growth_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.GROWTH,
        source_id="screening.growth",
    )


__all__ = ["growth_evaluator"]
