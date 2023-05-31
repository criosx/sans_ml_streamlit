import numpy
import os
import pandas
import plotly.graph_objects as go
from sasmodels.data import load_data
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
def column_load_file(column_number=None, col=None, file_list=None):
    cn = column_number
    cns = str(cn)
    ds = None
    file_name = ''

    uploaded_file = col.file_uploader("Upload File", key='comp_load_file' + cns, accept_multiple_files=False)
    if uploaded_file is not None:
        ds, tb_output, uploaded_file = app_functions.load_SANS_data(uploaded_file, user_sans_file_dir)
        if tb_output != '':
            col.error(tb_output)
        else:
            file_name = uploaded_file.name
    if uploaded_file is None:
        file_name = col.selectbox("Select File", file_list, key='comparison_selectbox' + cns)
        if file_name is not None:
            ds, tb_output, file_name = app_functions.load_sans_file(file_name, user_sans_file_dir)
            if tb_output != '':
                col.error(tb_output)
    return ds, file_name


def column_simulate_data(column_number=None, col=None, model_list=None, config_list=None):
    cn = column_number
    cns = str(cn)
    sans_graphs = []

    model_name = col.selectbox("Select model", model_list, key='comparison_model_selectbox' + cns)
    config_list = col.multiselect("Select configurations", config_list, key='comparison_config_selectbox' + cns)
    if config_list is not None:
        if not isinstance(config_list, list):
            config_list = [config_list]

    qmin = col.number_input('q_min', min_value=0.0001, max_value=0.8, value=0.001, format='%.4f',
                            key='simulation_qmin'+cns)
    qmax = col.number_input('q_max', min_value=0.0001, max_value=0.8, value=0.8, key='simulation_qmax'+cns)

    average = True
    if len(config_list) > 1:
        average_type = col.selectbox('Configuration stitching', ['overlap', 'average'], key='simulation_stitching'+cns)
        if average_type == 'overlap':
            average = False

    if model_name is not None:
        df_pars, li_allpars, datafile_names, fitobj = \
            app_functions.get_info_from_runfile(model_name, user_sans_model_dir, user_sans_file_dir, user_sans_temp_dir)
        simpar = pandas.DataFrame(df_pars.loc['value'])
        simpar.reset_index(inplace=True)
        simpar.columns = ['par', 'value']

        col.text("Enter simulation parameters")
        simpar_edited = col.experimental_data_editor(simpar, use_container_width=True, key='simulation_paredit'+cns)

        configurations = []
        if config_list is not None:
            for entry in config_list:
                df_config = pandas.read_json(os.path.join(config_path, entry), orient='record')
                config_dict = df_config.set_index('setting').T.to_dict('records')
                configurations.append(config_dict[0])

        # create a new series of data files called sim.dat or simX.dat
        # one configuration per dataset
        dataset_configurations = []
        if len(datafile_names) == 1:
            new_file_list = ['sim.dat']
            dataset_configurations = [configurations]
        else:
            new_file_list = []
            for i in range(len(datafile_names)):
                new_file_list.append('sim' + str(i) + '.dat')
                # the same configuration per dataset
                dataset_configurations.append(configurations)
        api_sasview.write_data_filenames_to_runfile(runfile=model_name, filelist=new_file_list)
        for filename in new_file_list:
            api_sasview.write_dummy_sans_file(filename)

        if configurations:
            liData = fitobj.fnSimulateData(basefilename='sim.dat', liConfigurations=dataset_configurations, qmin=qmin,
                                           qmax=qmax, t_total=None, simpar=simpar_edited, average=average)
            for i in range(len(liData)):
                sans_graphs.append([liData[i][1], new_file_list[i]])

            if col.button("Copy simulated data to user directory.", key='simulation_copy_btn'+cns):
                for file in new_file_list:
                    shutil.copyfile(os.path.join(user_sans_temp_dir, file), os.path.join(user_sans_file_dir, file))
        else:
            col.info('Select configuration!')

    return sans_graphs

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
config_list = sorted(config_list)


