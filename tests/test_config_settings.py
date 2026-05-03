from pathlib import Path

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


def test_explicit_default_profile_overrides_config_to_conservative(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADING_LAB_PROFILE", "default")
    monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)
    path = tmp_path / "trading.yaml"
    path.write_text(
        """
modeling:
  use_experiment_selected_target: true
""",
        encoding="utf-8",
    )

    cfg = load_trading_config(path)

    assert cfg.active_profile == "default"
    assert cfg.use_experiment_selected_target is False


def test_default_profile_keeps_experiment_selected_false(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADING_LAB_PROFILE", raising=False)
    monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)

    cfg = load_trading_config(tmp_path / "missing.yaml")

    assert cfg.active_profile == "default"
    assert cfg.use_experiment_selected_target is False


def test_research_profile_enables_experiment_selected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADING_LAB_PROFILE", "research")
    monkeypatch.delenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", raising=False)

    cfg = load_trading_config(tmp_path / "missing.yaml")

    assert cfg.active_profile == "research"
    assert cfg.use_experiment_selected_target is True


def test_env_override_can_disable_research_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADING_LAB_PROFILE", "research")
    monkeypatch.setenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", "0")

    cfg = load_trading_config(tmp_path / "missing.yaml")

    assert cfg.active_profile == "research"
    assert cfg.use_experiment_selected_target is False


def test_env_override_can_enable_default_profile(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TRADING_LAB_PROFILE", raising=False)
    monkeypatch.setenv("TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET", "1")

    cfg = load_trading_config(tmp_path / "missing.yaml")

    assert cfg.active_profile == "default"
    assert cfg.use_experiment_selected_target is True
