import pandas
from pathlib import Path
import streamlit as st
import uuid

from sans_app.support import app_functions
from sans_app.support import configuration

from scattertools.support import api_sasview
from pse.streamlit_components import (check_session_state, clear_project_data_dialog, monitor, run_control,
                                      save_session_state)

if not st.session_state["data_folders_ready"]:
    st.info("Files and Folders not set up. Please visit the File System tab.")
    st.stop()

# the optimization directory, that will contain all PSE-related files
user_sans_opt_dir = st.session_state['user_sans_opt_dir']
# Streamlit components from the PSE module expect this canonical directory
st.session_state['pse_dir'] = st.session_state['user_sans_opt_dir']
# the model directory used by other pages of this app, as well
user_sans_model_dir = st.session_state['user_sans_model_dir']
# the dirctory containing all the SANS scattering data files
user_sans_file_dir = st.session_state['user_sans_file_dir']
# the directory that contains the current fit (runfile) that will be used for the optimization
user_sans_fit_dir = st.session_state['user_sans_fit_dir']
# the directory that contains the configuration files from which can be chosen
user_sans_config_dir = st.session_state['user_sans_config_dir']
# the temp directory for various purposes
user_sans_temp_dir = st.session_state['user_sans_temp_dir']

# some analysis of the present files
file_list = sorted(p.name for p in Path(user_sans_file_dir).iterdir()
                   if p.is_file() and not p.name.startswith('.'))

model_list = sorted(p.name for p in Path(user_sans_model_dir).iterdir()
                   if p.is_file() and not p.name.startswith('.'))

config_list = sorted(p.name for p in Path(user_sans_config_dir).iterdir()
                   if p.is_file() and not p.name.startswith('.'))

# ------------ Functionality -----------

def adjust_consecutive_configurations():
    if len(st.session_state['df_opt_config']) > 1:
        for j in range(1, len(st.session_state['df_opt_config'])):
            change_flag = False
            # shorthand handles
            df0 = st.session_state['df_opt_config_edited'][0]
            dfj = st.session_state['df_opt_config_edited'][j]
            # modify successive configurations if any setting is shared with first configuration
            for par in df0.index.values:
                # copy a shared setting from the first to consecutive dataframes
                if par in dfj.index and bool(df0.loc[par, "shared"]) and not bool(dfj.loc[par, "shared"]):
                    dfj.loc[par, :] = df0.loc[par, :]
                    change_flag = True
                if par in dfj.index and bool(df0.loc[par, "shared"]) and bool(dfj.loc[par, "shared"]):
                    if not dfj.loc[par, :].equals(df0.loc[par, :]):
                        dfj.loc[par, :] = df0.loc[par, :]
                        change_flag = True
                if par in dfj.index and not bool(df0.loc[par, "shared"]) and bool(dfj.loc[par, "shared"]):
                    dfj.loc[par, :] = st.session_state['df_opt_config_original'][j].loc[par, :]
                    change_flag = True
            if change_flag:
                # change key of data editor associated with that particular data frame
                st.session_state['df_opt_config_key'][j] = str(uuid.uuid4())
                st.session_state['df_opt_config'][j] = dfj
                st.session_state['df_opt_config_edited'][j] = dfj

