from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def macro_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.MACRO,
        source_id="screening.macro",
    )


__all__ = ["macro_evaluator"]
