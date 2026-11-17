"""Readable rendering of existing overseas diagnostics, never an official report."""

from collections.abc import Mapping
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.application.technical_binding import verify_technical_binding
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.version import (
    CALENDAR_COVERAGE_NOTE_VERSION,
    CALENDAR_YEAR_COVERAGE_VERSION,
    EQUITY_BOUND_NOTE_VERSION,
    EQUITY_NOTE_VERSION,
    HOLDING_REVIEW_VERSION,
    LONG_HORIZON_DIAGNOSTICS_VERSION,
    LONG_HORIZON_NOTE_VERSION,
    MULTI_TIMEFRAME_DIAGNOSTICS_VERSION,
    MULTI_TIMEFRAME_NOTE_VERSION,
    NASDAQ_CALENDAR_AGE_VERSION,
    NASDAQ_CALENDAR_VERSION,
    NASDAQ_PRICE_NOTE_CONTEXT_VERSION,
    NASDAQ_PRICE_REVIEW_VERSION,
    TREND_PRICE_OBSERVATIONS_VERSION,
)

_CONFLUENCE = {
    "BULLISH_TECHNICAL_ALIGNMENT": "趋势与动能同向偏强；不是买入批准",
    "BEARISH_TECHNICAL_ALIGNMENT": "趋势与动能同向偏弱；不是自动卖出指令",
    "CONFLICTED": "技术家族存在冲突；不能把冲突等同于一定下跌",
    "NEUTRAL": "技术观测中性，没有一致方向",
    "INSUFFICIENT_DATA": "技术数据不足，不能形成完整技术观测",
}
_METRICS = {
    "annualTotalRevenue": "原生年度营收",
    "annualNetIncome": "原生年度净利润",
    "annualOperatingCashFlow": "原生年度经营现金流",
    "annualTotalAssets": "原生资产总额",
    "annualTotalLiabilitiesNetMinorityInterest": "原生负债字段",
    "annualStockholdersEquity": "原生股东权益",
    "annualTotalDebt": "原生债务字段",
}
_AUTHORITIES = (
    "execution_authorized", "validation_authorized", "investment_scoring_authorized",
    "historical_replay_eligible", "financial_scoring_authorized",
)


def _cell(value: object) -> str:
    if value is None:
        return "未取得"
    text = format(value, ".8g") if type(value) is float else str(value)
    if len(text) > 1000:
        raise ValueError("equity diagnostic label exceeds display bound")
    return text.replace("\\", "\\\\").replace("|", "\\|").replace(
        "\n", " ").replace("\r", " ").replace("<", "&lt;").replace(
        ">", "&gt;").replace("[", "\\[").replace("]", "\\]")


def _receipt(receipt: Mapping[str, Any]) -> None:
    body = {key: value for key, value in receipt.items() if key != "input_hash"}
    if sha256(financial_input_json(body).encode()).hexdigest() != receipt.get("input_hash"):
        raise ValueError("equity diagnostic receipt hash mismatch")
    if any(receipt.get(name) is not False for name in (
        "execution_authorized", "validation_authorized", "investment_scoring_authorized",
        "historical_replay_eligible",
    )):
        raise ValueError("equity diagnostic cannot render admitted trade inputs")


def _utc_cutoff(value: object) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("equity note cutoff must be an aware datetime")
    require_timezone(value, "equity note cutoff")
    return value.astimezone(UTC)


