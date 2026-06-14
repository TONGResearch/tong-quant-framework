from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from tong_quant.config.settings import RegimeModelSettings
from tong_quant.data.service import MarketDataService
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Instrument, Signal
from tong_quant.market_regime.base import WeightedMarketRegimeClassifier
from tong_quant.market_regime.config import scoring_config
from tong_quant.market_regime.metrics import trend_metric
from tong_quant.market_regime.models import MarketRegime, MarketRegimeInput, RegimeMetric
from tong_quant.market_regime.scoring import RegimeScoringConfig

CHINA_REQUIRED_METRICS = frozenset(
    {
        "csi_300_trend",
        "csi_all_share_trend",
        "rising_stocks",
        "market_turnover",
        "market_breadth",
    }
)


def default_china_scoring_config() -> RegimeScoringConfig:
    return RegimeScoringConfig(
        weights={
            "csi_300_trend": 0.25,
            "csi_all_share_trend": 0.20,
            "rising_stocks": 0.20,
            "market_turnover": 0.15,
            "market_breadth": 0.20,
        },
        bull_threshold=25,
        bear_threshold=-25,
        model_version="china-v0.3",
    )


def china_classifier_from_settings(
    settings: RegimeModelSettings,
) -> "ChinaMarketRegimeClassifier":
    return ChinaMarketRegimeClassifier(config=scoring_config(settings))


@dataclass(frozen=True, slots=True)
class ChinaMarketRegimeClassifier:
    config: RegimeScoringConfig = field(default_factory=default_china_scoring_config)
    source_id: str = "market_regime.china"
    required_metrics: frozenset[str] = CHINA_REQUIRED_METRICS

    def classify(self, inputs: MarketRegimeInput) -> tuple[MarketRegime, Signal]:
        classifier = WeightedMarketRegimeClassifier(
            source_id=self.source_id,
            required_metrics=self.required_metrics,
            config=self.config,
            signal_instrument=Instrument(
                symbol="CHINA_A_MARKET",
                market=Market.CHINA_A,
                name="China A-share Market",
                asset_type=AssetType.INDEX,
                currency="CNY",
                lot_size=1,
            ),
        )
        return classifier.classify(inputs)


@dataclass(frozen=True, slots=True)
class ChinaMarketRegimeInputBuilder:
    data: MarketDataService
    csi_300_symbol: str = "000300"
    csi_all_share_symbol: str = "000985"
    lookback_days: int = 140

    def build(
        self,
        *,
        market: Market,
        as_of: datetime,
        external_metrics: Mapping[str, RegimeMetric],
    ) -> MarketRegimeInput:
        if market is not Market.CHINA_A:
            raise ValueError("China regime builder requires the China A-share market")
        start = as_of.date() - timedelta(days=self.lookback_days)
        csi_300 = self.data.daily_bars(
            self.csi_300_symbol,
            market,
            AssetType.INDEX,
            start,
            as_of.date(),
            as_of=as_of,
        )
        csi_all_share = self.data.daily_bars(
            self.csi_all_share_symbol,
            market,
            AssetType.INDEX,
            start,
            as_of.date(),
            as_of=as_of,
        )
        metrics = (
            trend_metric(csi_300, name="csi_300_trend", as_of=as_of),
            trend_metric(csi_all_share, name="csi_all_share_trend", as_of=as_of),
            _required_external(external_metrics, "rising_stocks", as_of),
            _required_external(external_metrics, "market_turnover", as_of),
            _required_external(external_metrics, "market_breadth", as_of),
        )
        return MarketRegimeInput(
            market=market,
            as_of=as_of,
            metrics=metrics,
            subject="China A-share market",
        )


def _required_external(
    metrics: Mapping[str, RegimeMetric],
    name: str,
    as_of: datetime,
) -> RegimeMetric:
    try:
        metric = metrics[name]
    except KeyError as error:
        raise ValueError(f"missing external regime metric: {name}") from error
    if metric.available_at > as_of:
        raise ValueError(f"future external metric is not allowed: {name}")
    return metric
