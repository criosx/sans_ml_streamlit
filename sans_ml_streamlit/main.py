import matplotlib.pyplot as plt
import numpy
import os
import streamlit as st
from sasmodels.data import load_data


def auto_background():
    if Iq is None:
        return

    # average of last n points that is within the error bar of the n-1 th point
    background = None
    for i in range(-5, -30, -1):
        background_new = numpy.average(Iq[i:])
        if numpy.abs(Iq[i - 1] - background_new) > 2 * dI[i - 1]:
            break
        background = background_new

    return background

def plot_SANS():
    # Plot SANS curves
    fig, ax = plt.subplots()
    # Clear whatever was in the plot before
    ax.clear()
    # Plot data, add labels, change colors, ...
    ax.errorbar(Q, Iq, dI, ls='none', color='deepskyblue')
    ax.scatter(Q, Iq, s=30, marker='o', facecolors='none', edgecolors='deepskyblue', label='orignal')
    ax.errorbar(Q, Iq - background, dI, ls='none', color='darkred')
    ax.scatter(Q, Iq - background, s=30, marker='o', facecolors='none', edgecolors='darkred', label='-background')

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

# initialize variables
ds = None
Q = None
Iq = None
dI = None
dQ = None

tb_output = 'Select a File'

if not os.path.isdir('temp'):
    os.makedirs('temp')

st.write("""
# SANS ML Widget
""")

col1, col2 = st.columns(2)

uploaded_file = col1.file_uploader("Choose a SANS file")
if uploaded_file is not None:
    with open(os.path.join("temp", uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())
    ds = load_data(os.path.join("temp", uploaded_file.name))
    Q = ds.x
    Iq = ds.y
    dI = ds.dy
    dQ = ds.dx

solvent_sld = col1.number_input('Solvent SLD', format='%f', step=0.1, value=6.4)

col3, col4 = col1.columns(2)
background = col3.number_input('Background', format='%e', step=0.1, value=0.0)
if col4.button('Auto'):
    background = auto_background()

if ds is not None:
    col1.pyplot(plot_SANS())

col2.text(tb_output)

st.divider()
