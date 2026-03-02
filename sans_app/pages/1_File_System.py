import json
import subprocess
import platform
from pathlib import Path

import streamlit as st
from sans_app.support import configuration
from sans_app.support import app_functions

def open_in_file_browser(path: Path):
    if not path.exists():
        return

    system = platform.system()

    if system == "Darwin":        # macOS
        subprocess.run(["open", path])
    elif system == "Windows":
        subprocess.run(["explorer", path])
    elif system == "Linux":
        subprocess.run(["xdg-open", path])

def file_browser_button(path: Path, label="↗️"):
    if path.exists():
        if st.button(label, help=f"Open {path}"):
            open_in_file_browser(path)

cfg = st.session_state.cfg

st.write("""
# File System
## User
         """)

user_list = []
default_user = None
root = st.session_state.app_dir
if root.is_dir():
    user_list = [p.name for p in root.iterdir() if p.is_dir()]
    user_list.sort()
if st.session_state.cfg.user_name is not None:
    if st.session_state.cfg.user_name not in user_list:
        user_list.append(st.session_state.cfg.user_name)
        user_list.sort()
    default_user = user_list.index(st.session_state.cfg.user_name)
user = st.selectbox(
    "User Name",
    options=user_list,
    index=default_user,
    placeholder='Create or select a user.',
    accept_new_options=True)
if user and user != st.session_state.cfg.user_name:
    st.session_state.cfg.user_name = user
    st.session_state.cfg.project = None
    st.session_state.cfg.campaign = None
    st.session_state.cfg.experiment = None
    configuration.save_persistent_cfg(st.session_state.cfg)
if st.session_state.cfg.user_name is None:
    st.stop()

st.session_state.dataroot_dir = st.session_state.app_dir / cfg.user_name

col1, col2, col3 = st.columns([6, 1, 3])
info_text = "Data root directory " + str(st.session_state.dataroot_dir)
if st.session_state.dataroot_dir.is_dir():
    info_text += " exists."
    with col1:
        st.text(info_text)
    with col2:
        file_browser_button(st.session_state.dataroot_dir)
else:
    info_text += " has not been created, yet."
    with col1:
        st.text(info_text)
    with col3:
        if st.button("Create Data Root Directory", type='primary'):
            st.session_state.dataroot_dir.mkdir(parents=True, exist_ok=True)
            st.rerun()


st.write("""
## Project / Campaign / Experiment
""")

project_list = []
default_project = None
root = st.session_state.dataroot_dir
if root.is_dir():
    project_list = [p.name for p in root.iterdir() if p.is_dir()]
    project_list.sort()
if st.session_state.cfg.project is not None:
    if st.session_state.cfg.project not in project_list:
        project_list.append(st.session_state.cfg.project)
        project_list.sort()
    default_project = project_list.index(st.session_state.cfg.project)
project = st.selectbox(
    "Project Name",
    options=project_list,
    index=default_project,
    placeholder='Create or select a project.',
    accept_new_options=True)
if project and project != st.session_state.cfg.project:
    st.session_state.cfg.project = project
    configuration.save_persistent_cfg(st.session_state.cfg)
if st.session_state.cfg.project is None:
    st.stop()

campaign_list = []
default_campaign = None
root = st.session_state.dataroot_dir / st.session_state.cfg.project
if root.is_dir():
    campaign_list = [p.name for p in root.iterdir() if p.is_dir()]
    campaign_list.sort()
if st.session_state.cfg.campaign is not None:
    if st.session_state.cfg.campaign not in campaign_list:
        campaign_list.append(st.session_state.cfg.campaign)
        campaign_list.sort()
    default_campaign = campaign_list.index(st.session_state.cfg.campaign)
campaign = st.selectbox(
    "Campaign Name",
    options=campaign_list,
    index=default_campaign,
    placeholder='Create or select a campaign.',
    accept_new_options=True)
if campaign and campaign != st.session_state.cfg.campaign:
    st.session_state.cfg.campaign = campaign
    configuration.save_persistent_cfg(st.session_state.cfg)
if st.session_state.cfg.campaign is None:
    st.stop()

experiment_list = []
default_experiment = None
root = st.session_state.dataroot_dir / st.session_state.cfg.project / st.session_state.cfg.campaign
if root.is_dir():
    experiment_list = [p.name for p in root.iterdir() if p.is_dir()]
    experiment_list.sort()
