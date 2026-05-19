from __future__ import annotations

import hashlib
import os
from PIL import Image
import pandas
from pathlib import Path
from sasmodels.data import load_data
from scattertools.support import molstat
from scattertools.support import api_sasview
import shutil
import streamlit as st
import subprocess
from typing import Optional, Dict, Any

from sans_app.support import configuration

def process_runfile(model_name, model_dir, file_dir, fit_dir, force=True,
                    correct_data_paths=False):
    """
    Parses a run script and extracts parameters and data filenames from it. Given a fit_dir, it copies the data files
    and the script file to this directory from model_dir and file_dir, respectively. All other contents from the fit_dir
    are deleted.

    :param model_name: (str) The namem of the model, including file extension.
    :param model_dir: (str or Path-like) The directory of the model.
    :param file_dir: (str or Path-like) The directory of the data files.
    :param fit_dir: (str or Path-like) The directory in which the fit problem will be initialized.
    :param force: (bool) Whether to overwrite existing files in the directory.
    :param correct_data_paths: (bool) Whether to correct data file paths from absolute to relative (SansApp constraint).
    :return: (Pandas dataframe) of all parameters, (list) of all parameter names, (list) of all data filenames,
             (bumps problem) an instance of the fit object
    """

    def _file_hash(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    file_dir = Path(file_dir).expanduser().resolve()
    model_dir = Path(model_dir).expanduser().resolve()
    fit_dir = Path(fit_dir).expanduser().resolve()
    runfile = model_dir / model_name
    runfile_dest = fit_dir / model_name

    # extract name of data files from runfile
    datafile_names = api_sasview.extract_data_filenames_from_runfile(runfile=str(runfile))
    # strip any long path from filename and retain only the basename, write back to file
    datafile_names = [Path(file).name for file in datafile_names]
    datafile_paths = [str(file_dir / Path(file).name) for file in datafile_names]
    # This modifies the original file enforcing a SANS app constraint that the data file and the script are in the same
    # folder
    if correct_data_paths:
        api_sasview.write_data_filenames_to_runfile(runfile=str(runfile), filelist=datafile_names)

    already_prepared = False
    # check if model script has already been copied and is unchanged
    if runfile_dest.is_file() and _file_hash(runfile) == _file_hash(runfile_dest):
        # same for each data file
        for fname in datafile_names:
            if (file_dir / fname).is_file():
                if not (fit_dir / fname).is_file() and _file_hash(file_dir / fname) == _file_hash(fit_dir / fname):
                    break
            # no source data file is o.k., but then a dummy file of the same name should be present
            elif not (fit_dir / fname).is_file():
                break
        already_prepared = True

    if not already_prepared:
        if not force:
            if fit_dir.is_dir() and any(fit_dir.iterdir()):
                st.warning("Optimization folder is not empty. Please archive and clear contents.")
                st.stop()

        molstat.prepare_fit_directory(fitdir=str(fit_dir), runfile=str(runfile), datafile_names=datafile_paths)
        # if datafiles exist in user filedir, use those; otherwise create dummy files
        for filename in datafile_paths:
            if Path(filename).is_file():
                if not (fit_dir / Path(filename).name).is_file():
                    shutil.copyfile(filename, fit_dir / Path(filename).name)
            else:
                api_sasview.write_dummy_sans_file(str(fit_dir / Path(filename).name))

    # change of cwd is necessary since many fit setup scripts use relative filepaths
    os.chdir(fit_dir)
    fitobj = molstat.CMolStat(
        fitsource="SASView",
        spath=fit_dir,
        mcmcpath="MCMC",
        runfile=runfile.name,
        state=None,
        problem=None,
    )
    df_pars = pandas.DataFrame.from_dict(fitobj.fnLoadParameters())
    li_allpars = fitobj.fnGetAllParameterNames(model=0)

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
