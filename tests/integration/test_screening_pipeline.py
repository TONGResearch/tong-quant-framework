from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.config.settings import load_settings
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Market,
    ResearchQueueStatus,
    ScoreType,
    ScreeningDimensionName,
    SecurityStatus,
)
from tong_quant.domain.models import Instrument, InstrumentStatus
from tong_quant.screening.config import screening_engine_from_settings
from tong_quant.screening.models import (
    DimensionAssessment,
    HardScreenObservation,
    OpportunityCandidate,
    ScreeningRequest,
    screening_instrument_id,
)
from tong_quant.screening.repository import SQLiteScreeningRepository

pytestmark = pytest.mark.integration


def test_screening_to_research_queue_persistence(tmp_path: Path) -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=as_of,
        source="test",
    )
    candidate = OpportunityCandidate(
        instrument=instrument,
        discovery_source="discovery.earnings_surprise",
        discovered_at=as_of,
        available_at=as_of,
        thesis="Unexpected earnings improvement deserves research",
        evidence=("Point-in-time earnings release",),
        urgency_score=80,
        confidence_score=75,
    )
    observation = HardScreenObservation(
        candidate=candidate,
        as_of=as_of,
        available_at=as_of,
        status=InstrumentStatus(
            instrument,
            effective_from=date(2026, 1, 1),
            status=SecurityStatus.LISTED,
            is_tradable=True,
            available_at=as_of,
            source="test",
        ),
        data_quality_passed=True,
        average_daily_turnover=Decimal("10000000"),
        financial_health_score=75,
    )
    assessments = tuple(
        DimensionAssessment(
            dimension=dimension,
            score=65,
            confidence=80,
            evaluated_at=as_of,
            available_at=as_of,
            reasons=(f"{dimension.value} evidence",),
            source=f"screening.{dimension.value}",
            model_version="v0.4",
        )
        for dimension in ScreeningDimensionName
    )
    settings = load_settings(Path("config/default.toml"))
    run = screening_engine_from_settings(settings.screening).run(
        ScreeningRequest(
            market=Market.CHINA_A,
            as_of=as_of,
            observations=(observation,),
            assessments={screening_instrument_id(instrument): assessments},
        )
    )
    outcome = run.outcomes[0]

    store = SQLiteStore(tmp_path / "screening.sqlite3")
    store.initialize()
    store.upsert_instruments([instrument])
    SQLiteScreeningRepository(store).save_outcome(outcome)

    queue = store.research_queue(status=ResearchQueueStatus.PENDING)
    latest_score = store.latest_screening_score(
        instrument,
        ScoreType.RESEARCH,
        as_of=as_of,
    )
    assert len(queue) == 1
    assert run.watchlist.candidates == (candidate,)
    assert run.research_queue == (outcome.queue_entry,)
    assert queue[0]["priority_score"] != queue[0]["urgency_score"]
    assert store.table_count("research_queue") == 1
    assert store.table_count("screening_scorecards") == 1
    assert store.table_count("screening_results") == 12
    assert latest_score is not None
    assert latest_score["score"] == 65