def render_equity_note(
    document: Mapping[str, Any], *, technical_source: GlobalPriceInputs | None = None,
    technical_parameters: TechnicalParameters | None = None,
) -> str:
    """Presentation only; caller must use existing retained-source readers, not arbitrary JSON."""
    reject_sensitive_structure(document)
    encoded = financial_input_json(dict(document))
    if len(encoded.encode()) > 2 * 1024 * 1024:
        raise ValueError("equity diagnostic exceeds display bound")
    if (document.get("research_only") is not True
            or document.get("research_report_created") is not False
            or document.get("readiness_promoted") is not False
            or any(name in document and document[name] is not False for name in _AUTHORITIES)):
        raise ValueError("equity note requires unqualified research diagnostics")
    inputs, technical = document["inputs"], document["diagnostics"]
    _receipt(inputs)
    market = Market(inputs["market"])
    symbol = inputs["subject"]
    validate_yahoo_equity_subject(market, symbol)
    cutoff = _utc_cutoff(inputs.get("as_of"))
    binding = None
    if "technical_binding" in document:
        if technical_source is None or technical_parameters is None:
            raise ValueError("bound technical display requires original snapshot and parameters")
        binding = verify_technical_binding(document, technical_source, technical_parameters)
    elif technical_source is not None or technical_parameters is not None:
        raise ValueError("technical source verification requires explicit binding receipt")
    horizon = document.get("long_horizon")
    note_version = EQUITY_NOTE_VERSION if horizon is None else (
        MULTI_TIMEFRAME_NOTE_VERSION if horizon.get("model_version") == (
            MULTI_TIMEFRAME_DIAGNOSTICS_VERSION) else LONG_HORIZON_NOTE_VERSION)
    coverage = document.get("calendar_coverage")
    annual_coverage = horizon is not None and coverage is not None and coverage.get(
        "model_version") == CALENDAR_YEAR_COVERAGE_VERSION
    if annual_coverage:
        note_version = CALENDAR_COVERAGE_NOTE_VERSION
    if document.get("nasdaq_calendar_review") is not None:
        note_version = NASDAQ_PRICE_NOTE_CONTEXT_VERSION
    if binding is not None:
        note_version = EQUITY_BOUND_NOTE_VERSION
    if (technical.get("technical_research_only") is not True
            or technical.get("technical_scoring_admitted") is not False):
        raise ValueError("equity note requires unscored technical diagnostics")
    rows = [
        f"# {_cell(symbol)} · {_cell(market.value)} · 单股研究摘要",
        "", "这是现有代码的诊断输出，不是正式 ResearchReport、已验证买卖信号或执行指令。",
        "", "## 数据与结论边界",
        f"- 分析时点（UTC）：{cutoff.astimezone(UTC).isoformat()}",
        f"- 行情状态：{_cell(inputs['status'])}；观测条数：{_cell(inputs['observed_bar_count'])}",
        f"- 数据可信度上限：{_cell(inputs['trust_ceiling'])}；可用时间精度："
        f"{_cell(inputs['availability_precision'])}",
        f"- 时效状态：{_cell(inputs['freshness'])}；未评估不代表新鲜或可执行。",
        "- 原生行情的复权、交易时段与独立一致性尚未全部核验。",
        "", "## 技术计算",
        "| 项目 | 代码结果 |", "| --- | --- |",
    ]
    for label, key in (
        ("日线末值（来源原生，非实时成交价）", "technical_latest_close"),
        ("日线观测时间（非已验证收市时刻）", "technical_last_observed_at"),
        ("输入状态", "technical_input_status"),
        ("趋势家族", "trend_structure_family"), ("动能家族", "momentum_family"),
        ("MACD DIF", "macd_dif"), ("MACD DEA", "macd_dea"),
        ("MACD 差值（DIF−DEA，未乘 2）", "macd_histogram"),
        ("KDJ K", "kdj_k"), ("KDJ D", "kdj_d"), ("KDJ J", "kdj_j"),
        ("ATR（研究波动参考）", "technical_atr"),
        ("启动形态状态", "setup_state"), ("形态方向", "setup_direction"),
        ("三线事件", "triple_average_events"), ("格兰维尔事件", "granville_events"),
        ("技术缺失项", "technical_missing_inputs"),
    ):
        value = technical.get(key)
        if value == "" and key in {"triple_average_events", "granville_events"}:
            value = "无当前事件"
        elif value == "" and key == "technical_missing_inputs":
            value = "无已声明预热缺口；不等于来源已验证"
        rows.append(f"| {label} | {_cell(value)} |")
    rows.extend(["", _CONFLUENCE.get(technical.get("technical_confluence"),
                                    "未知技术状态；不得自行补成方向性结论。"),
        "MACD/KDJ 属于同一动能家族；均线/三线/格兰维尔延续属于同一趋势家族，不能重复投票。"])
    if binding is not None:
        rows.extend(["", "## 日线技术展示绑定",
            "已与明确选择的原始行情快照重新计算并核对；不证明数据真实、PIT合格或策略有效。",
            f"- 绑定版本：{_cell(binding['model_version'])}",
            f"- 原始行数：{_cell(binding['supplied_daily_row_count'])}",
            f"- 绑定标识：{_cell(binding['binding_hash'])}",
            "缺失、失败与停牌状态仍保留；绑定通过不授权评分、持仓管理或交易。"])
    if technical.get("setup_state") in {"ARMED", "CONFIRMED"} and technical.get(
        "setup_direction") in {"bullish", "bearish"}:
        rows.extend([f"形态结构参考：{_cell(technical.get('structural_invalidation_reference'))}；"
                     f"动态参考：{_cell(technical.get('dynamic_invalidation_reference'))}。",
                     "方向必须一起阅读；这些不是持仓止损价，也不保证能成交。"])
    else:
        rows.append("当前没有有效的启动形态参考；失效/过期形态的旧数值不作为当前持仓止损。")
    trend = document.get("trend_price_observations")
    if trend is not None:
        body = {key: value for key, value in trend.items() if key != "input_hash"}
        if (sha256(financial_input_json(body).encode()).hexdigest() != trend.get("input_hash")
                or trend.get("model_version") != TREND_PRICE_OBSERVATIONS_VERSION
                or _utc_cutoff(trend.get("as_of")) != cutoff
                or trend.get("subject") not in {symbol, None}
                or trend.get("market") not in {market.value, None}
                or trend.get("four_confirmations_complete") is not False
                or trend.get("research_only") is not True
                or any(trend.get(name) is not False for name in (
                    "scoring_authorized", "execution_authorized", "validation_authorized",
                    "historical_replay_eligible"))):
            raise ValueError("equity note trend observations mismatch")
        rows.extend(["", "## 改进海龟价格与成交量观测", "| 项目 | 原公式观测 |",
                     "| --- | --- |"])
        for label, key in (("数据状态", "status"), ("参数", "parameters_json"),
            ("此前通道最高价（不含当前日线）", "prior_channel_high"),
            ("严格价格突破", "strict_breakout_observed"),
            ("突破研究阈值", "breakout_threshold_observed"),
            ("此前平均成交量", "prior_average_volume"), ("本次成交量比", "volume_ratio"),
            ("量能研究阈值", "volume_threshold_observed")):
            value = trend.get(key)
            displayed = "是" if value is True else "否" if value is False else _cell(value)
            rows.append(f"| {label} | {displayed} |")
        rows.extend(["情绪确认：未评估；行业热度确认：未评估。完整四确认未齐，不是有效交易信号。",
                     "通道价和 ATR 是未验证研究观测，不是推荐挂单价或持仓止损。"])
    if document.get("long_horizon") is not None:
        rows.extend(_long_horizon_rows(document, cutoff))
    if annual_coverage:
        rows.extend(_calendar_coverage_rows(document, cutoff))
    if document.get("nasdaq_calendar_review") is not None:
        rows.extend(_nasdaq_calendar_rows(document, cutoff))
    rows.extend(["", "## 基本面观测（不代替最新财报）"])
    financial = document.get("financial_review")
    if financial is None:
        rows.append("未请求基本面。不能据技术结果补出估值、财务健康或投资结论。")
    else:
        fundamentals = document["fundamentals"]
        _receipt(fundamentals)
        review_body = {key: value for key, value in financial.items() if key != "review_hash"}
        if sha256(financial_input_json(review_body).encode()).hexdigest() != financial.get(
            "review_hash"):
            raise ValueError("equity note financial review hash mismatch")
        if (financial.get("subject") != symbol or financial.get("market") != market.value
                or _utc_cutoff(financial.get("as_of")) != cutoff
                or fundamentals.get("subject") != symbol
                or fundamentals.get("market") != market.value
                or financial.get("source_input_hash") != fundamentals.get("input_hash")
                or _utc_cutoff(fundamentals.get("as_of")) != cutoff
                or any(financial.get(name) is not False for name in _AUTHORITIES)):
            raise ValueError("equity note financial input context mismatch")
        rows.extend([f"- 基本面来源状态：{_cell(document.get('fundamentals_status'))}",
            f"- 研究核对状态：{_cell(financial.get('status'))}",
            "- 以下变化只描述提供商原生字段，不证明会计可比性、增长质量或已准入评分。",
            "| 原生项目 | 本期标签 | 本期原生金额 | 上期标签 | 原生变化 % | 状态 |",
            "| --- | --- | --- | --- | --- | --- |"])
        for item in financial.get("comparisons", ()):
            values = (_METRICS.get(item["native_metric"], item["native_metric"]),
                item.get("current_period_end"),
                f"{_cell(item.get('currency'))} {_cell(item.get('current_value'))}",
                item.get("prior_period_end"), item.get("native_change_percent"), item.get("status"))
            rows.append("| " + " | ".join(_cell(value) for value in values) + " |")
        rows.extend(["", "仍需核对：最新季度披露、修订、期间和合并口径、行业定义、估值"
                     "及独立数据一致性。"])
    if document.get("holding_review") is not None:
        rows.extend(_holding_rows(document, cutoff))
    rows.extend(["", "## 尚未覆盖的决策条件",
        "- 改进海龟必须同时有突破、成交量、市场情绪和行业热度确认；本摘要没有补造四确认。",
        "- 市值风格、完整政策/行业研究和真实筛选队列不能由这份诊断替代；七加一仍暂缓。",
        ("- 手工持仓备注不是已核实的成交、现金或仓位连续性；不生成补仓、卖出金额或持有期限。"
         if document.get("holding_review") is not None else
         "- 没有持仓与成本记录，不能据旧形态参考生成补仓、卖出金额或持有期限。"),
        "- 未完成独立验证，不生成 InvestmentScore、订单、自动分配或实盘授权。",
        "", "## 复核标识",
        f"- 展示版本：{note_version}",
        f"- 行情输入：{_cell(inputs['input_hash'])}",
        f"- 技术输入：{_cell(technical.get('technical_input_hash'))}",
        f"- 原始诊断内容：{sha256(encoded.encode()).hexdigest()}",
        "哈希用于复核内容，不证明来源真实、策略盈利或可执行。", ""])
    return "\n".join(rows)


