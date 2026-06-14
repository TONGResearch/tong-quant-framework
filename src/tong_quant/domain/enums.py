from enum import StrEnum


class Market(StrEnum):
    CHINA_A = "china_a"
    US = "us"
    HONG_KONG = "hong_kong"
    MALAYSIA = "malaysia"


class AssetType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"


class Adjustment(StrEnum):
    NONE = "none"
    FORWARD = "forward"
    BACKWARD = "backward"


class SignalAction(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    WATCH = "watch"
    RESEARCH = "research"
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"
    HOLD = "hold"
    BLOCK = "block"


class SignalStage(StrEnum):
    DISCOVERY = "discovery"
    SCREENING = "screening"
    RESEARCH = "research"
    STRATEGY = "strategy"
    MARKET_REGIME = "market_regime"
    RISK = "risk"
    AI = "ai"


class Regime(StrEnum):
    BULL = "bull"
    SIDEWAYS = "sideways"
    BEAR = "bear"


class ExecutionMode(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    SEMI_AUTOMATIC = "semi_automatic"
    AUTOMATIC = "automatic"
