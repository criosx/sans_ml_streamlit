
import pandas
from pathlib import Path
import streamlit as st
import uuid

from sans_app.support import app_functions
from sans_app.support import configuration

from scattertools.support import api_sasview
from pse.streamlit_components import (start_of_script_business, monitor, run_control, pse_directory,
                                      end_of_script_business)

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
            lower_opt = None
            upper_opt = None
            step_opt = None
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
                lfit = ufit = 0.
                lower_opt = row['lower_opt']
                upper_opt = row['upper_opt']
                step_opt = row['step_opt']
            else:
                lfit = ufit = lower_opt = upper_opt = step_opt = None

            li_summary.append(['n', '*', parconfig, parname, row['value'], lfit, ufit, lower_opt, upper_opt, step_opt])

    columns = pandas.Index(['type', 'dataset', 'config.', 'parameter', 'value', 'l_fit', 'u_fit', 'l_opt', 'u_opt',
                            'step_opt'])
    df_summary = pandas.DataFrame(li_summary, columns=columns)
    # remove shared configuration parameters that end up being exact duplicate rows
    df_summary = df_summary.drop_duplicates()

    return df_summary


def update_df_config(config_list_select):
    """
    Loads the configurations provided by the filenames in config_list_select into a list of dataframes, if it is a new
    selection. It then adds columns required for the optimization. For a new set of configurations, the widget keys
    of the instrument configuration parameters widget will be updated. It also saves the raw configurations for
    passing into Entropy().

    :param config_list_select: list of configuration filenames
    :return: no return value
    """

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
start_of_script_business()

cfg = st.session_state.cfg

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



st.write("""
# Job Monitor
""")
with st.expander('Monitor'):
    monitor()

st.write("""
# Setup New Optimization
""")