def summarize_optimization_parameter_settings():
    li_summary = []
    dfb = st.session_state['opt_background']

    # add model parameters
    for index, row in st.session_state['opt_parameters'].iterrows():
        parname = index
        # ["value", "lowerlimit", "upperlimit", "relative", "lower_opt", "upper_opt", "optimize"]
        if row['type'] == 'information':
            partype = 'd'
        else:
            partype = 'i'
        if not row['relative']:
            partype = 'f' + partype

        if index in dfb['source'].values:
            dataset = str(dfb.loc[dfb['source'] == index, 'dataset'].at[0])
            parconfig = '*'
        elif index in dfb['sink'].values:
            dataset = 'b'+str(dfb.loc[dfb['sink'] == index, 'dataset'].at[0])
            parconfig = '*'
        else:
            dataset = '-'
            parconfig = '-'

        if row['optimize']:
            lower_opt = str(row['lower_opt'])
            upper_opt = str(row['upper_opt'])
            step_opt = str(row['step_opt'])
        else:
            lower_opt = ''
            upper_opt = ''
            step_opt = ''
        li_summary.append([partype, dataset, parconfig, parname, row['value'], row['lowerlimit'], row['upperlimit'],
                           lower_opt, upper_opt, step_opt])

    # add configuration settings
    df0 = st.session_state['df_opt_config_edited'][0]
    num_config = len(st.session_state['df_opt_config_edited'])
    for i, config in enumerate(st.session_state['df_opt_config_edited']):
        for index, row in config.iterrows():
            parname = index
            if parname in df0.index.values and (num_config == 1 or df0.loc[index, 'shared']):
                parconfig = '*'
            else:
                parconfig = str(i)
            if row['optimize']:
                lfit = ufit = '0'
                lower_opt = str(row['lower_opt'])
                upper_opt = str(row['upper_opt'])
                step_opt = str(row['step_opt'])
            else:
                lfit = ufit = lower_opt = upper_opt = step_opt = ''

            li_summary.append(['n', '*', parconfig, parname, row['value'], lfit, ufit, lower_opt, upper_opt, step_opt])

    df_summary = pandas.DataFrame(li_summary, columns=['type', 'dataset', 'config.', 'parameter', 'value', 'l_fit',
                                                       'u_fit', 'l_opt', 'u_opt', 'step_opt'])

    return df_summary


def update_df_config(config_list_select):
    """
    Loads the configurations provided by the filenames in config_list_select into a list of dataframes, if it is a new
    selection. It then adds columns required for the optimization. For a new set of configurations, the widget keys
    of the instrument configuration parameters widget will be updated. It also saves the raw configurations for
    passing into Entropy().

    :param config_list_select: list of configuration filenames
    :return:
    """

    # function argument homogeineization
    if config_list_select is not None:
        if not isinstance(config_list, list):
            config_list_select = [config_list_select]
    else:
        config_list_select = []

    # only run update if config_lisit_select has changed
    if 'opt_config_list_select' in st.session_state and \
            st.session_state['opt_config_list_select'] == config_list_select:
        return
    else:
        st.session_state['opt_config_list_select'] = config_list_select

    df_config = []          # for streamlit data input and downstream processing
    configurations = []     # do be passed to Entropy(config= )
    for config_name in config_list_select:
        df = pandas.read_json(Path(user_sans_config_dir) / config_name, orient='record')
        df_config.append(df.copy(deep=True))
        config_dict = df.set_index('setting').T.to_dict('records')
        configurations.append(config_dict[0])

    st.session_state['pse_configurations'] = configurations

    for i, config in enumerate(df_config):
        if len(df_config) > 1:
            df_config[i]['shared'] = False
        df_config[i]['lower_opt'] = 0.0
        df_config[i]['upper_opt'] = 1.0
        df_config[i]['step_opt'] = 0.1
        df_config[i]['optimize'] = False
        df_config[i] = config.sort_values('setting')
        df_config[i].set_index('setting', inplace=True)

    # will store the edited configuration dataframe from the widget
    df_config_edited=[]
    # a saved copy of the original values for when config parameters are unshared between configurations
    df_config_original=[]
    for i, _ in enumerate(config_list_select):
        df_config_edited.append(df_config[i].copy(deep=True))
        df_config_original.append(df_config[i].copy(deep=True))

    st.session_state['df_opt_config'] = df_config
    st.session_state['df_opt_config_edited'] = df_config_edited
    st.session_state['df_opt_config_original'] = df_config_original
    st.session_state['df_opt_config_key'] = []
    for _ in range(len(df_config)):
        st.session_state['df_opt_config_key'].append(str(uuid.uuid4()))

    return

# ------------  GUI -------------------
check_session_state()
st.write("""
# Job Monitor
""")
with st.expander('Monitor'):
    monitor()

st.write("""
# Setup New Optimization
""")

