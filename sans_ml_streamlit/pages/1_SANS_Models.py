import os
from PIL import Image
import pandas
from sasmodels.data import load_data
from scattertools.support import molstat
from scattertools.support import api_sasview
import shutil
import streamlit as st
import subprocess

user_sans_model_dir = st.session_state['user_sans_model_dir']
user_sans_file_dir = st.session_state['user_sans_file_dir']
user_sans_fit_dir = st.session_state['user_sans_fit_dir']


# ---- Functionality --------
def get_info_from_runfile(model_name):

    fitdir = os.path.join(st.session_state['streamlit_dir'], 'temp')
    runfile = os.path.join(user_sans_model_dir, model_name)
    # extract name of data files from runfile
    datafile_names = api_sasview.extract_data_filenames_from_runfile(runfile=runfile)
    # determine, which parameters are fittable
    # fit_row = api_sasview.extract_parameters_from_runfile(runfile=runfile)

    # strip any long path from filename and retain only the basename, write back to file
    datafile_names = [os.path.basename(file) for file in datafile_names]
    api_sasview.write_data_filenames_to_runfile(runfile=runfile, filelist=datafile_names)

    # check if data files are in user folder, if not then create dummy files
    datafile_names_user = [os.path.join(user_sans_file_dir, os.path.basename(file)) for file in datafile_names]

    molstat.prepare_fit_directory(fitdir=fitdir, runfile=runfile, datafile_names=datafile_names_user)

    # if datafiles exist in user filedir, use those; otherwise create dummy files
    for filename in datafile_names_user:
        if os.path.isfile(filename):
            shutil.copyfile(filename, os.path.join(fitdir, os.path.basename(filename)))
        else:
            dummyfile = ['Q I dI dQ\n']
            for i in range(100):
                dummyfile.append(str(float(i)*0.005) + ' ' + str(1.0 - float(i)*0.005) + ' 0.001 0.001\n')
            dummyfile.append('\n')
            file = open(os.path.join(fitdir, os.path.basename(filename)), 'w')
            file.writelines(dummyfile)
            file.close()

    olddir = os.getcwd()
    os.chdir(fitdir)

    fitobj = molstat.CMolStat(
        fitsource="SASView",
        spath=fitdir,
        mcmcpath="MCMC",
        runfile=os.path.basename(runfile),
        state=None,
        problem=None,
    )

    df = pandas.DataFrame.from_dict(fitobj.fnLoadParameters())
    df = df.drop(index=['number', 'relval', 'variable', 'error'])
    df.loc['fit'] = fit_row
    os.chdir(olddir)
    return df, datafile_names


@st.cache_data
def load_sans_files(filelist):
    for file in filelist:
        try:
            with open(os.path.join(user_sans_file_dir, file.name), "wb") as f:
                f.write(file.getbuffer())
        except IOError:
            pass


def run_fit(fitdir=None, runfile=None, datafile_names=None, burn=1000, steps=200):
    # save current working directory
    olddir = os.getcwd()
    molstat.prepare_fit_directory(fitdir=fitdir, runfile=os.path.join(user_sans_model_dir, runfile),
                                  datafile_names=datafile_names)

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

if model_name:
    with open(os.path.join(model_path, model_name)) as f:
        model_txt = f.readlines()

    with st.expander("Model Script"):
        txt = st.text_area('Model Script', "".join(model_txt), key='sans_model_text', height=400,
                           on_change=save_sans_model, args=[model_path, model_name], label_visibility='collapsed')

    parameters, datafile_names = get_info_from_runfile(model_name)

    parameters_edited = st.experimental_data_editor(parameters)
    # TODO implement back-propagation to script

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
        datafile_names = [os.path.join(user_sans_file_dir, file.name) for file in uploaded_file]
        run_fit(fitdir=user_sans_fit_dir, runfile=model_name, datafile_names=datafile_names, burn=burn, steps=steps)





