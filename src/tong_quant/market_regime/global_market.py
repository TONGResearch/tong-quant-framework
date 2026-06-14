from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from tong_quant.config.settings import RegimeModelSettings
from tong_quant.data.service import MarketDataService
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Instrument, Signal
from tong_quant.market_regime.base import WeightedMarketRegimeClassifier
from tong_quant.market_regime.config import scoring_config
from tong_quant.market_regime.metrics import (
    relative_strength_metric,
    trend_metric,
    volatility_metric,
)
from tong_quant.market_regime.models import MarketRegime, MarketRegimeInput, RegimeMetric
from tong_quant.market_regime.scoring import RegimeScoringConfig

GLOBAL_REQUIRED_METRICS = frozenset(
    {
        "major_index_trend",
        "market_breadth",
        "volatility",
        "relative_strength",
    }
)


def default_global_scoring_config() -> RegimeScoringConfig:
    return RegimeScoringConfig(
        weights={
            "major_index_trend": 0.35,
            "market_breadth": 0.25,
            "volatility": 0.20,
            "relative_strength": 0.20,
        },
        bull_threshold=25,
        bear_threshold=-25,
        model_version="global-v0.3",
    )


def global_classifier_from_settings(
    market: Market,
    subject: str,
    settings: RegimeModelSettings,
) -> "GlobalMarketRegimeClassifier":
    return GlobalMarketRegimeClassifier(
        market=market,
        subject=subject,
        config=scoring_config(settings),
    )


@dataclass(frozen=True, slots=True)
class GlobalMarketRegimeClassifier:
    market: Market
    subject: str
    config: RegimeScoringConfig = field(default_factory=default_global_scoring_config)
    source_id: str = "market_regime.global"
    required_metrics: frozenset[str] = GLOBAL_REQUIRED_METRICS

    def __post_init__(self) -> None:
        if self.market is Market.CHINA_A:
            raise ValueError("use ChinaMarketRegimeClassifier for A-shares")

    def classify(self, inputs: MarketRegimeInput) -> tuple[MarketRegime, Signal]:
        classifier = WeightedMarketRegimeClassifier(
            source_id=self.source_id,
            required_metrics=self.required_metrics,
            config=self.config,
            signal_instrument=Instrument(
                symbol=f"{self.market.value.upper()}_MARKET",
                market=self.market,
                name=self.subject,
                asset_type=AssetType.INDEX,
                currency=_currency(self.market),
                lot_size=1,
            ),
        )
        return classifier.classify(inputs)


@dataclass(frozen=True, slots=True)
class GlobalMarketRegimeInputBuilder:
    data: MarketDataService
    market: Market
    major_index_symbol: str
    benchmark_symbol: str
    subject: str
    lookback_days: int = 180

    def __post_init__(self) -> None:
        if self.market is Market.CHINA_A:
            raise ValueError("use ChinaMarketRegimeInputBuilder for A-shares")

    def build(
        self,
        *,
        market: Market,
        as_of: datetime,
        external_metrics: Mapping[str, RegimeMetric],
    ) -> MarketRegimeInput:
        if market is not self.market:
            raise ValueError("requested market does not match global regime builder")
        start = as_of.date() - timedelta(days=self.lookback_days)
        major_index = self.data.daily_bars(
            self.major_index_symbol,
            market,
            AssetType.INDEX,
            start,
            as_of.date(),
            as_of=as_of,
        )
        benchmark = self.data.daily_bars(
            self.benchmark_symbol,
            market,
            AssetType.INDEX,
            start,
            as_of.date(),
            as_of=as_of,
        )
        breadth = _required_external(external_metrics, "market_breadth", as_of)
        metrics = (
            trend_metric(major_index, name="major_index_trend", as_of=as_of),
            breadth,
            volatility_metric(major_index, name="volatility", as_of=as_of),
            relative_strength_metric(
                major_index,
                benchmark,
                name="relative_strength",
                as_of=as_of,
            ),
        )
        return MarketRegimeInput(
            market=market,
            as_of=as_of,
            metrics=metrics,
            subject=self.subject,
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


def _currency(market: Market) -> str:
    return {
        Market.US: "USD",
        Market.HONG_KONG: "HKD",
        Market.MALAYSIA: "MYR",
    }[market]
