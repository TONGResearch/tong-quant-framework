"""PE, PB, EV/EBITDA, and future valuation screening."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def valuation_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.VALUATION,
        source_id="screening.valuation",
    )


__all__ = ["valuation_evaluator"]
