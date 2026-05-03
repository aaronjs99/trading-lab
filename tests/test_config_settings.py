from pathlib import Path

import pytest

from trading_lab.config import TradingConfig, load_trading_config


def test_default_trading_config_is_current_tqqq_setup(monkeypatch):
    monkeypatch.delenv("TRADING_LAB_PROFILE", raising=False)
    monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)
    cfg = TradingConfig()

    assert cfg.traded_symbol == "TQQQ"
    assert cfg.benchmark_symbol == "QQQ"
    assert cfg.core_symbol == "SPY"
    assert cfg.inverse_symbol == "SQQQ"
    assert cfg.use_experiment_selected_target is False
    assert cfg.selected_target_mode is None
    assert cfg.selected_target_name is None
    assert cfg.active_profile == "default"


def test_load_trading_config_from_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADING_LAB_PROFILE", raising=False)
    monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)
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


@pytest.mark.parametrize(
    ("profile", "override", "has_config_file", "expected_profile", "expected_use_experiment"),
    [
        ("default", None, True, "default", False),
        (None, None, True, "default", True),
        (None, None, False, "default", False),
        ("research", None, False, "research", True),
        ("research", "0", False, "research", False),
        (None, "1", False, "default", True),
    ],
)
def test_profile_and_env_control_experiment_target_selection(
    tmp_path: Path,
    monkeypatch,
    profile,
    override,
    has_config_file,
    expected_profile,
    expected_use_experiment,
):
    if profile is None:
        monkeypatch.delenv("TRADING_LAB_PROFILE", raising=False)
    else:
        monkeypatch.setenv("TRADING_LAB_PROFILE", profile)
    if override is None:
        monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)
    else:
        monkeypatch.setenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", override)
    path = tmp_path / "trading.yaml"
    if has_config_file:
        path.write_text(
            """
modeling:
  use_experiment_selected_target: true
""",
            encoding="utf-8",
        )

    cfg = load_trading_config(path)

    assert cfg.active_profile == expected_profile
    assert cfg.use_experiment_selected_target is expected_use_experiment