with (((((st.expander('Setup')))))):
    st.write("""
    ## PSE Directory
    """)
    pse_directory(identifier='SANS_experimental_optimization', st_directory_identifier='pse_dir')

    st.write("""
    ## SANS Model
    """)
    if cfg.pse_model_name in model_list:
         indx = model_list.index(cfg.pse_model_name)
    else:
        cfg.pse_model_name = None
        indx = None

    model_name = st.selectbox("Select from user directory", model_list, index=indx)

    if model_name is None:
        st.info("Please select a SANS model.")
        configuration.save_persistent_cfg(cfg)
        st.stop()
    if model_name != cfg.pse_model_name:
        cfg.pse_model_name = model_name
        st.session_state['pse_opt_pars_key'] = uuid.uuid4()

    datafile_names = api_sasview.extract_data_filenames_from_runfile(
        runfile=Path(user_sans_model_dir) / str(cfg.pse_model_name))
    for file in datafile_names:
        dfile = Path(user_sans_file_dir) / file
        if not dfile.is_file():
            infostr = 'Data file ' + file + ' not in user file folder. Please set up complete fit under Models and Fit'
            st.info(infostr)
            st.stop()

    st.write("""
    ## Instrument Configurations
    """)
    config_list_default = [
        config_name
        for config_name in cfg.pse_config_list
        if config_name in config_list
    ]

    if 'pse_default_config_list' not in st.session_state or st.session_state['configuration_reloaded']:
        st.session_state['pse_default_config_list'] = config_list_default
        st.session_state['config_multiselect_key'] = uuid.uuid4()

    config_list_select:list = st.multiselect("Select from user directory",
                                             config_list,
                                             key=st.session_state['config_multiselect_key'],
                                             default=st.session_state['pse_default_config_list'])
    if not config_list_select:
        st.info("Please select an instrument configuration.")
        st.stop()

    if cfg.pse_config_list != config_list_select or 'df_opt_config' not in st.session_state:
        cfg.pse_config_list = config_list_select
        # load and process configuration files, provide new widget keys if necessary
        update_df_config(cfg.pse_config_list)

    st.write("""
    ## Parameters
    ### Model Fit
    """)
    # this also copies the runfile and the data files to user_sans_opt_dir, we try to run this function with @st.cache
    df_pars, li_all_pars, datafile_names, model_fitobj = \
        app_functions.process_runfile(cfg.pse_model_name,
                                      user_sans_model_dir,
                                      user_sans_file_dir,
                                      user_sans_opt_dir,
                                      force=False,
                                      correct_data_paths=False)
    df_pars = df_pars.drop(index=['number', 'relval', 'variable', 'error'])
    df_pars = df_pars.transpose()
    df_pars['relative'] = True
    df_pars['lower_opt'] = 0.0
    df_pars['upper_opt'] = 1.0
    df_pars['optimize'] = False
    df_pars['type'] = 'information'
    df_pars['step_opt'] = 0.1

    if  st.session_state['configuration_reloaded']:
        saved_pars = cfg.pse_parameters_edited_json
        # check if reloaded config is non-empty and contains row dictionaries
        if isinstance(saved_pars, list) and saved_pars and all(isinstance(row, dict) for row in saved_pars):
            df_pars = pandas.DataFrame(saved_pars)
            if "index" in df_pars.columns:
                df_pars.set_index("index", inplace=True)
                df_pars.index.name = None
        st.session_state['pse_opt_pars_key'] = uuid.uuid4()

    st.session_state['opt_parameters'] = st.data_editor(
        df_pars,
        key = st.session_state['pse_opt_pars_key'],
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
    # save current dataframe state to the configuration
    cfg.pse_parameters_edited_json = st.session_state.opt_parameters.reset_index().to_dict(orient="records")

    st.write("""
    ### Instrument Configurations
    """)
    if  st.session_state['configuration_reloaded']:
        for i in range(len(cfg.pse_config_list)):
            if cfg.pse_configs_edited_json and i<len(cfg.pse_configs_edited_json):
                saved_pars = cfg.pse_configs_edited_json[i]
                # check if reloaded config data is non-empty and not a dict
                if isinstance(saved_pars, list) and saved_pars and all(isinstance(row, dict) for row in saved_pars):
                    st.session_state['df_opt_config'][i] = pandas.DataFrame(saved_pars)
                    if "index" in st.session_state['df_opt_config'][i].columns:
                        st.session_state['df_opt_config'][i].set_index("setting", inplace=True)
            st.session_state['df_opt_config_key'][i] = uuid.uuid4()

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

    # save various instrument configuration data frames to the app config
    cfg.pse_configs_json = [df.reset_index().to_dict(orient="records") for df in st.session_state.df_opt_config]
    cfg.pse_configs_edited_json = [df.reset_index().to_dict(orient="records") for df in
                                   st.session_state.df_opt_config_edited]
    cfg.pse_configs_original_json = [df.reset_index().to_dict(orient="records") for df in
                                     st.session_state.df_opt_config_original]

    st.write("""
    ### Simulated Scattering Background
    """)
    if cfg.pse_model_name is not None and config_list_select:
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
        df_summary = df_summary.replace(
            [float('inf'), float('-inf')], '').fillna('').astype(str).replace({'nan': '', 'None': ''}
                                                                              )
        st.write(df_summary)

# prepare fit directory
# not needed, as app_functions.process_runfile() above is already doing this


st.write("""
# Run Control
## Data Simulation
""")
col_opt_3, col_opt_4 = st.columns([1, 1])
col_opt_3.number_input('q_min [1/Å]', min_value=0.0001, max_value=0.8, value=cfg.pse_qmin, format='%.4f',
                       key='pse_qmin')
cfg.pse_qmin = st.session_state.pse_qmin
col_opt_4.number_input('q_max [1/Å]', min_value=0.0001, max_value=0.8, value=cfg.pse_qmax, key='pse_qmax')
cfg.pse_qmax = st.session_state.pse_qmax
col_opt_3.number_input('max time [s]   (0 = use configuration settings)', min_value=0, key='pse_tfix',
                       value=cfg.pse_tfix, step=1200)
cfg.pse_tfix = st.session_state.pse_tfix

st.write("""
## Data Fitting
""")
col_opt_5, col_opt_6 = st.columns([1, 1])
options=['MCMC', 'LM']
indx = options.index(cfg.pse_fitter)
col_opt_5.selectbox(label='optimizer', options=options, index=indx, key='pse_fitter')
cfg.pse_fitter = st.session_state.pse_fitter
if cfg.pse_fitter == 'MCMC':
    col_opt_6.number_input('MCMC burn', min_value=100, value=cfg.pse_mcmcburn, step=100, key='pse_mcmcburn')
    cfg.pse_mcmcburn = st.session_state.pse_mcmcburn
    col_opt_6.number_input('MCMC steps', min_value=100, value=cfg.pse_mcmcsteps, step=100, key='pse_mcmcsteps')
    cfg.pse_mcmcsteps = st.session_state.pse_mcmcsteps

kwargs_entropy_gp = {
    'exp_par': df_summary,
    'fitsource': 'sasview',
    'storage_path': str(user_sans_opt_dir),
    'runfile': cfg.pse_model_name,
    'mcmcburn': cfg.pse_mcmcburn,
    'mcmcsteps': cfg.pse_mcmcsteps,
    'deldir': True,
    'convergence': 2.0,
    'fitter': cfg.pse_fitter,
    'remove_fit_dir': True,
    'lm_iterations': 3,
    'mode': 'water',
    'background_rule': None,
    'configuration': st.session_state['pse_configurations'],
    'qmin': cfg.pse_qmin,
    'qmax': cfg.pse_qmax,
    'qrangefromfile': False,
    't_total': cfg.pse_tfix,
    'calc_symmetric': True,
    'upper_info_plotlevel': None,
    'plotlimits_filename': '',
    'jupyter_clear_output': False
}

st.write("""
## Phase Space Exploration
""")
run_control(configuration=configuration, kwargs=kwargs_entropy_gp)

end_of_script_business()

