"""Configuration loading for trading-lab."""

from trading_lab.config.columns import TradingColumns
from trading_lab.config.settings import TradingConfig, load_trading_config
from trading_lab.config.symbols import SymbolPair

__all__ = ["SymbolPair", "TradingColumns", "TradingConfig", "load_trading_config"]

from trading_lab.config.targets import PredictionTarget, default_prediction_targets, default_symbol_pair
