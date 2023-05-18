import os
from sasmodels.data import load_data
from scattertools.support import molstat
import shutil
import streamlit as st
import subprocess
import threading
import multiprocessing

user_sans_model_dir = st.session_state['user_sans_model_dir']
user_sans_file_dir = st.session_state['user_sans_file_dir']
user_sans_fit_dir = st.session_state['user_sans_fit_dir']


# ---- Functionality --------
@st.cache_data
def load_sans_files(filelist):
    for file in filelist:
        try:
            with open(os.path.join(user_sans_file_dir, file.name), "wb") as f:
                f.write(file.getbuffer())
        except IOError:
            pass


def run_fit(fitdir, runfile, burn, steps):
    # oldir = os.getcwd()
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

    fitobj.fnRestoreFit()
    return fitobj


def save_sans_model(path, name):
    with open(os.path.join(path, name), 'w') as f:
        f.write(st.session_state['sans_model_text'])


# --- GUI ----------------------
st.write("""
# Setup SANS Models
""")

# -------- SANS model loader
model_path = user_sans_model_dir
model_list = os.listdir(model_path)
model_list = [element for element in model_list if '.py' in element]
model_name = st.selectbox("SANS model", model_list)
model_name_stripped = os.path.splitext(model_name)[0]

if model_name:
    with open(os.path.join(model_path, model_name)) as f:
        model_txt = f.readlines()

    txt = st.text_area('Model Script', "".join(model_txt), key='sans_model_text', height=400,
                       on_change=save_sans_model, args=[model_path, model_name])

    st.divider()

st.write('Fit Data')
uploaded_file = st.file_uploader("Upload SANS files specified in your script", accept_multiple_files=True)
if uploaded_file is not None:
    if not isinstance(uploaded_file, list):
        filelist = [uploaded_file]
    load_sans_files(uploaded_file)

col1_1, col1_2 = st.columns([1, 1])
burn = col1_1.number_input('burn', format='%i', step=50, min_value=50, value=100, key='burn')
steps = col1_2.number_input('steps', format='%i', step=50, min_value=50, value=100, key='steps')

if st.button('Run Fit'):
    if model_name is not None and uploaded_file is not None:
        # empty fit directory
        for f in os.listdir(user_sans_fit_dir):
            fpath = os.path.join(user_sans_fit_dir, f)
            if os.path.isfile(fpath):
                os.remove(fpath)
            elif os.path.isdir(fpath):
                shutil.rmtree(fpath)
        # copy script and runfiles into fitdir
        shutil.copyfile(os.path.join(user_sans_model_dir, model_name), os.path.join(user_sans_fit_dir, model_name))
        for file in uploaded_file:
            shutil.copyfile(os.path.join(user_sans_file_dir, file.name), os.path.join(user_sans_fit_dir, file.name))
        # run fit
        st.info("Starting fit ...")
        fitobj = run_fit(user_sans_fit_dir, model_name_stripped, burn, steps)
        results = fitobj.fnAnalyzeStatFile(fConfidence=-1)
        st.write('Results:')
        st.write(results)