def _long_horizon_rows(document: Mapping[str, Any], cutoff: datetime) -> list[str]:
    receipt = document["long_horizon"]
    _receipt(receipt)
    inputs = document["inputs"]
    multi = receipt.get("model_version") == MULTI_TIMEFRAME_DIAGNOSTICS_VERSION
    if (receipt.get("model_version") not in {
            LONG_HORIZON_DIAGNOSTICS_VERSION, MULTI_TIMEFRAME_DIAGNOSTICS_VERSION}
            or ("weekly" in receipt) != multi or ("timeframe_alignment" in receipt) != multi
            or _utc_cutoff(receipt.get("as_of")) != cutoff
            or receipt.get("subject") not in {inputs["subject"], None}
            or receipt.get("market") != inputs["market"]
            or receipt.get("source_bars_content_hash") != inputs["bars_content_hash"]
            or receipt.get("supplied_daily_row_count") != inputs["observed_bar_count"]
            or receipt.get("research_only") is not True
            or any(receipt.get(key) is not False for key in (
                "calendar_verified", "source_adjustment_basis_verified", "scoring_authorized",
                "holding_management_authorized"))):
        raise ValueError("equity note long-horizon context mismatch")
    rows = ["", "## 周/月/年观察（未核验完整交易日覆盖）" if multi else
            "## 月线与年线观察（未核验完整交易日覆盖）",
        "未收完周期不进入指标；缺整期或停牌期间不跳过补算。参数是研究观测，不是交易规则。"]
    if multi:
        alignment = receipt["timeframe_alignment"]
        observed = alignment.get("daily_reference_observed_at")
        base_observed = inputs.get("last_observed_at")
        if (_utc_cutoff(alignment.get("as_of")) != cutoff
                or (observed is None) != (base_observed is None)
                or observed is not None and _utc_cutoff(observed) != _utc_cutoff(base_observed)
                or alignment.get("comparison_eligible") is not False
                or alignment.get("calendar_end_is_exchange_close") is not False):
            raise ValueError("equity note timeframe alignment mismatch")
        periods = alignment.get("periods")
        if (not isinstance(periods, (list, tuple)) or len(periods) != 3
                or {item.get("frequency") for item in periods} != {"weekly", "monthly", "yearly"}):
            raise ValueError("equity note requires exactly three distinct timeframe alignments")
        for item in periods:
            source_at = item.get("last_source_observed_at")
            age = item.get("lag_to_daily_observation_seconds")
            if item.get("last_ended_period_start") != receipt[item["frequency"]].get(
                "last_ended_period_start"
            ):
                raise ValueError("equity note timeframe period mismatch")
            if source_at is None:
                if age is not None:
                    raise ValueError("equity note missing timeframe cannot have an age")
            elif (observed is None or type(age) not in {int, float}
                  or age != (_utc_cutoff(observed) - _utc_cutoff(source_at)).total_seconds()
                  or age < 0):
                raise ValueError("equity note timeframe observation age mismatch")
            if any(item.get(key) is not None and _utc_cutoff(item[key]) > cutoff
                   for key in ("calendar_end_at", "latest_source_available_at")):
                raise ValueError("equity note timeframe contains future metadata")
        rows.extend([f"- 最新日线观察：{_cell(observed)}。",
            "| 周期 | 末个已结束周期起点 | 最后来源观察 | 与最新日线相差秒数 |",
            "| --- | --- | --- | --- |"])
        for item in periods:
            rows.append("| " + " | ".join(_cell(item[key]) for key in (
                "frequency", "last_ended_period_start", "last_source_observed_at",
                "lag_to_daily_observation_seconds")) + " |")
        rows.append("同一分析截止时间不等于同一天收盘；日历结束时刻不是经核验的交易所收盘。")
    frequencies = (("weekly", "周"), ("monthly", "月"), ("yearly", "年")) if multi else (
        ("monthly", "月"), ("yearly", "年"))
    for frequency, label in frequencies:
        item = receipt[frequency]
        rows.extend([f"### {label}度观察", f"- 状态：{_cell(item['status'])}；"
            f"已结束周期：{_cell(item['ended_period_count'])}；"
            f"实际计算周期：{_cell(item['calculation_period_count'])}。",
            f"- 末个已结束周期起点：{_cell(item['last_ended_period_start'])}；"
            f"末值：{_cell(item['last_ended_close'])}。",
            "| 均线周期 | 观察值 | 末值关系 | 状态 |", "| --- | --- | --- | --- |"])
        for average in item["moving_averages"]:
            rows.append("| " + " | ".join(_cell(average[key]) for key in (
                "periods", "value", "close_relation", "status")) + " |")
        for name in ("macd", "kdj"):
            indicator = item[name]
            rows.append(f"- {name.upper()}：{_cell(indicator['status'])}；需要"
                f"{_cell(indicator['required_periods'])}个{label}度观察，实际"
                f"{_cell(indicator['available_periods'])}个。")
            if indicator["values"] is not None:
                rows.append("  " + "；".join(f"{_cell(key)}={_cell(value)}"
                    for key, value in indicator["values"].items()))
    rows.extend(["同源日/周/月/年线不是独立投票；未核验覆盖、复权、来源及策略有效性。",
        "不据此估计持有年限或生成补仓/卖出指令。"])
    return rows


