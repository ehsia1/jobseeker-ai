"""Configuration modules for JobSeeker AI."""

# Re-export settings from the legacy config.py file for backward compatibility
import sys
import importlib.util
from pathlib import Path

# Load the settings from backend/config.py (the file, not this package)
_config_file = Path(__file__).parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("backend_config_settings", _config_file)
_config_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_module)
settings = _config_module.settings
Settings = _config_module.Settings

from backend.config.industry_config import (
    Industry,
    IndustryConfig,
    INDUSTRY_CONFIGS,
    get_industry_config,
    suggest_industry,
    get_industry_job_boards,
    get_all_industries,
    get_industry_for_profession,
)

__all__ = [
    "settings",
    "Settings",
    "Industry",
    "IndustryConfig",
    "INDUSTRY_CONFIGS",
    "get_industry_config",
    "suggest_industry",
    "get_industry_job_boards",
    "get_all_industries",
    "get_industry_for_profession",
]
