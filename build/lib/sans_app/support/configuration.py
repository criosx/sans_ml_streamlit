import json
import os

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

try:
    from platformdirs import user_config_dir
except ImportError:
    user_config_dir = None


@dataclass
class DataConfig:
    # Identity
    user_name: str = 'default'
    user_email: str = ''

    # Optional identity/context
    user_id: Optional[str] = None
    organization: Optional[str] = None
    lab_group: Optional[str] = None

    # Defaults
    project: Optional[str] = None
    campaign: Optional[str] = None
    experiment: Optional[str] = None

    # DataLad behavior
    use_datalad: bool = False
    datalad_profile: Optional[str] = None

    # GIN repository
    use_gin: bool = False
    GIN_url: Optional[str] = None
    GIN_repo: Optional[str] = None
    GIN_user: Optional[str] = None

    # Datamanager root directory (currently disabled as it is derived from app directory and username
    # dm_root: Optional[str] = None


def default_config_path() -> Path:
    # env override
    override = os.getenv("SANS_APP_CONFIG")
    if override:
        return Path(override).expanduser()
    if user_config_dir:
        return Path(user_config_dir("sans_app", "streamlit")) / "config.json"
    # fallback
    return Path.home() / ".sans_app_config" / "config.json"


def load_persistent_cfg() -> DataConfig:
    """Load config from disk and return a DataConfig instance.

    If no config file exists (or it cannot be parsed), returns a default DataConfig.
    Unknown keys in the JSON are ignored to allow schema evolution.
    """
    cfg_path = default_config_path()
    if not cfg_path.exists():
        return DataConfig()

    try:
        raw = json.loads(cfg_path.read_text())
    except (json.JSONDecodeError, OSError, NotADirectoryError):
        return DataConfig()

    if not isinstance(raw, dict):
        return DataConfig()

    valid_keys = {f.name for f in fields(DataConfig)}
    filtered = {k: v for k, v in raw.items() if k in valid_keys}
    return DataConfig(**filtered)


def save_persistent_cfg(data: DataConfig | dict) -> None:
    cfg_path = default_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    payload = data
    if isinstance(data, DataConfig):
        payload = {f.name: getattr(data, f.name) for f in fields(DataConfig)}

    cfg_path.write_text(json.dumps(payload, indent=2))
