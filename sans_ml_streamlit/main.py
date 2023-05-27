import os
import pandas
from pathlib import Path
import shutil
import streamlit as st

# check if all working directories exist
app_dir = os.path.join(os.path.expanduser('~'), 'app_data')
if not os.path.isdir(app_dir):
    os.mkdir(app_dir)

streamlit_dir = os.path.join(app_dir, 'streamlit_sans_ml')
if not os.path.isdir(streamlit_dir):
    os.mkdir(streamlit_dir)

user_sans_config_dir = os.path.join(streamlit_dir, 'SANS_configurations')
if not os.path.isdir(user_sans_config_dir):
    os.mkdir(user_sans_config_dir)

user_ml_model_dir = os.path.join(streamlit_dir, 'ml_models')
if not os.path.isdir(user_ml_model_dir):
    os.mkdir(user_ml_model_dir)

user_sans_model_dir = os.path.join(streamlit_dir, 'SANS_models')
if not os.path.isdir(user_sans_model_dir):
    os.mkdir(user_sans_model_dir)

user_sans_file_dir = os.path.join(streamlit_dir, 'SANS_files')
if not os.path.isdir(user_sans_file_dir):
    os.mkdir(user_sans_file_dir)

user_sans_fit_dir = os.path.join(streamlit_dir, 'SANS_fit')
if not os.path.isdir(user_sans_fit_dir):
    os.mkdir(user_sans_fit_dir)

temp_dir = os.path.join(streamlit_dir, 'temp')
if not os.path.isdir(temp_dir):
    os.mkdir(temp_dir)

# Copy example SANS models into user model directory if not already present.
# This makes sure that a new user always has a selection of models available.
example_model_dir = os.path.join(str(Path(__file__).parent.parent), 'example_SANS_models')
model_files = [f for f in os.listdir(example_model_dir) if os.path.isfile(os.path.join(example_model_dir, f))]
for file in model_files:
    if not os.path.isfile(os.path.join(user_sans_model_dir, file)):
        shutil.copyfile(os.path.join(example_model_dir, file), os.path.join(user_sans_model_dir, file))

# For similar reasons, copy one data file to the user directory. This data file is the default for the example models.
example_file_dir = os.path.join(str(Path(__file__).parent.parent), 'example_SANS_files')
if not os.path.isfile(os.path.join(user_sans_file_dir, 'data0.dat')):
    shutil.copyfile(os.path.join(example_file_dir, 'data0.dat'), os.path.join(user_sans_file_dir, 'data0.dat'))

# And do this for configurations
example_config_dir = os.path.join(str(Path(__file__).parent.parent), 'example_SANS_configurations')
if not os.path.isfile(os.path.join(user_sans_config_dir, 'pinhole.json')):
    shutil.copyfile(os.path.join(example_config_dir, 'pinhole.json'), os.path.join(user_sans_config_dir,
                                                                                   'pinhole.json'))

# save paths to persistent session state
st.session_state['streamlit_dir'] = streamlit_dir
st.session_state['user_sans_config_dir'] = user_sans_config_dir
st.session_state['user_sans_model_dir'] = user_sans_model_dir
st.session_state['user_sans_file_dir'] = user_sans_file_dir
st.session_state['user_sans_fit_dir'] = user_sans_fit_dir
st.session_state['user_ml_model_dir'] = user_ml_model_dir
st.session_state['example_sans_config_dir'] = example_config_dir

df_folders = pandas.DataFrame({
    'App home': [st.session_state['streamlit_dir']],
    'SANS models': [st.session_state['user_sans_model_dir']],
    'SANS data': [st.session_state['user_sans_file_dir']],
    'SANS instrument configurations': [st.session_state['user_sans_config_dir']],
    'SANS fits': st.session_state['user_sans_fit_dir'],
    'ML models': [st.session_state['user_ml_model_dir']]
})

df_folders = df_folders.T
df_folders.columns = ['folder']

st.write("""
# SANS App
## How it works
Welcome to the SANS App. On the left, you can choose between modules, each providing a different SANS computing 
service. Data and models modified with either module are available to the others via the shared app file system.

*Note: This app's current and future functionality is already available via Python modules and Jupyter notebooks at 
https://github.com/criosx/scattertools.*

### Models and Fit
This module provides a model uploader and editor, as well as a fitting interface to test them out. It is also suited 
for initial data analysis during the beam time, for example.

### Data Simulation
(in development)

Here, data can be simulated using any model set up in the previous module. A configuration editor allows to simulate 
data for a particular SANS instrument. Comparisons between differently simulated data allow testing of the sensitivity 
of a specific experiment as required in a beam time proposal. Instrument configurations and simulated data are 
prerequisites for the Experimental Optimization and Machine Learning Training modules.  

### Experimental Optimization
(in development)

This module allows finding the optimal instrument and sample configuration given a set of parameters of interest. 
Optimization examples are scattering contrast, counting time, neutron wavelength, sample-detector distances, number of 
instrument configurations and more.

### Machine Learning Training
(in development)

Here, an ML model can be trained using a set of SANS models from the first module and simulated data from the second. 
This approach allows for generating a task-specific ML model that can be deployed within and outside this app. The ML models 
provide classification and regression prediction for a SANS data set.

### Machine Learning Prediction

This module provides an interface for ML prediction using an ML model trained in the previous module.


## The App File System
Like a mobile App, the SANS App has a limited file system. All data are stored in the following folders:

""")

df_folders

st.divider()

"""
*Contact: frank.heinrich@nist.gov*
"""
