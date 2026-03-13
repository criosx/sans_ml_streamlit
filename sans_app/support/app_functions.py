from __future__ import annotations

import glob
import os
from PIL import Image
import pandas
from pathlib import Path
from roadmap_datamanager import datamanager
from sasmodels.data import load_data
from scattertools.support import molstat
from scattertools.support import api_sasview
import shutil
import streamlit as st
import subprocess
import tempfile
from typing import Optional, Dict, Any

from sans_app.support import configuration


def get_info_from_runfile(model_name, model_dir, file_dir, fit_dir):
    runfile = os.path.join(model_dir, model_name)
    # extract name of data files from runfile
    datafile_names = api_sasview.extract_data_filenames_from_runfile(runfile=runfile)

    # strip any long path from filename and retain only the basename, write back to file
    datafile_names = [os.path.basename(file) for file in datafile_names]
    api_sasview.write_data_filenames_to_runfile(runfile=runfile, filelist=datafile_names)

    # check if data files are in user folder, if not then create dummy files
    datafile_names_user = [os.path.join(file_dir, os.path.basename(file)) for file in datafile_names]

    molstat.prepare_fit_directory(fitdir=fit_dir, runfile=runfile, datafile_names=datafile_names_user)

    # if datafiles exist in user filedir, use those; otherwise create dummy files
    for filename in datafile_names_user:
        if os.path.isfile(filename):
            shutil.copyfile(filename, os.path.join(fit_dir, os.path.basename(filename)))
        else:
            api_sasview.write_dummy_sans_file(os.path.join(fit_dir, os.path.basename(filename)))

    os.chdir(fit_dir)
    fitobj = molstat.CMolStat(
        fitsource="SASView",
        spath=fit_dir,
        mcmcpath="MCMC",
        runfile=os.path.basename(runfile),
        state=None,
        problem=None,
    )
    df_pars = pandas.DataFrame.from_dict(fitobj.fnLoadParameters())
    li_allpars = list(fitobj.Interactor.problem.model_parameters().keys())

    return df_pars, li_allpars, datafile_names, fitobj


