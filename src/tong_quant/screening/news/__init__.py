"""News sentiment, regulation, and policy screening."""
from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.screening.dimensions import EvidenceDimensionEvaluator


def news_evaluator() -> EvidenceDimensionEvaluator:
    return EvidenceDimensionEvaluator(
        dimension=ScreeningDimensionName.NEWS,
        source_id="screening.news",
    )


__all__ = ["news_evaluator"]
