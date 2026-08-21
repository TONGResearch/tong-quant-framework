import os
from datetime import UTC, datetime

import pytest

from tong_quant.data.providers.cninfo import CNINFO_DISCLOSURES_DATASET
from tong_quant.data.providers.cninfo_direct import (
    CnInfoDirectEvidenceAdapter,
    CnInfoHttpClient,
)
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.domain.enums import Market

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_data,
    pytest.mark.skipif(
        os.getenv("TONG_QUANT_LIVE_CNINFO") != "1",
        reason="set TONG_QUANT_LIVE_CNINFO=1 to run direct CNInfo network checks",
    ),
]


def test_direct_cninfo_public_metadata_contract() -> None:
    now = datetime.now(UTC)
    batch = CnInfoDirectEvidenceAdapter(
        client=CnInfoHttpClient(max_attempts=1, max_pages=1),
        clock=lambda: datetime.now(UTC),
    ).fetch(
        ProviderDatasetRequest(
            dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A,
            subject="300777",
            as_of=now,
            parameters={
                "start_date": "2025-01-02",
                "end_date": "2025-01-02",
                "capture_artifacts": "false",
                "max_artifacts": "0",
            },
        )
    )

    assert batch.provider == "cninfo_direct"
    assert batch.raw_record_count >= 1
    assert all(record.payload.get("announcement_id") for record in batch.records)