def _nasdaq_calendar_rows(document: Mapping[str, Any], cutoff: datetime) -> list[str]:
    receipt = document["nasdaq_calendar_review"]
    _receipt(receipt)
    source, inputs = receipt["source"], document["inputs"]
    body = {key: value for key, value in source.items() if key != "input_hash"}
    if (receipt.get("model_version") != NASDAQ_PRICE_REVIEW_VERSION
            or receipt.get("price_input_hash") != inputs["input_hash"]
            or receipt.get("subject") != inputs["subject"]
            or receipt.get("market") != inputs["market"] or inputs["market"] != "us"
            or _utc_cutoff(receipt.get("as_of")) != cutoff
            or receipt.get("status") != "SOURCE_OBSERVATION_ONLY"
            or receipt.get("exchange_pairing_status") != "NASDAQ_SOURCE_PRICE_VENUE_UNVERIFIED"
            or receipt.get("snapshot_scope") not in {"single_database_snapshot",
                "separate_database_snapshots_shared_cutoff"}
            or any(receipt.get(key) is not False for key in (
                "cross_store_atomicity_verified", "exchange_binding_verified", "calendar_complete",
                "canonical_calendar_authorized", "session_completeness_verified",
                "scoring_authorized"))
            or sha256(financial_input_json(body).encode()).hexdigest() != source.get("input_hash")
            or source.get("model_version") != NASDAQ_CALENDAR_VERSION
            or source.get("freshness_model_version") != NASDAQ_CALENDAR_AGE_VERSION
            or _utc_cutoff(source.get("as_of")) != cutoff or source.get("market") != "us"
            or source.get("exchange") != "NASDAQ"
            or type(source.get("year")) is not int or not 2000 <= source["year"] <= 2100
            or source.get("subject") != f"NASDAQ:{source['year']}"
            or source.get("trust_ceiling") != "LOW"
            or source.get("availability_precision") != "retrieval_time"
            or type(source.get("maximum_source_age_seconds")) is not int
            or source["maximum_source_age_seconds"] <= 0
            or any(source.get(key) is not False for key in (
                "published_at_known", "calendar_complete", "actual_session_verified",
                "canonical_calendar_authorized", "scoring_authorized",
                "historical_replay_eligible", "validation_authorized", "execution_authorized"))
            or source.get("source_capture_at") is not None and _utc_cutoff(
                source["source_capture_at"]) > cutoff
            or any(_utc_cutoff(row["available_at"]) > cutoff for row in source["captures"])
            or source["freshness"] != "WITHIN_CONFIGURED_LIMIT" and source["declarations"]
            or len(receipt["declaration_comparisons"]) != len(source["declarations"])):
        raise ValueError("equity note Nasdaq source context mismatch")
    captured = source["source_capture_at"]
    if captured is not None:
        elapsed = cutoff - _utc_cutoff(captured)
        age = (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds
        if (source["source_capture_age_microseconds"] != age
                or source["source_capture_age_seconds"] != age / 1_000_000):
            raise ValueError("equity note Nasdaq source age mismatch")
    else:
        age = None
    fresh = source["freshness"]
    if (fresh not in {"BLOCKED_INPUT", "WITHIN_CONFIGURED_LIMIT", "STALE"}
            or fresh == "WITHIN_CONFIGURED_LIMIT" and (
                age is None or not 0 <= age <= source["maximum_source_age_seconds"] * 1_000_000
                or source.get("source_bound") is not True
                or source.get("source_status") != "explicit_declarations_unqualified"
                or source["status"] != "explicit_declarations_unqualified"
                or source["declarations"] != source["observed_declarations"])):
        raise ValueError("equity note Nasdaq source freshness mismatch")
    rows = ["", "## Nasdaq 原文日历证据（独立来源，未认证完整日历）",
        f"- 来源状态：{_cell(source['status'])}；时效：{_cell(source['freshness'])}。",
        f"- 抓取时间：{_cell(source['source_capture_at'])}；"
        f"年龄（秒）：{_cell(source['source_capture_age_seconds'])}；"
        f"调用方上限（秒）：{_cell(source['maximum_source_age_seconds'])}。",
        f"- 当前声明：{len(source['declarations'])}；保留的原始观测："
        f"{len(source['observed_declarations'])}；原文哈希：{_cell(source.get('document_sha256'))}。",
        "- LOW / retrieval_time；抓取成功或未超时不能证明内容正确、最初发布日期或历史完整性。",
        f"- 数据快照：{_cell(receipt['snapshot_scope'])}；"
        "同一截止时间不代表跨库原子快照，也不验证股票所属交易所。",
        "| 声明日期 | 来源类型 | 来源当地提前收市时间 | 未来日期 | 日期对照状态 |",
        "| --- | --- | --- | --- | --- |"]
    for row, declaration in zip(receipt["declaration_comparisons"], source["declarations"],
                                strict=True):
        if (any(row.get(key) != value for key, value in declaration.items())
                or row.get("future_schedule_date") is not (
                    date.fromisoformat(declaration["trade_date"]) > cutoff.astimezone(
                        ZoneInfo("America/New_York")).date())
                or row.get("actual_session_verified") is not False
                or row.get("missing_open_observation_assessed") is not False):
            raise ValueError("equity note Nasdaq declaration mismatch")
        rows.append("| " + " | ".join(_cell(value) for value in (
            row["trade_date"], row["session_kind"], row["core_close_local"],
            row["future_schedule_date"], _nasdaq_date_comparison_label(row))) + " |")
    rows.extend(["提前收市时间属于来源的 America/New_York 声明，不是已核实的实际成交时段。",
        "未来日期、无可用行情或区间外日期显示未评估，不将原始False当作已经核对无冲突。",
        "过期或失败来源不参与当前日期对照，原始观测仍保留；没有旧的有利结果回退。",
        "未列出的日期仍未知；不复制到正式交易日历，不补齐周末，不改变上方覆盖率、指标或买卖权限。"])
    return rows


def _nasdaq_date_comparison_label(row: Mapping[str, Any]) -> str:
    future, inside, conflict = (row.get(key) for key in (
        "future_schedule_date", "within_price_observation_span",
        "closed_date_observation_conflict"))
    observed = row.get("price_date_observed")
    closed = row.get("session_kind") == "FULL_DAY_CLOSED"
    early = row.get("session_kind") == "EARLY_CORE_CLOSE"
    if (any(type(value) is not bool for value in (future, inside, conflict))
            or observed is not None and type(observed) is not bool
            or not (closed or early)
            or future and (observed is not None or inside)
            or observed is None and inside or observed is True and not inside
            or conflict is not (closed and observed is True and not future)):
        raise ValueError("equity note Nasdaq comparison state mismatch")
    if future:
        return "未评估（未来计划日期）"
    if observed is None:
        return "未评估（无可用行情对照）"
    if not inside:
        return "未评估（行情区间外）"
    if early:
        return "未评估（缺盘中时段依据）"
    return "候选日期冲突（未核验）" if conflict else "未见该日行情（非完整性认证）"


def _calendar_coverage_rows(document: Mapping[str, Any], cutoff: datetime) -> list[str]:
    receipt = document["calendar_coverage"]
    _receipt(receipt)
    inputs, horizon = document["inputs"], document["long_horizon"]
    if (receipt.get("model_version") != CALENDAR_YEAR_COVERAGE_VERSION
            or _utc_cutoff(receipt.get("as_of")) != cutoff
            or receipt.get("market") != inputs["market"]
            or receipt.get("subject") not in {inputs["subject"], None}
            or receipt.get("source_bars_content_hash") != inputs["bars_content_hash"]
            or receipt.get("supplied_daily_row_count") != inputs["observed_bar_count"]
            or receipt.get("calendar_period_input_hash") != horizon["calendar_input_hash"]
            or receipt.get("calendar_trust_level") != "unknown"
            or receipt.get("calendar_availability_precision") != "unknown"
            or receipt.get("calendar_scope") != "MARKET_ONLY_EXCHANGE_UNVERIFIED"
            or receipt.get("latest_calendar_available_at") is not None and _utc_cutoff(
                receipt["latest_calendar_available_at"]) > cutoff
            or any(receipt.get(key) is not False for key in (
                "calendar_verified", "session_completeness_verified",
                "source_adjustment_basis_verified", "scoring_authorized"))):
        raise ValueError("equity note calendar coverage context mismatch")
    rows = ["", "## 周/月/年交易日期覆盖核对（非来源认证）",
        f"- 核对状态：{_cell(receipt['status'])}；已读日历记录："
        f"{_cell(receipt['supplied_calendar_row_count'])}；"
        f"不同声明日期：{_cell(receipt['selected_calendar_date_count'])}。",
        "| 周期 | 已结束区间数 | 缺日历声明的区间数 | 缺已声明开市日行情数 | 休市日行情冲突数 |",
        "| --- | --- | --- | --- | --- |"]
    for frequency in ("weekly", "monthly", "yearly"):
        ended = [item for item in receipt[frequency] if item["calendar_period_ended"]]
        values = (frequency, len(ended),
                  sum(bool(item["unknown_calendar_dates"]) for item in ended),
                  sum(len(item["missing_open_dates"]) for item in ended),
                  sum(len(item["observed_on_declared_closed_dates"]) for item in ended))
        rows.append("| " + " | ".join(_cell(value) for value in values) + " |")
    rows.extend(["各周期分别计数，不能相加为独立证据；未知日期不能自动当作周末或休市。",
        "| 年度起点 | 状态 | 未知日历日期数 | 条件行情覆盖率 % |",
        "| --- | --- | --- | --- |"])
    for item in receipt["yearly"]:
        rows.append("| " + " | ".join(_cell(value) for value in (
            item["period_start_date"], item["status"], len(item["unknown_calendar_dates"]),
            item["observed_open_date_coverage_percent"])) + " |")
    rows.append("覆盖率仅针对给定声明；100%也不是完整交易时段、来源可信度或PIT验收。"
                "本核对不升级指标、评分或买卖权限。")
    return rows


def _holding_rows(document: Mapping[str, Any], cutoff: datetime) -> list[str]:
    review = document["holding_review"]
    body = {key: value for key, value in review.items() if key != "review_hash"}
    if (sha256(financial_input_json(body).encode()).hexdigest() != review.get("review_hash")
            or review.get("model_version") != HOLDING_REVIEW_VERSION
            or _utc_cutoff(review.get("as_of")) != cutoff
            or review.get("subject") != document["inputs"]["subject"]
            or review.get("market") != document["inputs"]["market"]
            or review.get("source_input_hash") != document["inputs"]["input_hash"]
            or review.get("technical_input_hash") != document["diagnostics"].get(
                "technical_input_hash")
            or review.get("research_only") is not True
            or any(review.get(name) is not False for name in (
                *_AUTHORITIES, "holding_management_authorized"))):
        raise ValueError("equity note holding review context mismatch")
    context = review["owner_context"]
    if (context.get("symbol") != review["subject"] or context.get("market") != review["market"]
            or _utc_cutoff(context.get("observed_at")) > _utc_cutoff(context.get("recorded_at"))
            or _utc_cutoff(context.get("recorded_at")) > cutoff):
        raise ValueError("equity note owner context mismatch")
    rows = ["", "## 持仓复核（手工备注，未验证）",
        "这不是已核实的券商账本，也不改变原始技术、基本面或验证结论。",
        f"- 数量：{_cell(context['quantity'])}；备注平均成本："
        f"{_cell(context['reported_average_cost'])} {_cell(context['currency'])}。",
        f"- 持仓观察时间：{_cell(context['observed_at'])}；意向："
        f"{_cell(context['investment_intent'])}，不是模型计算的期限。",
        f"- 手工记录时间：{_cell(context['recorded_at'])}；不是经认证的历史可用时间。",
        f"- 对照状态：{_cell(review['comparison_status'])}；"
        f"阻断原因：{_cell(review['blockers'])}。",
        f"- 本次行情观察时间：{_cell(review['price_observed_at'])}；"
        f"观察年龄（秒）：{_cell(review['price_age_seconds'])}。",
        f"- 价格与备注成本差异（%）：{_cell(review['price_only_change_percent'])}；"
        "不含费用、汇率、分红或仓位变化，不能当作账户实际收益。",
        f"- 用户声明的亏损复核阈值：{_cell(context['loss_review_percent'])}%；"
        f"本次观察：{_cell(review['loss_review_status'])}。这不是建议止损线或亏损保证。",
        "", "| 研究问题 | 当前可用结论／下一项 |", "| --- | --- |",
        "| 能持有多久 | NOT_ESTIMATED：须验证论点持续性、估值、资金需求和不同持有窗口 |",
        "| 何时考虑退出 | 基本面论点失效尚未评估；技术偏弱或冲突仅要求复核，不是卖出指令 |",
        "| 何时考虑补仓 | 尚缺合格财务、方法验证、现金与集中度复核；不因下跌或成本下降自动补仓 |",
        "| 实操技术 | 保留上文MACD/KDJ、趋势、三线、格兰维尔及可选海龟观测，不增加重复投票 |",
        "| 基本面 | 上文原生变化不等于最新季度核验；需明确论点、反论点及可证伪失效条件 |",
        "没有生成持有／买入／补仓／卖出信号，没有估计最优持有年限，没有执行授权。",
        f"持仓复核版本：{HOLDING_REVIEW_VERSION}；内容标识：{_cell(review['review_hash'])}。"]
    if "PRICE_PREDATES_HOLDING_OBSERVATION" in review["blockers"]:
        rows.append("特别提醒：日线早于持仓观察时间，不能用于计算买入后的收益或当前持仓止损。")
    return rows
