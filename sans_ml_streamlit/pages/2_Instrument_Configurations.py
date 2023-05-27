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


# --- Functionality ------------
def create_non_default_configuration(default, modifier):
    modifier = modifier.strip()
    if modifier == '':
        return default

    if modifier in default:
        st.error('Chose unique extension.')
        return default

    splitpath = os.path.splitext(default)
    config_name = splitpath[0] + '_' + modifier + splitpath[1]
    if not os.path.isfile(os.path.join(user_sans_config_dir, config_name)):
        shutil.copyfile(os.path.join(user_sans_config_dir, default), os.path.join(user_sans_config_dir, config_name))
        st.info('Created new configuration ' + config_name + ' from ' + default + ' .')
    else:
        st.info('Switching to existing configuration ' + config_name + ' .')

    remove_key_exp_data_frame_edit()

    return config_name


@st.cache_data
def load_config(file):
    try:
        with open(os.path.join(user_sans_config_dir, file.name), "wb") as f:
            f.write(file.getbuffer())
        st.session_state['sans_config_selectbox'] = file.name
    except IOError:
        pass


def remove_configuration(name):
    if os.path.isfile(os.path.join(user_sans_config_dir, name)):
        os.remove(os.path.join(user_sans_config_dir, name))
        if os.path.isfile(os.path.join(example_sans_config_dir, name)):
            shutil.copyfile(os.path.join(example_sans_config_dir, name), os.path.join(user_sans_config_dir, name))
            st.info('Replaced configuration ' + name + ' with default.')
        else:
            st.info('Removed configuration ' + name + ' .')

    remove_key_exp_data_frame_edit()


def remove_key_exp_data_frame_edit():
    if 'exp_data_frame_config' in st.session_state:
        del st.session_state.exp_data_frame_config

@st.cache_data
def save_config(df, fname):
    df.to_json(os.path.join(user_sans_config_dir, fname), orient='records')


# --- GUI ----------------------
configfile_names = None

# --- SANS configuration loader-
config_path = user_sans_config_dir
config_list = os.listdir(config_path)
config_list = [element for element in config_list if '.json' in element]

if 'sans_config_selectbox' in st.session_state:
    if st.session_state.sans_config_selectbox not in config_list:
        # it got deleted via the remove button
        st.session_state.sans_config_selectbox = config_list[0]

if 'sans_config_modifier' in st.session_state and 'sans_config_selectbox' in st.session_state:
    config_name = create_non_default_configuration(st.session_state.sans_config_selectbox,
                                                   st.session_state.sans_config_modifier)
    st.session_state.sans_config_selectbox = config_name
    st.session_state.sans_config_modifier = ''

# repeat in case there were changes
config_path = user_sans_config_dir
config_list = os.listdir(config_path)
config_list = [element for element in config_list if '.json' in element]


st.write("""
# Instrument Configurations
""")

col1_a, col1_b, = st.columns([1.2, 1])
config_name = col1_a.selectbox("Select configuration", config_list, key='sans_config_selectbox',
                               on_change=remove_key_exp_data_frame_edit)

btn_remove = col1_a.button("Delete", on_click=remove_configuration, args=[config_name])
name_modifier = col1_b.text_input('Create or switch to copy with extension', '', key='sans_config_modifier')
with open(os.path.join(user_sans_config_dir, config_name), "rb") as file:
    btn = col1_b.download_button(
        label="Download",
        data=file,
        file_name=config_name,
        mime='text/plain'
    )

# This solution does not work, updates only every other time.
# df_config_edited = st.experimental_data_editor(df_config, use_container_width=True)
# Adapted this from: https://discuss.streamlit.io/t/experimental-data-editor/39707/2
# requires to remove key from session_state when changing config to edit

if 'exp_data_frame_config' not in st.session_state:
    df_config = pandas.read_json(os.path.join(config_path, config_name), orient='record')
    st.session_state.exp_data_frame_config = st.experimental_data_editor(df_config, use_container_width=True)
    df_config_edited = st.session_state.exp_data_frame_config
else:
    df_config_edited = st.experimental_data_editor(st.session_state.exp_data_frame_config, use_container_width=True)

save_config(df_config_edited, config_name)

st.divider()

uploaded_config = st.file_uploader("Upload", type=['json'])
if uploaded_config is not None:
    load_config(uploaded_config)

