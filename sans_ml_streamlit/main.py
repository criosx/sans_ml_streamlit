import matplotlib.pyplot as plt
import numpy
import os
import pickle
import streamlit as st
from sasmodels.data import load_data
import tensorflow as tf
import time

if not os.path.isdir('temp'):
    os.makedirs('temp')

tb_output = ['No SANS File Loaded']


# GUI signals
def update_background_input_auto(Q, Iq, dI, dQ, qmin, qmax):
    if uploaded_file is not None:
        background = auto_background(Q, Iq, dI, dQ, qmin, qmax)
        st.session_state.background = background


# Functionality
@st.cache_data
def auto_background(Q, Iq, dI, dQ, qmin, qmax):
    Iq_backg = numpy.where(Q <= qmin, Iq[Q <= qmin][-1], Iq)
    Iq_backg = numpy.where(Q >= qmax, Iq[Q >= qmax][0], Iq_backg)

    # average of last n points that is within the error bar of the n-1 th point
    background = None
    for i in range(-5, -30, -1):
        background_new = numpy.average(Iq_backg[i:])
        if numpy.abs(Iq_backg[i - 1] - background_new) > 2 * dI[i - 1]:
            break
        background = background_new
    return background


@st.cache_data
def load_ml_model(model):
    dirname = os.path.join('ml_models', model)
    try:
        sans_models = fnLoadObject(os.path.join(dirname, 'sans_models.dat'))
        par_names = fnLoadObject(os.path.join(dirname, 'par_names.dat'))
        # Load model for prediction. Compile = False avoids supplying the custom loss function.
        ml_model = tf.keras.models.load_model(dirname, compile=False)
    except IOError:
        tb_output = ['Could not load ML model']
        ml_model = None
        sans_models = None
        par_names = None
    return sans_models, par_names, ml_model


@st.cache_data
def load_SANS_data(uploaded_file):
    try:
        with open(os.path.join("temp", uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        ds = load_data(os.path.join("temp", uploaded_file.name))
        Q = ds.x
        Iq = ds.y
        dI = ds.dy
        dQ = ds.dx
        tb_output = " "
    except IOError:
        Q = Iq = dI = dQ = None
        tb_output = ["Invalid SANS data file."]
        uploaded_file = None
    return Q, Iq, dI, dQ, tb_output, uploaded_file

def fnLoadObject(sFileName):
    with open(sFileName, 'rb') as file:
        load_object = pickle.load(file)
    return load_object


@st.cache_data
def plot_SANS(Q, Iq, dI, dQ, background, qmin, qmax):
    time.sleep(1)
    # adjust Iq w/ respect to qmin, qmax
    Iq_plot = numpy.where(Q <= qmin, Iq[Q <= qmin][-1], Iq)
    Iq_plot = numpy.where(Q >= qmax, Iq[Q >= qmax][0], Iq_plot)
    dI_plot = numpy.where(Q < qmin, 0.0, dI)
    dI_plot = numpy.where(Q > qmax, 0.0, dI_plot)

    upper_index = numpy.where(Q >= qmax)
    Iq_plot[upper_index] = Iq[upper_index][0]

    # Plot SANS curves
    fig, ax = plt.subplots()
    # Clear whatever was in the plot before
    ax.clear()
    # Plot data, add labels, change colors, ...
    ax.errorbar(Q, Iq_plot, dI_plot, ls='none', color='deepskyblue')
    ax.scatter(Q, Iq_plot, s=30, marker='o', facecolors='none', edgecolors='deepskyblue', label='orignal')
    ax.errorbar(Q, Iq_plot - background, dI_plot, ls='none', color='darkred')
    ax.scatter(Q, Iq_plot - background, s=30, marker='o', facecolors='none', edgecolors='darkred', label='-background')

    ax.legend(fontsize=16)
    ax.set_ylabel("$Iq$ (cm$^{-1}$)", fontsize=16)
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.minorticks_on()
    ax.tick_params(which="both", direction="in", labelsize=16)
    ax.tick_params(bottom=True, top=True, left=True, right=True, which="both")
    ax.set_xlabel("$q$ (Å$^{-1}$)", fontsize=16)
    # self.ax.figure.set_size_inches(8, 5)
    # Make sure everything fits inside the canvas
    fig.tight_layout()
    return fig


@st.cache_data
def predict(Q, Iq, dI, dQ, background, solvent_sld, ml_model_name, qmin, qmax):

    #truncate data to index range
    Iq_pred = numpy.where(Q <= qmin, Iq[Q <= qmin][-1], Iq)
    Iq_pred = numpy.where(Q >= qmax, Iq[Q >= qmax][0], Iq_pred)


    Iq_pred = Iq_pred - background
    Iq_pred = numpy.log10(numpy.abs(Iq_pred))

    # interpolation of SANS data to hardcoded grid
    qmin = 0.01
    qmax = 0.8
    numpoints = int((numpy.log10(qmax) - numpy.log10(qmin)) * 60)
    qvec = numpy.logspace(numpy.log10(qmin), numpy.log10(qmax), num=numpoints, endpoint=True)
    qvec = qvec[:105]

    intensity = numpy.interp(qvec, Q, Iq_pred)
    intensity = intensity[numpy.newaxis, :]
    intensity = tf.convert_to_tensor(intensity, dtype=tf.float32)

    sup = numpy.array([background, solvent_sld]).astype('float32')
    sup = sup[numpy.newaxis, :]

    y_pred = ml_model.predict([intensity, sup])

    tb_output = ["---Classification---"]
    for i, model in enumerate(sans_models):
        pstr = f'{y_pred[-1][0][i]:.2f}' + ' ' + model
        tb_output.append(pstr)
    tb_output.append("")

    tb_output.append("---Regression---")
    for i in range(len(y_pred) - 1):
        pstr = 'Model: ' + sans_models[i]
        tb_output.append(pstr)
        for j in range(len(par_names[i])):
            parname = par_names[i][j]
            if 'sld' in parname:
                correction = 0.1
            else:
                correction = 1
            pstr = parname + ' ' + f'{y_pred[i][0][j] * correction:.4f}'
            tb_output.append(pstr)
        tb_output.append("")

    return tb_output


# -------- GUI ------------------
st.write("""
# SANS ML Widget
""")

col1, col2 = st.columns([2,1])

# -------- File Dialog
uploaded_file = col1.file_uploader("Choose a SANS file")
if uploaded_file is not None:
    Q, Iq, dI, dQ, tb_output, uploaded_file = load_SANS_data(uploaded_file)
    (qmin, qmax) = col1.select_slider('Selet Q-range', options=Q, value=(float(Q[0]), float(Q[-1])))
    solvent_sld = col1.number_input('Solvent SLD', format='%f', step=0.1, value=6.4)
    # ------- Background number input with Auto Button
    col1.text('Background')
    col3, col4 = col1.columns([5,1])
    background = col3.number_input('Background', format='%e', step=0.1, key='background', label_visibility='collapsed')
    col4.button('Auto', on_click=update_background_input_auto, args=[Q, Iq, dI, dQ, qmin, qmax])
    # -------- File Plot
    col1.pyplot(plot_SANS(Q, Iq, dI, dQ, background, qmin, qmax))

# -------- ML model loader
model_list = os.listdir('ml_models')
ml_model_name = col2.selectbox("ML model", model_list)
sans_models, par_names, ml_model = load_ml_model(ml_model_name)

if uploaded_file:
    tb_output = predict(Q, Iq, dI, dQ, background, solvent_sld, ml_model_name, qmin, qmax)
tout = ""
for element in tb_output:
    tout += element + '\n'

col2.text(tout)
st.divider()


