import os
import streamlit as st

# check if all working directories exist

app_dir = os.path.join(os.path.expanduser('~'), 'app_data')
if not os.path.isdir(app_dir):
    os.mkdir(app_dir)
streamlit_dir = os.path.join(app_dir, 'streamlit_sans_ml')
if not os.path.isdir(streamlit_dir):
    os.mkdir(streamlit_dir)
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

st.session_state['streamlit_dir'] = streamlit_dir
st.session_state['user_sans_model_dir'] = user_sans_model_dir
st.session_state['user_sans_file_dir'] = user_sans_file_dir
st.session_state['user_sans_fit_dir'] = user_sans_fit_dir
st.session_state['user_ml_model_dir'] = user_ml_model_dir


st.write("""
# SANS ML Main

 
""")
st.write('SANS models: ', st.session_state['user_sans_model_dir'])
st.write('SANS files: ', st.session_state['user_sans_file_dir'])
st.write('ML models: ', st.session_state['user_ml_model_dir'])
