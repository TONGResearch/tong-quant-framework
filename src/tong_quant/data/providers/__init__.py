"""External market and fundamental data provider adapters."""

from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.calibration import AkShareCalibrationAdapter
from tong_quant.data.providers.cninfo import CnInfoEvidenceAdapter
from tong_quant.data.providers.cninfo_direct import (
    CnInfoDirectEvidenceAdapter,
    CnInfoHttpClient,
)
from tong_quant.data.providers.tushare import TushareCalibrationAdapter
from tong_quant.data.providers.yahoo import YahooFinanceEvidenceAdapter

__all__ = [
    "AkShareAdapter",
    "AkShareCalibrationAdapter",
    "CnInfoEvidenceAdapter",
    "CnInfoDirectEvidenceAdapter",
    "CnInfoHttpClient",
    "TushareCalibrationAdapter",
    "YahooFinanceEvidenceAdapter",
]
