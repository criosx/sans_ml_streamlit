from pathlib import Path
import shutil

import streamlit as st

from roadmap_datamanager.gui import streamlit_components as stc
from sans_app.support import configuration

def copy_examples_to_storage():
    """
    Copies the provided examples into the below-experiment storage folders.
    :return: no return value
    """
    cfg = st.session_state.cfg
    exp_root = Path(cfg.dm_root).expanduser().resolve() / cfg.project / cfg.campaign / cfg.experiment
    user_sans_config_dir = exp_root / 'SANS_configurations'
    user_sans_model_dir = exp_root / 'SANS_models'
    user_sans_file_dir = exp_root / 'SANS_files'

    example_model_dir = Path(__file__).parent.parent / 'example_data' / "example_SANS_models"
    for src in example_model_dir.iterdir():
        dst = Path(user_sans_model_dir) / src.name
        if src.is_file() and not dst.exists():
            shutil.copyfile(src, dst)

    # For similar reasons, copy one data file to the user directory. This data file is the default for the example
    # models.
    src = Path(__file__).parent.parent / 'example_data' / 'example_SANS_files' / 'data0.dat'
    dst = Path(user_sans_file_dir) / 'data0.dat'
    if not dst.exists():
        shutil.copyfile(src, dst)

    # And do this for configurations
    example_config_dir = Path(__file__).parent.parent / 'example_data' / 'example_SANS_configurations'
    config_files = [f for f in example_config_dir.iterdir()]
    for file in config_files:
        if not (user_sans_config_dir / file.name).exists():
            shutil.copyfile(str(file), (user_sans_config_dir / file.name))

cfg = st.session_state.cfg

# ----------------------- User dialog --------------------------------------
cfg= stc.UI_fragment_user(
    cfg=cfg,
    user_root_dir=st.session_state.user_root_dir,
    enable_user_selection=True
)
st.session_state.cfg = cfg
configuration.save_persistent_cfg(st.session_state.cfg)

dm_root = st.session_state.cfg.dm_root
if dm_root is None or not dm_root.is_dir():
    st.stop()


# ------------------ Project/Campaign/Experiment Diaolog -------------------
cfg, st.session_state.data_folders_ready, rerun = stc.UI_fragment_PCE(cfg)
st.session_state.cfg = cfg
configuration.save_persistent_cfg(st.session_state.cfg)
if rerun:
    st.rerun()
if not st.session_state.data_folders_ready:
    st.stop()

# -------------------- Storage Directory --------------------------------------
cfg, rerun = stc.UI_fragment_app_storage(
    cfg=cfg,
    storage_folders=['SANS_configurations', 'ml_models', 'SANS_models', 'SANS_files', 'SANS_fit',
                     'SANS_experimental_optimization'],
    gitignore_folders=['SANS_fit'],
    special_action=copy_examples_to_storage,
    special_action_arguments=None,
    special_action_label='Copy examples into storage folders.',
    special_action_enabled=True
)
st.session_state.cfg = cfg
configuration.save_persistent_cfg(st.session_state.cfg)
cfg = st.session_state.cfg
exp_root = Path(cfg.dm_root).expanduser().resolve() / cfg.project / cfg.campaign / cfg.experiment
st.session_state["user_sans_config_dir"] = exp_root / 'SANS_configurations'
st.session_state["user_ml_model_dir"] = exp_root / 'ml_models'
st.session_state["user_sans_model_dir"] = exp_root / 'SANS_models'
st.session_state["user_sans_file_dir"] = exp_root / 'SANS_files'
st.session_state["user_sans_fit_dir"] = exp_root / 'SANS_fit'
st.session_state["user_sans_opt_dir"] = exp_root / 'SANS_experimental_optimization'
if rerun:
    st.rerun()

# --------------------- Datalad UI fragment --------------------------
cfg, dm = stc.UI_fragment_datalad(
    cfg=st.session_state.cfg
)
st.session_state.cfg = cfg
st.session_state.datamanager = dm
configuration.save_persistent_cfg(st.session_state.cfg)
if not st.session_state.cfg.use_datalad or dm is None:
    st.stop()

# ---------------------- GIN remote storage ----------------------------
cfg, rerun = stc.UI_fragment_GIN_actions(st.session_state.cfg, st.session_state.datamanager)
st.session_state.cfg = cfg
configuration.save_persistent_cfg(st.session_state.cfg)
if rerun:
    st.rerun()
