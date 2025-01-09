import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Use the entire browser width
st.set_page_config(layout="wide")

# Initialize offset in session_state if not set
if "x_offset" not in st.session_state:
    st.session_state["x_offset"] = 0.0

# Two main columns: left for inputs, right for plot
col_inputs, col_plot = st.columns([1, 4])

with col_inputs:
    st.title("Merged Sine Waves")

    # Number of Waves
    wave_count = st.number_input(
        "Number of Waves",
        min_value=1, max_value=10,
        value=3, step=1
    )

    # Collect wave parameters
    wave_params = []
    for i in range(wave_count):
        st.markdown(f"**Wave {i+1}**")
        
        amp_col, freq_col = st.columns(2)
        with amp_col:
            amp = st.number_input(
                f"Amplitude (Wave {i+1})",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                key=f"amplitude_{i}"
            )
        with freq_col:
            freq = st.number_input(
                f"Frequency (Wave {i+1})",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                key=f"frequency_{i}"
            )

        wave_params.append((amp, freq))

with col_plot:
    # Grab the current offset from session_state
    offset = st.session_state["x_offset"]

    # Create x-values (offset applied)
    x = np.linspace(0, 2 * np.pi, 1000) + offset

    # Prepare array for the merged wave
    y_merged = np.zeros_like(x)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    for i, (amp, freq) in enumerate(wave_params, start=1):
        y = amp * np.sin(freq * x)
        ax.plot(x, y, label=f"Wave {i}: A={amp}, f={freq}", alpha=0.4)
        y_merged += y

    # Merged wave in bold red
    ax.plot(x, y_merged, label="Merged Wave", color="red", linewidth=2)
    ax.set_xlabel("x")
    ax.set_ylabel("Amplitude")
    ax.set_title("Merged Sine Waves (Slider Below)")
    ax.legend(loc="upper right")

    st.pyplot(fig)

# Now place the slider *below* the plot
st.subheader("Offset Slider (Below the Plot)")
st.session_state["x_offset"] = st.slider(
    "X Offset",
    min_value=-10.0,
    max_value=10.0,
    value=st.session_state["x_offset"],
    step=0.1
)
