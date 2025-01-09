import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Use full browser width
st.set_page_config(layout="wide")

# Create two columns: left (for inputs), right (for plot)
col_inputs, col_plot = st.columns([1, 3])  # Adjust ratios as needed

with col_inputs:
    st.title("Sine Waves with Variable π-Multiplier")
    
    st.markdown(r"""
    Choose a **π-multiplier** below. For example: 
    - `2` → each wave uses $2\pi$, 
    - `3` → $3\pi$, 
    - `4` → $4\pi$, etc.

    We have four waves, each completing an integer multiple of cycles
    within $x \in [0, 64]$, but now controlled by your chosen π-multiplier.
    """)

    # Phase options
    phase_red_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]
    phase_green_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]
    phase_blue_options = [0, 1.57, 3.14, 4.72]
    phase_yellow_options = [0, 1.1, 1.6, 2.0, 3.14, 4.2, 4.7, 5.2]

    # User picks each phase
    alpha_red = st.selectbox("Phase α_red (64 sin)", phase_red_options, index=0)
    alpha_green = st.selectbox("Phase α_green (32 sin)", phase_green_options, index=0)
    alpha_blue = st.selectbox("Phase α_blue (16 sin)", phase_blue_options, index=0)
    alpha_yellow = st.selectbox("Phase α_yellow (8 sin)", phase_yellow_options, index=0)

    st.markdown("---")
    
    # Let the user pick the pi-multiplier
    pi_multiplier = st.slider(
        "π-Multiplier (e.g., 2 = 2π, 3 = 3π, etc.)",
        min_value=1,
        max_value=10,
        value=2,
        step=1
    )

    st.write(f"Current π-multiplier: **{pi_multiplier}** → effectively using **{pi_multiplier}π** in each term.")
    
with col_plot:
    # Define x from 0..64
    x = np.linspace(0, 64, 2000)

    # Build each wave using the chosen π-multiplier
    wave1 = 64 * np.sin(alpha_red    + pi_multiplier*np.pi*(x/64))
    wave2 = 32 * np.sin(alpha_green  + pi_multiplier*np.pi*(x/32))
    wave3 = 16 * np.sin(alpha_blue   + pi_multiplier*np.pi*(x/16))
    wave4 =  8 * np.sin(alpha_yellow + pi_multiplier*np.pi*(x/8))

    # Sum them up
    merged_wave = wave1 + wave2 + wave3 + wave4

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(x, wave1, label="64 sin(α_red + mπ·x/64)",   alpha=0.4, color="red")
    ax.plot(x, wave2, label="32 sin(α_green + mπ·x/32)", alpha=0.4, color="green")
    ax.plot(x, wave3, label="16 sin(α_blue + mπ·x/16)",  alpha=0.4, color="blue")
    ax.plot(x, wave4, label="8 sin(α_yellow + mπ·x/8)",  alpha=0.4, color="orange")

    ax.plot(x, merged_wave, label="Sum of all waves", color="magenta", linewidth=2)

    ax.set_xlabel("x (0 to 64)")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"Sine Waves with {pi_multiplier}π Factor")
    ax.legend(loc="upper right")

    st.pyplot(fig)
