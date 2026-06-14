"""Positioning screens that avoid obvious tops without bottom picking."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def positioning_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.POSITIONING,
        source_id="screening.positioning",
    )


__all__ = ["positioning_evaluator"]
