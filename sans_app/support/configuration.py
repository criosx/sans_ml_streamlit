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
    pse_model_name: str = field(
        default = '',
        metadata={"config_groups": ["pse"]}
    )
    pse_config_list: list[str] = field(
        default_factory=list,
        metadata={"config_groups": ["pse"]}
    )
    pse_parameters_edited_json: dict = field(
        default_factory=dict,
        metadata={"config_groups": ["pse"]}
    )
    # various configurations states as used in 4_Experimental_Optimization
    pse_configs_json: list[dict[str, Any]] = field(
        default_factory=list,
        metadata={"config_groups": ["pse"]}
    )
    pse_configs_edited_json: list[dict[str, Any]] = field(
        default_factory=list,
        metadata={"config_groups": ["pse"]}
    )
    pse_configs_original_json: list[dict[str, Any]] = field(
        default_factory=list,
        metadata={"config_groups": ["pse"]}
    )

    # pse data simulation
    pse_qmin: float = field(
        default=0.001,
        metadata={"config_groups": ["pse"]}
    )
    pse_qmax: float = field(
        default=0.5,
        metadata={"config_groups": ["pse"]}
    )
    pse_tfix: float = field(
        default=0,
        metadata={"config_groups": ["pse"]}
    )

    # pse data fitting
    pse_fitter: str = field(
        default='LM',
        metadata={"config_groups": ["pse"]}
    )
    pse_mcmcburn: int = field(
        default=100,
        metadata={"config_groups": ["pse"]}
    )
    pse_mcmcsteps: int = field(
        default=100,
        metadata={"config_groups": ["pse"]}
    )


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