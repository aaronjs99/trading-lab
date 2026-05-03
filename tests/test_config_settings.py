from pathlib import Path

from trading_lab.config import TradingConfig, load_trading_config


def test_default_trading_config_is_current_tqqq_setup():
    cfg = TradingConfig()

    assert cfg.traded_symbol == "TQQQ"
    assert cfg.benchmark_symbol == "QQQ"
    assert cfg.core_symbol == "SPY"
    assert cfg.inverse_symbol == "SQQQ"
    assert cfg.use_experiment_selected_target is False
    assert cfg.selected_target_mode is None
    assert cfg.selected_target_name is None


def test_load_trading_config_from_yaml(tmp_path: Path):
    path = tmp_path / "trading.yaml"
    path.write_text(
        """
symbols:
  traded: SOXL
  benchmark: SOXX
  core: SPY
  inverse: SOXS
account:
  value: 1234
allocation:
  max_traded_allocation_wait: 0.07
  max_core_allocation_wait: 0.44
modeling:
  use_experiment_selected_target: true
  selected_target_mode: threshold_horizon_return
  selected_target_name: soxl_5d_up5_before_down5_threshold_horizon_return
""",
        encoding="utf-8",
    )

    cfg = load_trading_config(path)

    assert cfg.traded_symbol == "SOXL"
    assert cfg.benchmark_symbol == "SOXX"
    assert cfg.inverse_symbol == "SOXS"
    assert cfg.account_value == 1234
    assert cfg.max_traded_allocation_wait == 0.07
    assert cfg.max_core_allocation_wait == 0.44
    assert cfg.use_experiment_selected_target is True
    assert cfg.selected_target_mode == "threshold_horizon_return"
    assert cfg.selected_target_name == "soxl_5d_up5_before_down5_threshold_horizon_return"