@st.cache_data
def load_SANS_data(uploaded_file, file_save_dir):
    try:
        with open(os.path.join(file_save_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        ds, tb_output, file_name = load_sans_file(uploaded_file.name, file_save_dir)
        if file_name is None:
            uploaded_file = None
    except (IOError, TypeError) as exc:
        ds = None
        tb_output = "Invalid SANS data file. " + str(exc)
        uploaded_file = None
    return ds, tb_output, uploaded_file


@st.cache_data
def load_sans_file(file_name, file_dir):
    try:
        dso = load_data(os.path.join(file_dir, file_name))
        Q = dso.x
        Iq = dso.y
        dI = dso.dy
        dQ = dso.dx
        ds = pandas.DataFrame(
            {'Q': Q,
             'I': Iq,
             'dI': dI,
             'dQ': dQ
             }
        )
        tb_output = ""
    except (IOError, TypeError) as exc:
        ds = None
        tb_output = "Invalid SANS data file. " + str(exc)
        file_name = None

    return ds, tb_output, file_name


@st.cache_data
def load_sans_files(filelist, file_dir):
    for file in filelist:
        try:
            with open(os.path.join(file_dir, file.name), "wb") as f:
                f.write(file.getbuffer())
        except IOError:
            pass


def monitor_jobs(job_dir):
    job_dir = Path(job_dir)
    status_path = job_dir / "status.json"

    if not status_path.is_file():
        status = "idle"
    else:
        status_df = pandas.read_json(status_path)
        status = status_df["status"].values[0]

    latest_mtime = max(
        (p.stat().st_mtime for p in job_dir.rglob("*") if p.is_file()),
        default=job_dir.stat().st_mtime,
    )

    return latest_mtime, status


def run_fit(fitdir=None, runfile=None, datafile_names=None, datafile_names_uploaded=None, file_dir=None, model_dir=None,
            burn=1000, steps=200):
    # save current working directory
    olddir = os.getcwd()

    # check if all data files are in place
    breakflag = False
    for file in datafile_names:
        if file not in datafile_names_uploaded:
            if os.path.isfile(os.path.join(file_dir, file)):
                infostr = 'Data file ' + file + ' not uploaded. Using copy from user file folder.'
                st.info(infostr)
            else:
                errorstr = 'Data file ' + file + ' not uploaded.'
                st.error(errorstr)
                breakflag = True

    if breakflag:
        return

    datafpaths = [os.path.join(file_dir, file) for file in datafile_names]
    molstat.prepare_fit_directory(fitdir=fitdir, runfile=os.path.join(model_dir, runfile), datafile_names=datafpaths)

    st.info("Starting the fit ...")
    runfile = os.path.splitext(runfile)[0]
    os.chdir(fitdir)
    with open('run_fit.py', 'w') as file:
        file.write('from scattertools.support import molstat\n')
        file.write('\n')
        file.write("if __name__ == '__main__':\n")
        file.write('    fitobj = molstat.CMolStat(\n')
        file.write('        fitsource="SASView",\n')
        file.write('        spath="' + fitdir + '",\n')
        file.write('        mcmcpath="MCMC",\n')
        file.write('        runfile="' + runfile + '",\n')
        file.write('        state=None,\n')
        file.write('        problem=None,\n')
        file.write('    )\n')
        file.write('\n')
        file.write('    fitobj.Interactor.fnRunMCMC(' + str(burn) + ', ' + str(steps) + ', batch=False)\n')
        file.write('\n')

    # bumps uses multithreading, which collides with Streamlits requirement to register the thread context
    subprocess.call(['python', 'run_fit.py'])

    fitobj = molstat.CMolStat(
        fitsource="SASView",
        spath=fitdir,
        mcmcpath="MCMC",
        runfile=runfile,
        state=None,
        problem=None,
    )

    st.info("Analyzing the fit ...")
    fitobj.fnRestoreFit()
    results = fitobj.fnAnalyzeStatFile(fConfidence=-1)
    st.write('Results:')
    st.write(results)
    for file in os.listdir("MCMC"):
        if file.endswith(".png"):
            image = Image.open(os.path.join('MCMC', file))
            st.image(image)

    os.chdir(olddir)
    return


def run_optimization(optdir=None, runfile=None, file_dir=None, model_dir=None, burn=1000, steps=200):

    datafile_names = api_sasview.extract_data_filenames_from_runfile(runfile=runfile)
    for file in datafile_names:
        dfile = os.path.join(file_dir, file)
        if not os.path.isfile(dfile):
            infostr = 'Data file ' + file + ' not in user file folder. Please set up complete fit under Models and Fit'
            st.info(infostr)
            return

    datafpaths = [os.path.join(file_dir, file) for file in datafile_names]
    molstat.prepare_fit_directory(fitdir=optdir, runfile=os.path.join(model_dir, runfile), datafile_names=datafpaths)

    # TODO: copy optimization specific files

def setup_app_dirs(
        create_dirs=False,
        copy_examples=False,
        init_datalad=False):
    """
    Sets up directories for app use. Initializes the datamanager.
    :param create_dirs: (bool) whether to create directories if they do not exist
    :param copy_examples: (bool) whether to copy provided examples to user folders
    :param init_datalad: (bool) whether to initialize the DataLad repo in the app dir tree
    :return:
    """
    # check if canonical app working directories exist
    app_dir = Path.home() / "app_data" / "sans_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    st.session_state['app_dir'] = app_dir

    # load config file from disc
    cfg = configuration.load_persistent_cfg()
    st.session_state["cfg"] = cfg

    # default data root based on username
    dataroot_dir = app_dir / cfg.user_name
    st.session_state['dataroot_dir'] = dataroot_dir

    if cfg.project is None or cfg.campaign is None or cfg.experiment is None:
        st.session_state["data_folders_ready"] = False
        return

    exp_root = dataroot_dir / cfg.project / cfg.campaign / cfg.experiment
    if not (exp_root.is_dir() or create_dirs):
        st.session_state["data_folders_ready"] = False
        return

    st.session_state["data_folders_ready"] = True
    dataroot_dir.mkdir(parents=True, exist_ok=True)
    exp_root.mkdir(parents=True, exist_ok=True)

    user_sans_config_dir = exp_root / 'SANS_configurations'
    user_sans_config_dir.mkdir(parents=True, exist_ok=True)
    user_ml_model_dir = exp_root / 'ml_models'
    user_ml_model_dir.mkdir(parents=True, exist_ok=True)
    user_sans_model_dir = exp_root / 'SANS_models'
    user_sans_model_dir.mkdir(parents=True, exist_ok=True)
    user_sans_file_dir = exp_root / 'SANS_files'
    user_sans_file_dir.mkdir(parents=True, exist_ok=True)
    user_sans_fit_dir = exp_root / 'SANS_fit'
    user_sans_fit_dir.mkdir(parents=True, exist_ok=True)
    user_sans_opt_dir = exp_root / 'SANS_experimental_optimization'
    user_sans_opt_dir.mkdir(parents=True, exist_ok=True)


    # save paths to persistent session state
    st.session_state['user_sans_config_dir'] = user_sans_config_dir
    st.session_state['user_sans_model_dir'] = user_sans_model_dir
    st.session_state['user_sans_file_dir'] = user_sans_file_dir
    st.session_state['user_sans_fit_dir'] = user_sans_fit_dir
    st.session_state['user_sans_opt_dir'] = user_sans_opt_dir
    st.session_state['user_ml_model_dir'] = user_ml_model_dir
    if 'user_sans_temp_dir' not in st.session_state:
        st.session_state['user_sans_temp_dir'] = tempfile.mkdtemp()
    if 'example_sans_config_dir' not in st.session_state:
        st.session_state['example_sans_config_dir'] = (
                Path(__file__).parent.parent / 'example_data' / 'example_SANS_configurations')

    if copy_examples:
        # Copy example SANS models into user model directory if not already present.
        # This makes sure that a new user always has a selection of models available.
        example_model_dir = Path(__file__).parent.parent / 'example_data' / "example_SANS_models"
        for src in example_model_dir.iterdir():
            dst = Path(user_sans_model_dir) / src.name
            if src.is_file() and not dst.exists():
                shutil.copyfile(src, dst)

        # For similar reasons, copy one data file to the user directory. This data file is the default for the example models.
        src = Path(__file__).parent.parent / 'example_data' / 'example_SANS_files' / 'data0.dat'
        dst = Path(user_sans_file_dir) / 'data0.dat'
        if not dst.exists():
            shutil.copyfile(src, dst)

        # And do this for configurations
        example_config_dir = Path(__file__).parent.parent / 'example_data' / 'example_SANS_configurations'
        config_files = [f for f in example_config_dir.iterdir()]
        for file in config_files:
            if not os.path.isfile(os.path.join(user_sans_config_dir, file.name)):
                shutil.copyfile(str(file), os.path.join(user_sans_config_dir, file.name))

    # st.session_state['example_sans_config_dir'] = example_config_dir

    if init_datalad:
        dm = datamanager.DataManager(
            root= dataroot_dir,
            user_name = cfg.user_name,
            user_email = cfg.user_email,
            default_project = cfg.project,
            default_campaign = cfg.campaign,
            GIN_url = cfg.GIN_url,
            GIN_repo = cfg.GIN_repo,
            GIN_user = cfg.GIN_user,
            verbose=True
        )
        st.session_state['datamanager'] = dm
    else:
        st.session_state['datamanager'] = None


def ssh_config_block(host_alias: str, hostname: str, username: str) -> str:
    return (
        f"Host {host_alias}\n"
        f"    HostName {hostname}\n"
        f"    User {username}\n"
    )


def ssh_config_path() -> Path:
    # Standard location across macOS, Linux, and most Windows OpenSSH installs
    return Path.home() / ".ssh" / "config"


def ssh_config_has_entry(host_alias: str, hostname: str | None = None, username: str | None = None) -> tuple[bool, str]:
    """
    Checks whether an entry for the host already exists in ~/.ssh/config.
    Returns (found, message).
    """

    config_file = ssh_config_path()

    if not config_file.exists():
        return False, f"SSH config file does not exist yet: {config_file}"

    try:
        text = config_file.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"Could not read SSH config: {exc}"

    lines = text.splitlines()

    current_host = None
    host_blocks = {}

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("host "):
            current_host = stripped.split(maxsplit=1)[1]
            host_blocks[current_host] = []
        elif current_host:
            host_blocks[current_host].append(stripped)

    if host_alias in host_blocks:
        block = "\n".join(host_blocks[host_alias])
        if hostname and f"hostname {hostname}".lower() not in block.lower():
            return True, f"Host '{host_alias}' exists but different from hostname ({hostname})."
        if username and f"user {username}".lower() not in block.lower():
            return True, f"Host '{host_alias}' exists but user differs."
        return True, f"Host '{host_alias}' exists in {config_file}."

    return False, f"No SSH config entry for host '{host_alias}'."

def ssh_default_key_path(hostname: str, username: str) -> Path:
    safe_host = hostname.replace(".", "_").replace("/", "_")
    safe_user = username.replace(".", "_").replace("/", "_")
    return Path.home() / ".ssh" / f"id_ed25519_{safe_user}_{safe_host}"

def ssh_ensure_ssh_dir() -> Path:
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(ssh_dir, 0o700)
    except OSError:
        pass
    return ssh_dir

def ssh_generate_keypair(private_key_path: Path, comment: str = "") -> tuple[bool, str]:
    ssh_ensure_ssh_dir()

    if private_key_path.exists() or private_key_path.with_suffix(".pub").exists():
        return False, f"Key file already exists: {private_key_path}"

    cmd = [
        "ssh-keygen",
        "-t", "ed25519",
        "-f", str(private_key_path),
        "-N", "",
    ]
    if comment:
        cmd.extend(["-C", comment])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        return False, "ssh-keygen was not found on this system."
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        message = stderr if stderr else stdout if stdout else str(exc)
        return False, f"ssh-keygen failed: {message}"

    try:
        os.chmod(private_key_path, 0o600)
    except OSError:
        pass

    output = (result.stdout or "").strip()
    return True, output if output else f"Created SSH key pair at {private_key_path}"

def ssh_test_connection(host_alias: str) -> tuple[bool, str, str]:
    """
    Test SSH connectivity using the configured host alias.
    Returns (success, summary_message, detailed_output).
    """
    cmd = [
        "ssh",
        "-T",
        "-o", "BatchMode=yes",
        host_alias,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return False, "ssh was not found on this system.", ""
    except subprocess.TimeoutExpired:
        return False, f"SSH connection test timed out for host '{host_alias}'.", ""
    except Exception as exc:
        return False, f"SSH connection test failed: {exc}", ""

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    combined = "\n".join(part for part in [stdout, stderr] if part).strip()

    success_markers = [
        "successfully authenticated",
        "welcome to gin",
        "you've successfully authenticated",
    ]
    permission_markers = [
        "shell access is not supported",
        "pty allocation request failed",
    ]

    lowered = combined.lower()
    if any(marker in lowered for marker in success_markers) or any(marker in lowered for marker in permission_markers):
        return True, f"SSH connection to '{host_alias}' appears to work.", combined

    if result.returncode == 0:
        return True, f"SSH connection to '{host_alias}' succeeded.", combined

    return False, f"SSH connection to '{host_alias}' failed.", combined