st.write("""
# Instrument Configurations
""")

with st.expander('Edit'):
    uploaded_config = st.file_uploader("Upload", type=['json'])
    if uploaded_config is not None:
        load_config(uploaded_config)
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


st.write("""
    # Simulate and Compare Data
    """)

col_data1, col_data2 = st.columns([1, 1])

# ----------- data column 1 ----------
choice1 = col_data1.radio("Source Data 1", ("Load File", "Simulate Data"), key='comparison_radio_1')
col_data1.divider()
sans_graphs1 = sans_graphs2 = []

if choice1 == 'Load File':
    ds1, file_name1 = column_load_file(column_number=1, col=col_data1, file_list=file_list)
    if ds1 is not None:
        sans_graphs1 = [[ds1, file_name1]]
else:
    sans_graphs1 = column_simulate_data(column_number=1, col=col_data1, model_list=model_list, config_list=config_list)

# ----------- data column 2 ----------
choice2 = col_data2.radio("Source Data 2", ("Load File", "Simulate Data"), key='comparison_radio_2')
col_data2.divider()
if choice2 == 'Load File':
    ds2, file_name2 = column_load_file(column_number=2, col=col_data2, file_list=file_list)
    if ds2 is not None:
        sans_graphs2 = [[ds2, file_name2]]
else:
    sans_graphs2 = column_simulate_data(column_number=2, col=col_data2, model_list=model_list, config_list=config_list)

fig = go.Figure()
if sans_graphs1:
    for g in sans_graphs1:
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=g[0]['I'], mode='markers',
                                 error_y=dict(type='data', array=g[0]['dI'], visible=True), name='1 - '+g[1]))
if sans_graphs2:
    for g in sans_graphs2:
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=g[0]['I'], mode='markers',
                                 error_y=dict(type='data', array=g[0]['dI'], visible=True), name='2 - '+g[1]))
fig.update_xaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='Momentum transfer (1/Å)')
fig.update_yaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='Intensity (1/cm)')
fig['data'][0]['showlegend'] = True
st.plotly_chart(fig, user_container_width=True)

fig = go.Figure()
if sans_graphs1:
    for g in sans_graphs1:
        y_result = numpy.divide(g[0]['dI'], g[0]['I'], out=numpy.zeros_like(g[0]['dI']), where=g[0]['I']!=0)
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=y_result, mode='markers', name='1 - '+g[1]))
if sans_graphs2:
    for g in sans_graphs2:
        y_result = numpy.divide(g[0]['dI'], g[0]['I'], out=numpy.zeros_like(g[0]['dI']), where=g[0]['I'] != 0)
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=y_result, mode='markers', name='2 - '+g[1]))
fig.update_xaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='Momentum transfer (1/Å)')
fig.update_yaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='dI / I')
fig['data'][0]['showlegend'] = True
st.plotly_chart(fig, user_container_width=True)

fig = go.Figure()
if sans_graphs1:
    for g in sans_graphs1:
        y_result = numpy.divide(g[0]['dQ'], g[0]['Q'], out=numpy.zeros_like(g[0]['dQ']), where=g[0]['Q']!=0)
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=y_result, mode='markers', name='1 - '+g[1]))
if sans_graphs2:
    for g in sans_graphs2:
        y_result = numpy.divide(g[0]['dQ'], g[0]['Q'], out=numpy.zeros_like(g[0]['dQ']), where=g[0]['Q']!=0)
        fig.add_trace(go.Scatter(x=g[0]['Q'], y=y_result, mode='markers', name='2 - '+g[1]))
fig.update_xaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='Momentum transfer (1/Å)')
fig.update_yaxes(type="log", ticks='inside', showgrid=True, showline=True, linewidth=2, mirror=True,
                 title_text='dQ / Q')
fig['data'][0]['showlegend'] = True
st.plotly_chart(fig, user_container_width=True)