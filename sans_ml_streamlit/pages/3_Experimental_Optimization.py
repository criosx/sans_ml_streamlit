import numpy
import os
import pandas
import plotly.graph_objects as go
from scattertools.support import api_sasview
import shutil
import streamlit as st

import sys
sys.path.append(st.session_state['app_functions_dir'])
import app_functions

user_sans_model_dir = st.session_state['user_sans_model_dir']
user_sans_file_dir = st.session_state['user_sans_file_dir']
user_sans_fit_dir = st.session_state['user_sans_fit_dir']
user_sans_config_dir = st.session_state['user_sans_config_dir']
user_sans_temp_dir = os.path.join(st.session_state['streamlit_dir'], 'temp')
example_sans_config_dir = st.session_state['example_sans_config_dir']


# ------------ Functionality -----------


# ------------  GUI -------------------
file_path = user_sans_file_dir
file_list = os.listdir(file_path)
file_list = sorted(element for element in file_list if element[0] != '.')

model_path = user_sans_model_dir
model_list = os.listdir(model_path)
model_list = sorted([element for element in model_list if '.py' in element])

configfile_names = None
config_path = user_sans_config_dir
config_list = os.listdir(config_path)
config_list = sorted([element for element in config_list if '.json' in element])

st.write("""
# Select SANS Model
""")
model_name = st.selectbox("Select from user directory", model_list, key='opt_sans_model_selectbox')

df_pars = None
if model_name is not None:
    df_pars, li_all_pars, datafile_names, model_fitobj = \
        app_functions.get_info_from_runfile(model_name, user_sans_model_dir, user_sans_file_dir, user_sans_fit_dir)
    df_pars = df_pars.drop(index=['number', 'relval', 'variable', 'error'])
    df_pars = df_pars.transpose()

st.write("""
# Select Instrument Configurations
""")
config_list_select = st.multiselect("Select from user directory", config_list, key='opt_config_selectbox')
if config_list_select is not None:
    if not isinstance(config_list, list):
        config_list_select = [config_list_select]
    df_config = []
    for config_name in config_list_select:
        df_config.append(pandas.read_json(os.path.join(config_path, config_name), orient='record'))

st.write("""
# Optimization Setup
### Model Fit Parameters
""")

parameters_edited = st.experimental_data_editor(df_pars)


st.write("""
### Configuration Parameters
""")

col_opt1, col_opt2 = st.columns([1, 1])
qmin = col_opt1.number_input('q_min', min_value=0.0001, max_value=0.8, value=0.001, format='%.4f', key='opt_qmin')
qmax = col_opt2.number_input('q_max', min_value=0.0001, max_value=0.8, value=0.8, key='opt_qmax')





