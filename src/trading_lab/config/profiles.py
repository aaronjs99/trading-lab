from __future__ import annotations

import os


PROFILE_ENV = "TRADING_LAB_PROFILE"
TARGET_OVERRIDE_ENV = "TRADING_LAB_USE_EXPERIMENT_SELECTED_TARGET"
DEFAULT_PROFILE = "default"
RESEARCH_PROFILE = "research"


def active_profile(environ: dict[str, str] | None = None) -> str:
    return profile_from_env(environ) or DEFAULT_PROFILE


def profile_from_env(environ: dict[str, str] | None = None) -> str | None:
    env = environ if environ is not None else os.environ
    raw = env.get(PROFILE_ENV)
    if raw is None:
        return None
    profile = raw.strip().lower()
    if profile not in {DEFAULT_PROFILE, RESEARCH_PROFILE}:
        return None
    return profile


def profile_uses_experiment_target(profile: str) -> bool:
    return profile == RESEARCH_PROFILE


def bool_env_override(environ: dict[str, str] | None = None) -> bool | None:
    env = environ if environ is not None else os.environ
    raw = env.get(TARGET_OVERRIDE_ENV)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None
