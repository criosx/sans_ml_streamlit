from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Any

from roadmap_datamanager.configuration import BaseConfig, load_config, save_config
from pse.configuration import DataManagerConfig as PSEConfig

@dataclass
class DataManagerConfig(PSEConfig):
    CONFIG_ENV_VAR: ClassVar[str] = "SANS_APP_CONFIG"
    CONFIG_APP_NAME: ClassVar[str] = "sans_app"
    CONFIG_APP_AUTHOR: ClassVar[str] = "streamlit"
    CONFIG_FILENAME: ClassVar[str] = "config.json"

    # pse setup
    pse_model_name: str = ''
    pse_config_list: list[str] = field(default_factory=list)

    # pse data simulation
    pse_qmin: float = 0.001
    pse_qmax: float = 0.5
    pse_tfix: float = 0

    # pse data fitting
    pse_fitter: str = 'LM'
    pse_mcmcburn: int = 100
    pse_mcmcsteps: int = 100


def load_persistent_cfg() -> DataManagerConfig:
    config_cls = DataManagerConfig
    return load_config(
        config_cls,
        env_var=getattr(config_cls, "CONFIG_ENV_VAR", None),
        app_name=config_cls.CONFIG_APP_NAME,
        app_author=config_cls.CONFIG_APP_AUTHOR,
        filename=getattr(config_cls, "CONFIG_FILENAME", "config.json"),
    )

def save_persistent_cfg(data: Any) -> Path:
    cls = type(data)
    return save_config(
        data,
        env_var=getattr(cls, "CONFIG_ENV_VAR", None),
        app_name=cls.CONFIG_APP_NAME,
        app_author=cls.CONFIG_APP_AUTHOR,
        filename=getattr(cls, "CONFIG_FILENAME", "config.json"),
    )