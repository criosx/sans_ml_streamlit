import os
from PIL import Image
import pandas
from scattertools.support import molstat
from scattertools.support import api_sasview
import shutil
import streamlit as st
import subprocess

user_sans_model_dir = st.session_state['user_sans_model_dir']
user_sans_file_dir = st.session_state['user_sans_file_dir']
user_sans_fit_dir = st.session_state['user_sans_fit_dir']
user_sans_config_dir = st.session_state['user_sans_config_dir']
user_sans_temp_dir = os.path.join(st.session_state['streamlit_dir'], 'temp')
example_sans_config_dir = st.session_state['example_sans_config_dir']


st.write("""
    # Simulate and Compare
    """)