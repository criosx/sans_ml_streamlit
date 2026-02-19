import os
import shutil
import streamlit as st
import sys
sys.path.append(st.session_state['app_functions_dir'])
import app_functions

user_sans_model_dir = st.session_state['user_sans_model_dir']
user_sans_file_dir = st.session_state['user_sans_file_dir']
user_sans_fit_dir = st.session_state['user_sans_fit_dir']
user_sans_temp_dir = os.path.join(st.session_state['streamlit_dir'], 'temp')


# ---- Functionality --------
def add_par(parname, model_name, fitobj):
    fitobj.Interactor.fnReplaceParameterLimitsInSetup(parname, 0., 1., modify='add')
    shutil.copyfile(os.path.join(user_sans_temp_dir, model_name), os.path.join(user_sans_model_dir, model_name))


def remove_par(parname, model_name, fitobj):
    fitobj.Interactor.fnReplaceParameterLimitsInSetup(parname, 0., 1., modify='remove')
    shutil.copyfile(os.path.join(user_sans_temp_dir, model_name), os.path.join(user_sans_model_dir, model_name))


def update_par(df_pars, model_name, fitobj):
    labels = list(df_pars.index)
    for index, row in df_pars.iterrows():
        fitobj.Interactor.fnReplaceParameterLimitsInSetup(index, row['lowerlimit'], row['upperlimit'])
    shutil.copyfile(os.path.join(user_sans_temp_dir, model_name), os.path.join(user_sans_model_dir, model_name))


@st.cache_data
def load_model(file):
    try:
        with open(os.path.join(user_sans_model_dir, file.name), "wb") as f:
            f.write(file.getbuffer())
        st.session_state['sans_model_selectbox'] = file.name
    except IOError:
        pass


def save_sans_model(path, name):
    with open(os.path.join(path, name), 'w') as f:
        f.write(st.session_state['sans_model_text'])


# --- GUI ----------------------
st.write("""
# Select SANS Model
""")

# -------- SANS model loader
model_path = user_sans_model_dir
model_list = os.listdir(model_path)
model_list = sorted([element for element in model_list if '.py' in element])
datafile_names = None

# st.text("Select SANS model")
col1_a, col1_b = st.columns([1.5, 2])
uploaded_model = col1_b.file_uploader("Upload / Download", type=['py'])
if uploaded_model is not None:
    load_model(uploaded_model)
model_name = col1_a.selectbox("Select from user directory", model_list, key='sans_model_selectbox')

if model_name:
    with open(os.path.join(user_sans_model_dir, model_name), "rb") as file:
        btn = col1_b.download_button(
            label="Download",
            data=file,
            file_name=model_name,
            mime='text/plain'
        )

    st.divider()

    st.write("""
    # Edit Model
    """)

    with open(os.path.join(model_path, model_name)) as f:
        model_txt = f.readlines()
    with st.expander("Edit Model Script"):
        txt = st.text_area('Model Script', "".join(model_txt), key='sans_model_text', height=400,
                           on_change=save_sans_model, args=[model_path, model_name], label_visibility='collapsed')

    col1_1, col1_2 = st.columns([1, 1])
    df_pars, li_all_pars, datafile_names, model_fitobj = \
        app_functions.get_info_from_runfile(model_name, user_sans_model_dir, user_sans_file_dir, user_sans_fit_dir)
    df_pars = df_pars.drop(index=['number', 'relval', 'variable', 'error', 'value'])
    df_pars = df_pars.transpose()

    col1_1.text('Edit fit ranges')
    parameters_edited = col1_1.data_editor(
        df_pars,
        disabled=["_index"],
        column_config={
            'lowerlimit': "lower limit",
            'upperlimit': "upper limit"
        }
    )
    col1_1.button('Apply', on_click=update_par, args=[parameters_edited, model_name, model_fitobj],
                  use_container_width=False)

    col1_2.text('Add / Remove fit parameters')
    col1_2_1, col1_2_2 = col1_2.columns([2, 1])
    li_current_pars = sorted(list(df_pars.index.values))
    li_addable_pars = sorted(list(set(li_all_pars) - set(li_current_pars)))
    par_to_add = col1_2_1.selectbox("Add fit parameter", li_addable_pars, label_visibility='collapsed')
    col1_2_2.button('Add', on_click=add_par, args=[par_to_add, model_name, model_fitobj], use_container_width=True)

    col1_2_3, col1_2_4 = col1_2.columns([2, 1])
    par_to_del = col1_2_3.selectbox("Remove fit parameter", li_current_pars, label_visibility='collapsed')
    col1_2_4.button('Remove', on_click=remove_par, args=[par_to_del, model_name, model_fitobj],
                    use_container_width=True)

    col1_2.divider()
    col1_2.text('Expected Data Files:')
    for file in datafile_names:
        col1_2.text(file)

    st.divider()


st.write("""
# Fit Data
""")

uploaded_file = st.file_uploader("Upload SANS files specified in your script", accept_multiple_files=True)
if uploaded_file is not None:
    if not isinstance(uploaded_file, list):
        filelist = [uploaded_file]
    app_functions.load_sans_files(uploaded_file, user_sans_file_dir)

col1_3, col1_4 = st.columns([1, 1])
burn = col1_3.number_input('burn', format='%i', step=50, min_value=50, value=100, key='burn')
steps = col1_4.number_input('steps', format='%i', step=50, min_value=50, value=100, key='steps')

if st.button('Run Fit'):
    if model_name is not None and uploaded_file is not None:
        datafile_names_uploaded = [file.name for file in uploaded_file]
        app_functions.run_fit(fitdir=user_sans_fit_dir, runfile=model_name, datafile_names=datafile_names,
                              datafile_names_uploaded=datafile_names_uploaded, file_dir=user_sans_file_dir,
                              model_dir=user_sans_model_dir, burn=burn, steps=steps)
        # zip fit folder for download
        st.info('Zipping the fit ...')
        shutil.make_archive(os.path.join(user_sans_temp_dir, 'fit'), 'zip', user_sans_fit_dir)
        with open(os.path.join(user_sans_temp_dir, 'fit.zip'), "rb") as file:
            btn2 = st.download_button(
                label='Download  Fit',
                data=file,
                file_name='fit.zip',
                mime=None
            )

