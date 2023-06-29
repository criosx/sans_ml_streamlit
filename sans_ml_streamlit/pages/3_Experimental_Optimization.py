import numpy
import copy
import os
import pandas
import plotly.graph_objects as go
from scattertools.support import api_sasview
import shutil
import streamlit as st
import time

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
def delete_config_data_editor_keys():
    if 'df_opt_config_key' in st.session_state:
        del st.session_state['df_opt_config_key']

@st.cache_data
def update_df_config(config_list_select):
    df_config = []
    if config_list_select is not None:
        if not isinstance(config_list, list):
            config_list_select = [config_list_select]
        for config_name in config_list_select:
            df_config.append(pandas.read_json(os.path.join(config_path, config_name), orient='record'))

    for i, config in enumerate(df_config):
        if len(df_config) > 1:
            df_config[i]['shared'] = False
        df_config[i]['lower_opt'] = 0.0
        df_config[i]['upper_opt'] = 1.0
        df_config[i]['optimize'] = False
    st.session_state['df_opt_config_default'] = df_config
    st.session_state['df_opt_config_updated'] = df_config
    st.session_state['df_opt_config_associated']=[]
    for _ in range(len(df_config)):
        st.session_state['df_opt_config_associated'].append(None)

    if 'df_opt_config_key' not in st.session_state:
        st.session_state['df_opt_config_key'] = []
        for _ in range(len(df_config)):
            st.session_state['df_opt_config_key'].append(str(time.time()))

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
config_list_select = st.multiselect(
    "Select from user directory",
    config_list,
    key='opt_config_selectbox',
    on_change=delete_config_data_editor_keys
)
update_df_config(config_list_select)

st.write("""
# Optimization Setup
### Model Fit Parameters
""")

df_pars['relative'] = False
df_pars['lower_opt'] = 0.0
df_pars['upper_opt'] = 1.0
df_pars['optimize'] = False
parameters_edited = st.data_editor(
    df_pars,
    key='opt_pars',
    disabled=["_index"],
    column_order=["value", "lowerlimit", "upperlimit", "relative", "lower_opt", "upper_opt", "optimize"],
    column_config={
        'lowerlimit': "lower fit",
        'upperlimit': "upper",
        'relative': 'relative',
        'lower_opt': 'lower opt',
        'upper_opt': 'upper',
        'optimize': 'optimize'
    }
)

st.write("""
### Configuration Parameters
""")

if config_list_select:
    tablist = st.tabs(config_list_select)
    for i, config in enumerate(st.session_state['df_opt_config_default']):
        with tablist[i]:
            if i > 0:
                # Shared is disabled except for the first configuration. This is not a limitation as any shared
                # setting must be present in all configurations.
                disabled = ["_index", "setting", "shared"]
            else:
                # settings can be shared in the first configuration
                disabled = ["_index", "setting"]

            # The key argument has a variable string from session state that is used to reset the data editor upon
            # changing it. Otherwise, this is the typical approach to avoid the every-other-update works only problem
            if st.session_state['df_opt_config_associated'][i] is None:
                df_temp = st.session_state['df_opt_config_default'][i]
                st.session_state['df_opt_config_associated'][i] = st.data_editor(
                    df_temp,
                    key='opt_configs_' + str(i) + '_' + st.session_state['df_opt_config_key'][i],
                    hide_index=True,
                    use_container_width=True,
                    disabled=disabled,
                    column_config={
                        'lower_opt': 'lower opt',
                        'upper_opt': 'upper',
                        'optimize': 'optimize'
                    }
                )
                df_config_edited = st.session_state['df_opt_config_associated'][i]
            else:
                df_config_edited = st.data_editor(
                    st.session_state['df_opt_config_associated'][i],
                    key='opt_configs_' + str(i) + '_' + st.session_state['df_opt_config_key'][i],
                    hide_index=True,
                    use_container_width=True,
                    disabled=disabled,
                    column_config={
                        'lower_opt': 'lower opt',
                        'upper_opt': 'upper',
                        'optimize': 'optimize'
                    }
                )

            st.session_state['df_opt_config_updated'][i] = df_config_edited

            if i == 0:
                if len(st.session_state['df_opt_config_updated']) > 1:
                    for j in range(1, len(st.session_state['df_opt_config_updated'])):
                        # shorthand handles
                        df0 = st.session_state['df_opt_config_updated'][0]
                        dfj = st.session_state['df_opt_config_updated'][j]
                        # modify successive configurations if any setting is shared with first configuration
                        for par in dfj['setting'].values:
                            # It is a given that there is only one setting with a particular name. .iat[0] refers to the
                            # first element in a list of one element. There should be a better way to do this.
                            if df0.loc[df0['setting'] == par, 'shared'].iat[0]:
                                # copy shared settings from first configuration into the current one
                                dfj.loc[dfj['setting'] == par, 'shared'] = True
                                dfj.loc[dfj['setting'] == par, 'optimize'] = \
                                    df0.loc[df0['setting'] == par, 'optimize'].iat[0]
                                dfj.loc[dfj['setting'] == par, 'lower_opt'] = \
                                    df0.loc[df0['setting'] == par, 'lower_opt'].iat[0]
                                dfj.loc[dfj['setting'] == par, 'upper_opt'] = \
                                    df0.loc[df0['setting'] == par, 'upper_opt'].iat[0]
                        st.session_state['df_opt_config_associated'][j] = dfj
                        # change key of data editor associated with that particular data frame
                        st.session_state['df_opt_config_key'] = str(time.time())




st.write("""
### Background Parameters
""")

col_opt1, col_opt2 = st.columns([1, 1])
qmin = col_opt1.number_input('q_min', min_value=0.0001, max_value=0.8, value=0.001, format='%.4f', key='opt_qmin')
qmax = col_opt2.number_input('q_max', min_value=0.0001, max_value=0.8, value=0.8, key='opt_qmax')