if st.session_state.cfg.experiment is not None:
    if st.session_state.cfg.experiment not in experiment_list:
        experiment_list.append(st.session_state.cfg.experiment)
        experiment_list.sort()
    default_experiment = experiment_list.index(st.session_state.cfg.experiment)
experiment = st.selectbox(
    "Experiment Name",
    options=experiment_list,
    index=default_experiment,
    placeholder='Create or select an experiment.',
    accept_new_options=True)
if experiment and experiment != st.session_state.cfg.experiment:
    st.session_state.cfg.experiment = experiment
    configuration.save_persistent_cfg(st.session_state.cfg)
if st.session_state.cfg.experiment is None:
    st.stop()

col4, col5, col6 = st.columns([6, 1, 3])
exp_dir = root / st.session_state.cfg.experiment
info_text = "Experiment directory " + str(exp_dir)
if exp_dir.is_dir():
    info_text += " exists."
    with col4:
        st.text(info_text)
    with col5:
        file_browser_button(exp_dir)
    with col6:
        if st.button("Copy Examples into Experiment Directory"):
            app_functions.setup_app_dirs(create_dirs=True, copy_examples=True)
else:
    info_text += " has not been created, yet."
    with col4:
        st.text(info_text)
    with col6:
        if st.button("Create Experimental Directory", type='primary'):
            # exp_dir.mkdir(parents=True, exist_ok=True)
            app_functions.setup_app_dirs(create_dirs=True)
            st.rerun()
    st.stop()

st.write("""
## DataLad
""")

use_datalad = st.toggle(label='Use DataLad', value=st.session_state.cfg.use_datalad)
if use_datalad != st.session_state.cfg.use_datalad:
    st.info(use_datalad)
    st.session_state.cfg.use_datalad = use_datalad
    st.info(st.session_state.cfg)
    configuration.save_persistent_cfg(st.session_state.cfg)

if not st.session_state.cfg.use_datalad:
    st.stop()

app_functions.setup_app_dirs(create_dirs=False, copy_examples=False, init_datalad=True)
dm = st.session_state.datamanager

root_dir = st.session_state.dataroot_dir
project_dir = root_dir / st.session_state.cfg.project
campaign_dir = project_dir / st.session_state.cfg.campaign
exp_dir = campaign_dir / st.session_state.cfg.experiment

_, r_installed, r_status = st.session_state.datamanager.get_status(dataset=root_dir, recursive=False)
_, p_installed, p_status = st.session_state.datamanager.get_status(dataset=project_dir, recursive=False)
_, c_installed, c_status = st.session_state.datamanager.get_status(dataset=campaign_dir, recursive=False)
_, e_installed, e_status = st.session_state.datamanager.get_status(dataset=exp_dir, recursive=False)
ds_installed = r_installed and p_installed and c_installed and e_installed


#all dirs exists at this point in the script as checked above
col5, col6 = st.columns([7, 3])
if not ds_installed:
    with col5:
        st.info('DataLad branch (project / campaign / experiment) is not (fully) initialized.')
    with col6:
        if st.button("Initialize DataLad Tree.", type='primary'):
            # ensure that data structure is a datalad tree
            dm.init_tree(project=cfg.project, campaign=cfg.campaign, experiment=cfg.experiment, force=True)
            st.rerun()
    st.stop()
else:
    # st.info(e_status)
    status = r_status + p_status + c_status + e_status
    clean = True
    for element in status:
        if element['state'] != 'clean':
            clean = False
    if clean:
        with col5:
            st.text('DataLad branch (project / campaign / experiment) is saved (clean).')
    else:
        with col5:
            st.info('DataLad branch (project / campaign / experiment) has unsaved changes.')
        with col6:
            if st.button("Save DataLad Branch.", type='primary'):
                dm.save(path=exp_dir, recursive=True)
                dm.save(path=campaign_dir, recursive=False)
                dm.save(path=project_dir, recursive=False)
                dm.save(path=root_dir, recursive=False)
                st.rerun()
        st.stop()

with st.expander(label='Detailed Status', expanded=False):
    only_non_clean = st.toggle(label='Show only non-clean entries.', value=True)
    if only_non_clean:
        status = [element for element in status if element['state']!='clean']
    # Pretty-print the combined DataLad status (list of dicts) as JSON.
    st.text(json.dumps(status, indent=2, sort_keys=True, default=str))


st.write("""
## GIN Remote Storage
""")