with ((st.expander('Setup'))):
    st.write("""
    ## SANS Model
    """)
    if 'pse_model_name' in st.session_state and st.session_state['pse_model_name'] in model_list:
         indx = model_list.index(st.session_state['pse_model_name'])
    else:
        st.session_state['pse_model_name'] = None
        indx = None

    model_name = st.selectbox("Select from user directory", model_list, index=indx, key='opt_sans_model_selectbox')

    if model_name is None:
        st.info("Please select a SANS model.")
        st.stop()
    if st.session_state['pse_model_name'] != model_name:
        st.session_state['pse_model_name'] = model_name
        save_session_state(st.session_state['pse_dir'])

    # this also copies the runfile and the data files to user_sans_opt_dir
    df_pars, li_all_pars, datafile_names, model_fitobj = \
        app_functions.get_info_from_runfile(model_name, user_sans_model_dir, user_sans_file_dir, user_sans_opt_dir)
    df_pars = df_pars.drop(index=['number', 'relval', 'variable', 'error'])
    df_pars = df_pars.transpose()

    st.write("""
    ## Instrument Configurations
    """)
    if 'pse_config_list_select' in st.session_state:
        config_list_default = [
            config_name
            for config_name in st.session_state['pse_config_list_select']
            if config_name in config_list
        ]
    else:
        st.session_state['pse_config_list_select'] = []
        config_list_default = []

    config_list_select = st.multiselect(
        "Select from user directory",
        config_list,
        default=config_list_default,
        key='opt_sans_config_multiselect'
    )
    if not config_list_select:
        st.info("Please select an instrument configuration.")
        st.stop()

    if st.session_state['pse_config_list_select'] != config_list_select:
        st.session_state['pse_config_list_select'] = config_list_select
        save_session_state(st.session_state['pse_dir'])

    # load and process configuration files
    update_df_config(config_list_select)

    st.write("""
    ## Parameters
    ### Model Fit
    """)
    df_pars['relative'] = True
    df_pars['lower_opt'] = 0.0
    df_pars['upper_opt'] = 1.0
    df_pars['optimize'] = False
    df_pars['type'] = 'information'
    df_pars['step_opt'] = 0.1
    parameters_edited = st.data_editor(
        df_pars,
        disabled=["_index"],
        column_order=["type", "value", "lowerlimit", "upperlimit", "relative", "optimize", "lower_opt", "upper_opt",
                      "step_opt"],
        column_config={
            'type': st.column_config.SelectboxColumn(
                "type",
                help="Nuisance parameter or contributing to the information content of the measurment.",
                options=['information', 'nuisance']
            ),
            'lowerlimit': "lower fit",
            'upperlimit': "upper",
            'relative': 'relative',
            'lower_opt': 'lower opt',
            'upper_opt': 'upper',
            'optimize': 'optimize',
            'step_opt': 'step'
        }
    )
    st.session_state['opt_parameters'] = parameters_edited

    st.write("""
    ### Instrument Configurations
    """)
    tablist = st.tabs(config_list_select)
    first_init_marker = False
    for i, config in enumerate(st.session_state['df_opt_config']):
        with tablist[i]:
            if i > 0:
                # Shared is disabled except for the first configuration. This is not a limitation as any shared
                # setting must be present in all configurations.
                disabled = ["_index", "setting", "shared"]
            else:
                # settings can be shared in the first configuration
                disabled = ["_index", "setting"]

            # The key argument has a variable string from session state that is used to reset the data editor upon
            # changing it. Otherwise, this is the typical approach to avoid the every-other-update works only
            # problem
            common_keyword_args = {
                'key': st.session_state['df_opt_config_key'][i],
                'hide_index': False,
                'width': 'stretch',
                'disabled': disabled,
                'column_order': ["setting", "value", "shared", "optimize", "lower_opt", "upper_opt", "step_opt"],
                'column_config': {
                    'lower_opt': 'lower opt',
                    'upper_opt': 'upper',
                    'optimize': 'optimize',
                    'step_opt': 'step'
                }
            }

            st.session_state['df_opt_config_edited'][i] = st.data_editor(
                st.session_state['df_opt_config'][i].copy(deep=True),
                **common_keyword_args
            )
            adjust_consecutive_configurations()

    st.write("""
    ### Simulated Scattering Background
    """)
    if model_name is not None and config_list_select:
        col_opt_1, col_opt_2 = st.columns([1.5, 1])
        num_datasets = len(datafile_names)

        li_df = []
        for i in range(num_datasets):
            li_df.append([i, None, None])

        df_opt_background = pandas.DataFrame(li_df, columns=["dataset", "source", "sink"])

        df_opt_background_edited = col_opt_1.data_editor(
            df_opt_background,
            hide_index=True,
            disabled=["dataset"],
            column_config={
                'dataset': 'data set',
                'source': st.column_config.SelectboxColumn(
                    "source",
                    help="Parameter that determines background.",
                    options=df_pars.index.values.tolist()
                ),
                'sink': st.column_config.SelectboxColumn(
                    "sink",
                    help="Parameter that determines background.",
                    options=df_pars.index.values.tolist()
                )
            }
        )

        st.session_state['opt_background'] = df_opt_background_edited
        opt_background_rule = col_opt_2.selectbox("background rule", ['water', 'acetonitrile'])

        st.write("""
        ### Shorthand Summary
        """)
        df_summary = summarize_optimization_parameter_settings()
        st.write(df_summary)


