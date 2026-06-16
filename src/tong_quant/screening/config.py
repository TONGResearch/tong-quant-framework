from tong_quant.config.settings import ScreeningSettings
from tong_quant.domain.enums import ScoreType
from tong_quant.screening.engine import ScreeningEngine
from tong_quant.screening.policies import default_market_policies
from tong_quant.screening.research_queue import WeightedQueuePrioritizer
from tong_quant.screening.scoring import ScoreConfig, WeightedScoreAggregator


def screening_engine_from_settings(settings: ScreeningSettings) -> ScreeningEngine:
    return ScreeningEngine(
        policies=default_market_policies(),
        research_scorer=WeightedScoreAggregator(
            ScoreConfig(
                score_type=ScoreType.RESEARCH,
                weights=settings.research_score.weights,
                model_version=settings.research_score.model_version,
                maximum_component_weight=settings.research_score.maximum_component_weight,
                require_all_components=settings.research_score.require_all_components,
            )
        ),
        prioritizer=WeightedQueuePrioritizer(
            research_weight=settings.research_queue.research_weight,
            urgency_weight=settings.research_queue.urgency_weight,
            confidence_weight=settings.research_queue.confidence_weight,
        ),
    )
