from contextlib import closing
import pandas
from pathlib import Path
import socket
import streamlit as st
import subprocess
import sys
import tempfile
import uuid

from sans_app.support import configuration

# first initialization
if 'first_initialization' not in st.session_state:
    st.session_state['first_initialization'] = True
    st.session_state["data_folders_ready"] = False
    st.session_state['user_root_dir'] = Path.home() / "app_data"

    st.session_state.cfg = configuration.load_persistent_cfg()
    # initialize some widgets
    # force rerendering of toggle widgets
    st.session_state['rpse_key'] = str(uuid.uuid4())
    st.session_state['ppse_key'] = str(uuid.uuid4())
    st.session_state['update_counter'] = 0
    st.session_state["user_sans_temp_dir"] = tempfile.mkdtemp()

    # get free server port and start PSE server
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))  # Bind to a free port provided by the host.
        port = s.getsockname()[1]  # Return the port number assigned.
    st.session_state['gp_server_port'] = port
    st.session_state['gp_server_process'] = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from scattertools.infotheory.entropy import Entropy_server; "
                "Entropy_server().run(int(sys.argv[1]))"
            ),
            str(port),
        ],
        stdout=None,
        stderr=None,
    )

if st.session_state["data_folders_ready"]:
    df_folders = pandas.DataFrame({
        'User home': [str(st.session_state['user_root_dir'])],
        'Data home': [str(st.session_state.cfg.dm_root)],
        'SANS models': [str(st.session_state['user_sans_model_dir'])],
        'SANS data': [str(st.session_state['user_sans_file_dir'])],
        'SANS instrument configurations': [str(st.session_state['user_sans_config_dir'])],
        'SANS fits': str(st.session_state['user_sans_fit_dir']),
        'SANS experimental optimization': str(st.session_state['user_sans_opt_dir']),
        'ML models': [str(st.session_state['user_ml_model_dir'])]
    })
else:
    df_folders = pandas.DataFrame({
        'User home': [str(st.session_state['user_root_dir'])],
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

if not st.session_state["data_folders_ready"]:
    st.info("Files and Folders not set up. Please visit the File System tab.")
    st.stop()


st.divider()

"""
*Contact: frank.heinrich@nist.gov*
"""
