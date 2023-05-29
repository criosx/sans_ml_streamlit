import os
from PIL import Image
import pandas
import plotly.graph_objects as go
from sasmodels.data import load_data
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


# ------------ Functionality -----------
@st.cache_data
def load_SANS_data(uploaded_file):
    try:
        with open(os.path.join(user_sans_file_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        Q, Iq, dI, dQ, tb_output, file_name = load_sans_file(uploaded_file.name)
        if file_name is None:
            uploaded_file = None
    except IOError:
        Q = Iq = dI = dQ = None
        tb_output = ["Invalid SANS data file."]
        uploaded_file = None
    return Q, Iq, dI, dQ, tb_output, uploaded_file

@st.cache_data
def load_sans_file(file_name):
    try:
        ds = load_data(os.path.join(user_sans_file_dir, file_name))
        Q = ds.x
        Iq = ds.y
        dI = ds.dy
        dQ = ds.dx
        tb_output = ""
    except IOError:
        Q = Iq = dI = dQ = None
        tb_output = ["Invalid SANS data file."]
        file_name = None

    return Q, Iq, dI, dQ, tb_output, file_name



# ------------  GUI -------------------
file_path = user_sans_file_dir
file_list = os.listdir(file_path)
file_list = sorted(file_list)
Q1 = Iq1 = dI1 = dQ1 = None
Q2 = Iq2 = dI2 = dQ2 = None

st.write("""
    # Simulate and Compare Data
    """)

col_data1, col_data2 = st.columns([1,1])

# ----------- data column 1 ----------
choice1 = col_data1.radio("Source Data 1", ("Load File", "Simulate Data"))
if choice1 == 'Load File':
    col_data1.divider()
    uploaded_file1 = col_data1.file_uploader("Upload 1", accept_multiple_files=False)
    if uploaded_file1 is not None:
        Q1, Iq1, dI1, dQ1, tb_output1, uploaded_file1 = load_SANS_data(uploaded_file1)
        if tb_output1 == '':
            if uploaded_file1.name not in file_list:
                file_list.append(uploaded_file1.name)
                file_list = sorted(file_list)
            if 'comparison_selectbox1' in st.session_state:
                st.session_state.comparison_selectbox1 = uploaded_file1.name
    else:
        file_name1 = col_data1.selectbox("User directory", file_list, key='comparison_selectbox1')
        if file_name1 is not None:
            Q1, Iq1, dI1, dQ1, tb_output1, file_name1 = load_sans_file(file_name1)
            if tb_output1 != '':
                col_data1.error(tb_output1)

else:
    pass

# ----------- data column 2 ----------
choice2 = col_data2.radio("Source Data 2", ("Load File", "Simulate Data"))
if choice2 == 'Load File':
    col_data2.divider()
    uploaded_file2 = col_data2.file_uploader("Upload 2", accept_multiple_files=False)
    if uploaded_file2 is not None:
        Q2, Iq2, dI2, dQ2, tb_output2, uploaded_file2 = load_SANS_data(uploaded_file2)
        if tb_output2 == '':
            if uploaded_file2.name not in file_list:
                file_list.append(uploaded_file2.name)
                file_list = sorted(file_list)
            if 'comparison_selectbox1' in st.session_state:
                st.session_state.comparison_selectbox2 = uploaded_file2.name
    else:
        file_name2 = col_data2.selectbox("User directory", file_list, key='comparison_selectbox2')
        if file_name2 is not None:
            Q2, Iq2, dI2, dQ2, tb_output2, file_name2 = load_sans_file(file_name2)
            if tb_output2 != '':
                col_data2.error(tb_output2)
else:
    pass

fig = go.Figure()
if Q1 is not None:
    df_graph1 = pandas.DataFrame(list(zip(Q1, Iq1, dI1, dQ1)), columns=['Q', 'Iq', 'dI', 'dQ'])
    fig.add_trace(go.Scatter(x=df_graph1['Q'], y=df_graph1['Iq'], error_y=dict(type='data', array=df_graph1['dI'],
                                                                               visible=True), name='data 1'))
if Q2 is not None:
    df_graph2 = pandas.DataFrame(list(zip(Q2, Iq2, dI2, dQ2)), columns=['Q', 'Iq', 'dI', 'dQ'])
    fig.add_trace(go.Scatter(x=df_graph2['Q'], y=df_graph2['Iq'], error_y=dict(type='data', array=df_graph2['dI'],
                                                                               visible=True), name='data 2'))

fig.update_xaxes(type="log")
fig.update_yaxes(type="log")

st.plotly_chart(fig, user_container_width=True)