datafile_names = api_sasview.extract_data_filenames_from_runfile(runfile=Path(user_sans_model_dir) / str(model_name))
for file in datafile_names:
    dfile = Path(user_sans_file_dir) / file
    if not dfile.is_file():
        infostr = 'Data file ' + file + ' not in user file folder. Please set up complete fit under Models and Fit'
        st.info(infostr)
        st.stop()


# prepare fit directory
# not needed, as app_functions.get_info_from_runfile() above is already doing this


st.write("""
# Run Control
## Data Simulation
""")
col_opt_3, col_opt_4 = st.columns([1, 1])
default_qmin = st.session_state['pse_qmin'] if 'pse_qmin' in st.session_state else 0.001
default_qmax = st.session_state['pse_qmax'] if 'pse_qmax' in st.session_state else 0.5
default_tfix = st.session_state['pse_tfix'] if 'pse_tfix' in st.session_state else 0
qmin = col_opt_3.number_input('q_min [1/Å]', min_value=0.0001, max_value=0.8, value=default_qmin, format='%.4f')
qmax = col_opt_4.number_input('q_max [1/Å]', min_value=0.0001, max_value=0.8, value=default_qmax)
tfix = col_opt_3.number_input('max time [s]   (0 = use configuration settings)', min_value=0, value=default_tfix,
                              format='%i', step=1200)
st.session_state['pse_qmin'] = qmin
st.session_state['pse_qmax'] = qmax
st.session_state['pse_tfix'] = tfix

st.write("""
## Data Fitting
""")

col_opt_5, col_opt_6 = st.columns([1, 1])
default_fitter = st.session_state['pse_fitter'] if 'pse_fitter' in st.session_state else 'MCMC'
default_mcmcburn = st.session_state['pse_mcmcburn'] if 'pse_mcmcburn' in st.session_state else 100
default_mcmcsteps = st.session_state['pse_mcmcsteps'] if 'pse_mcmcsteps' in st.session_state else 100
options=['MCMC', 'LM']
indx = options.index(default_fitter)
fitter = col_opt_5.selectbox(label='optimizer', options=options, index=indx)
if fitter == 'MCMC':
    mcmcburn = col_opt_6.number_input('MCMC burn', min_value=100, value=default_mcmcburn, step=100)
    mcmcsteps = col_opt_6.number_input('MCMC steps', min_value=100, value=default_mcmcsteps, step=100)
else:
    mcmcburn = default_mcmcburn
    mcmcsteps = default_mcmcsteps

kwargs_entropy_gp = {
    'exp_par': df_summary,
    'fitsource': 'sasview',
    'storage_path': str(user_sans_opt_dir),
    'runfile': model_name,
    'mcmcburn': mcmcburn,
    'mcmcsteps': mcmcsteps,
    'deldir': True,
    'convergence': 2.0,
    'fitter': 'MCMC',
    'remove_fit_dir': True,
    'lm_iterations': 3,
    'mode': 'water',
    'background_rule': None,
    'configuration': st.session_state['pse_configurations'],
    'qmin': qmin,
    'qmax': qmax,
    'qrangefromfile': False,
    't_total': tfix,
    'calc_symmetric': True,
    'upper_info_plotlevel': None,
    'plotlimits_filename': '',
    'jupyter_clear_output': False
}

save_session_state(st.session_state['pse_dir'])

st.write("""
## Phase Space Exploration
""")
run_control(configuration=configuration, kwargs=kwargs_entropy_gp)

