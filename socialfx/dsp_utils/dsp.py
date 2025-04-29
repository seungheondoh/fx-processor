import numpy as np
import scipy.signal
from functools import partial
from typing import Dict, List, Optional, Union, Tuple

def biquad(gain_db, freq, q, sample_rate, filter_type):
    """
    Calculate biquad filter coefficients.

    Args:
        gain_db (float): Filter gain in dB
        freq (float): Center/cutoff frequency in Hz
        q (float): Q factor
        sample_rate (float): Audio sample rate
        filter_type (str): Filter type. Options: "peaking", "low_pass"

    Returns:
        b (np.ndarray): Numerator coefficients [b0, b1, b2]
        a (np.ndarray): Denominator coefficients [1, a1, a2]
    """
    if filter_type == "peaking":
        # Convert gain from dB to linear
        A = 10 ** (gain_db / 40.0)
        w0 = 2 * np.pi * freq / sample_rate
        alpha = np.sin(w0) / (2 * q)

        # Peaking EQ filter coefficients
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A

    elif filter_type == "low_pass":
        w0 = 2 * np.pi * freq / sample_rate
        alpha = np.sin(w0) / (2 * q)

        # Lowpass filter coefficients
        b0 = (1 - np.cos(w0)) / 2
        b1 = 1 - np.cos(w0)
        b2 = (1 - np.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha

    # Normalize by a0
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])

    return b, a

def socialfx_eq(
    x: np.ndarray,
    sample_rate: float,
    band0_gain_db: float,
    band1_gain_db: float,
    band2_gain_db: float,
    band3_gain_db: float,
    band4_gain_db: float,
    band5_gain_db: float,
    band6_gain_db: float,
    band7_gain_db: float,
    band8_gain_db: float,
    band9_gain_db: float,
    band10_gain_db: float,
    band11_gain_db: float,
    band12_gain_db: float,
    band13_gain_db: float,
    band14_gain_db: float,
    band15_gain_db: float,
    band16_gain_db: float,
    band17_gain_db: float,
    band18_gain_db: float,
    band19_gain_db: float,
    band20_gain_db: float,
    band21_gain_db: float,
    band22_gain_db: float,
    band23_gain_db: float,
    band24_gain_db: float,
    band25_gain_db: float,
    band26_gain_db: float,
    band27_gain_db: float,
    band28_gain_db: float,
    band29_gain_db: float,
    band30_gain_db: float,
    band31_gain_db: float,
    band32_gain_db: float,
    band33_gain_db: float,
    band34_gain_db: float,
    band35_gain_db: float,
    band36_gain_db: float,
    band37_gain_db: float,
    band38_gain_db: float,
    band39_gain_db: float,
    q_factor: Optional[float] = None,
    range_scale: Optional[float] = None,
    normalize: Optional[bool] = False,
):
    """40-band Graphic Equalizer based on the JavaScript Equalizer implementation.

    This is a NumPy implementation of a 40-band graphic equalizer with center frequencies
    logarithmically spaced from 20 Hz to 20 kHz, directly matching the JavaScript implementation.
    Each band is implemented as a peaking filter and applied in series, just like in equalizer.js.

    JS equivalent: equalizer.js

    Key mappings from JavaScript:
    - Center frequencies are identical to those in equalizer.js line 29
    - Q factor default of 4.31 matches equalizer.js line 31
    - Range scale of 5.0 matches the multiplier in equalizer.js line 90

    Args:
        x (np.ndarray): Time domain tensor with shape (channels, samples)
        sample_rate (float): Audio sample rate
        band0_gain_db (float): Band 1 filter gain in dB
        band1_gain_db (float): Band 2 filter gain in dB
        ...
        band39_gain_db (float): Band 40 filter gain in dB
        q_factor (float, optional): Q-factor for all bands. Defaults to 4.31.
        range_scale (float, optional): Overall gain scaling factor. Defaults to 1.0.

    Returns:
        y (np.ndarray): Equalized signal. Shape (channels, samples).
    """
    chs, seq_len = x.shape

    # Set default values if not provided, matching JavaScript defaults
    if q_factor is None:
        q_factor = 4.31  # From equalizer.js line 31

    if range_scale is None:
        range_scale = 1.0

    # Define center frequencies (exact match from equalizer.js line 29)
    center_freqs = np.array([
        20, 50, 83, 120, 161, 208, 259, 318, 383, 455,
        537, 628, 729, 843, 971, 1114, 1273, 1452, 1652, 1875,
        2126, 2406, 2719, 3070, 3462, 3901, 4392, 4941, 5556, 6244,
        7014, 7875, 8839, 9917, 11124, 12474, 13984, 15675, 17566, 19682
    ])

    # Stack all gain parameters into an array
    band_gains = np.array([
        band0_gain_db, band1_gain_db, band2_gain_db, band3_gain_db, band4_gain_db,
        band5_gain_db, band6_gain_db, band7_gain_db, band8_gain_db, band9_gain_db,
        band10_gain_db, band11_gain_db, band12_gain_db, band13_gain_db, band14_gain_db,
        band15_gain_db, band16_gain_db, band17_gain_db, band18_gain_db, band19_gain_db,
        band20_gain_db, band21_gain_db, band22_gain_db, band23_gain_db, band24_gain_db,
        band25_gain_db, band26_gain_db, band27_gain_db, band28_gain_db, band29_gain_db,
        band30_gain_db, band31_gain_db, band32_gain_db, band33_gain_db, band34_gain_db,
        band35_gain_db, band36_gain_db, band37_gain_db, band38_gain_db, band39_gain_db
    ])
    # Check if normalization is needed (similar to equalizer.js)
    # Normalize the curve if requested (matching equalizer.js lines 74-91)
    if normalize:
        # Find min and max values for normalization
        min_val = np.min(band_gains)
        max_val = np.max(band_gains)
        # Apply normalization if there's a range to normalize
        if max_val != min_val:
            # Normalize to range [-1, 1] exactly as in equalizer.js
            normalized_gains = np.zeros_like(band_gains)
            for i in range(len(band_gains)):
                # This matches the JS implementation's normalization formula:
                # dat = value[i] - min_el
                # dat = dat / (max_el - min_el) * 2
                # curve.push(dat - 1)
                normalized_gains[i] = (band_gains[i] - min_val) / (max_val - min_val) * 2 - 1
            band_gains = normalized_gains
    # Apply range scaling to all bands (matching equalizer.js line 90)
    # In JS: gain = range * 5 * curve[i]
    band_gains = band_gains * range_scale * 5.0
    # Apply all filters in sequence (matching JavaScript chain of filters)
    x_out = x.copy()
    # Process each channel
    for ch in range(chs):
        channel_data = x_out[ch]

        # Apply each band filter in sequence
        for i in range(40):
            # Generate filter coefficients for this band
            b, a = biquad(
                band_gains[i],
                center_freqs[i],
                q_factor,
                sample_rate,
                "peaking"
            )

            # Apply filter to the channel
            channel_data = scipy.signal.lfilter(b, a, channel_data)

        x_out[ch] = channel_data

    return x_out


def socialfx_reverb(
    x: np.ndarray,
    sample_rate: float,
    delay_time: float,  # d
    decay: float,       # g
    stereo_spread: float,  # m
    cutoff_freq: float,  # f
    wet_gain: float,    # E
    wet_dry: float = 1.0,     # wetdry
):
    """Parametric reverberator based on the JavaScript Reverb implementation.

    This is a NumPy implementation of the reverberator described in
    "A Digital Reverberator Controlled through Measures of the Reverberation" by Rafii and Pardo,
    directly matching the JavaScript implementation in reverb.js.

    JS equivalent: reverb.js

    Key mappings from JavaScript:
    - Parameter names match reverb.js: d→delay_time, g→decay, m→stereo_spread,
      f→cutoff_freq, E→wet_gain, wetdry→wet_dry
    - Constants match reverb.js: allpass_gain=0.1, min_delay=0.01
    - Comb filter structure matches reverb.js lines 40-48
    - Stereo allpass structure matches reverb.js lines 49-61
    - Wet/dry mixing follows reverb.js lines 82-96

    Args:
        x (np.ndarray): Input audio array with shape (channels, samples)
        sample_rate (float): Audio sample rate
        delay_time (float): Base delay time in seconds (d). Range: 0.01 to 0.1
        decay (float): Decay coefficient (g). Range: 0 to 1
        stereo_spread (float): Stereo width parameter (m). Range: -0.012 to 0.012
        cutoff_freq (float): Lowpass filter cutoff frequency (f). Range: 0 to sample_rate/2
        wet_gain (float): Wet signal gain (E). Range: 0 to 1
        wet_dry (float): Wet/dry mix ratio (wetdry). Range: 0 to 1

    Returns:
        np.ndarray: Reverberated signal. Shape (channels, samples)
    """
    chs, seq_len = x.shape

    # Convert to mono if input is multichannel
    if chs > 1:
        x_mono = np.mean(x, axis=0, keepdims=True)
    else:
        x_mono = x.copy()

    # Constants from JavaScript implementation
    allpass_gain = 0.1  # Fixed allpass gain from reverb.js line 9
    min_delay = 0.01    # Minimum delay from reverb.js line 10

    # Calculate reverberation time (matching RT60 calculation in reverb.js)
    rt60 = delay_time * np.log(0.001) / np.log(decay)

    # Create parallel comb filters (6 in total as in JS implementation, lines 40-48)
    comb_outputs = []
    for i in range(6):
        # Calculate delay and gain for each comb filter (matching reverb.js lines 40-48)
        comb_delay = delay_time * (15 - i) / 15
        comb_gain = np.power(0.001, comb_delay / rt60)

        # Convert delay to samples
        comb_delay_samples = int(round(comb_delay * sample_rate))

        # Apply comb filter
        # Simulate recursive IIR filter with feedback
        comb_out = np.zeros_like(x_mono)

        # Efficiently implement comb filter
        for t in range(seq_len):
            if t < comb_delay_samples:
                comb_out[0, t] = x_mono[0, t]
            else:
                # Get previous output at delay point
                prev_out = comb_out[0, t - comb_delay_samples]
                comb_out[0, t] = x_mono[0, t] + comb_gain * prev_out

        comb_outputs.append(comb_out)

    # Sum comb filter outputs (matching reverb.js combExit)
    comb_sum = np.sum(comb_outputs, axis=0)

    # Create stereo allpass filters (matching reverb.js lines 49-61)
    da = min_delay + 0.006  # Matches the da calculation in reverb.js
    left_delay_time = da + stereo_spread / 2
    right_delay_time = da - stereo_spread / 2

    # Convert allpass delay times to samples
    left_delay_samples = int(round(left_delay_time * sample_rate))
    right_delay_samples = int(round(right_delay_time * sample_rate))

    # Apply allpass filters for left and right channels
    # This implements the allpass filter formula from reverb.js: y[n] = -g*x[n] + x[n-d] + g*y[n-d]
    left_out = np.zeros_like(comb_sum)
    right_out = np.zeros_like(comb_sum)

    for t in range(seq_len):
        # Left channel allpass
        if t < left_delay_samples:
            left_out[0, t] = -allpass_gain * comb_sum[0, t]
        else:
            delayed_in = comb_sum[0, t - left_delay_samples]
            delayed_out = left_out[0, t - left_delay_samples]
            left_out[0, t] = -allpass_gain * comb_sum[0, t] + delayed_in + allpass_gain * delayed_out

        # Right channel allpass
        if t < right_delay_samples:
            right_out[0, t] = -allpass_gain * comb_sum[0, t]
        else:
            delayed_in = comb_sum[0, t - right_delay_samples]
            delayed_out = right_out[0, t - right_delay_samples]
            right_out[0, t] = -allpass_gain * comb_sum[0, t] + delayed_in + allpass_gain * delayed_out

    # Apply lowpass filter to both channels (matching reverb.js lines 62-69)
    # Create lowpass filter using biquad
    b_lp, a_lp = biquad(
        0.0,  # zero gain for lowpass
        cutoff_freq,
        0.707,  # Q factor for Butterworth response
        sample_rate,
        "low_pass"
    )

    # Apply lowpass filter to both channels
    left_filt = scipy.signal.lfilter(b_lp, a_lp, left_out[0])
    right_filt = scipy.signal.lfilter(b_lp, a_lp, right_out[0])

    # Create stereo output
    left_filt = left_filt.reshape(1, -1)
    right_filt = right_filt.reshape(1, -1)
    wet_output = np.vstack([left_filt, right_filt])

    # If input was mono, duplicate mono to stereo
    if chs == 1:
        dry_output = np.vstack([x, x])
    else:
        # If input was already stereo, use as is
        dry_output = x

    # Apply gain adjustments as in JS implementation (matching reverb.js lines 82-85)
    total_gain = wet_gain + 1
    g1 = 1 / total_gain

    gain_clean = np.cos((1 - g1) * 0.125 * np.pi)
    gain_wet = np.cos(g1 * 0.375 * np.pi)
    gain_scale = 0.5 * 0.8 / (gain_clean + gain_wet)

    # Apply wet/dry mix (matching reverb.js lines 93-96)
    wet_level = np.cos((1 - wet_dry) * 0.5 * np.pi)
    dry_level = np.cos(wet_dry * 0.5 * np.pi)

    # Final output mix (matching the structure in reverb.js)
    output = dry_level * dry_output + wet_level * gain_scale * (gain_clean * x_mono + gain_wet * wet_output)

    return output


def socialfx_compressor(
    x: np.ndarray,
    sample_rate: float,
    threshold_db: float,
    ratio: float,
    attack_ms: float,
    release_ms: float,
    knee_db: float,
    makeup_gain_db: float = 0.0,
    eps: float = 1e-8,
):
    """Dynamic range compressor.
    Args:
        x (np.ndarray): Input audio array with shape (channels, samples)
        sample_rate (float): Audio sample rate
        threshold_db (float): Compression threshold in dB
        ratio (float): Compression ratio
        attack_ms (float): Attack time in milliseconds
        release_ms (float): Release time in milliseconds
        knee_db (float): Knee width in dB
        makeup_gain_db (float): Makeup gain in dB
        eps (float, optional): Small epsilon value to avoid log(0). Defaults to 1e-8.
    Returns:
        y (np.ndarray): Compressed signal with shape (channels, samples).
    """
    chs, seq_len = x.shape

    # If multiple channels are present, create sum side-chain
    if chs > 1:
        x_side = np.sum(x, axis=0, keepdims=True)
    else:
        x_side = x.copy()

    # Compute time constants
    normalized_attack_time = sample_rate * (attack_ms / 1e3)
    normalized_release_time = sample_rate * (release_ms / 1e3)
    constant = 9.0
    alpha_A = np.exp(-np.log(constant) / normalized_attack_time)
    alpha_R = np.exp(-np.log(constant) / normalized_release_time)

    # Compute energy in dB
    x_db = 20 * np.log10(np.abs(x_side).clip(eps))

    # Static characteristic with soft knee
    x_sc = x_db.copy()

    # When signal is at the threshold engage knee
    idx1 = x_db >= (threshold_db - (knee_db / 2))
    idx2 = x_db <= (threshold_db + (knee_db / 2))
    idx = np.logical_and(idx1, idx2)
    x_sc_below = x_db + ((1 / ratio) - 1) * (
        (x_db - threshold_db + (knee_db / 2)) ** 2
    ) / (2 * knee_db)
    x_sc[idx] = x_sc_below[idx]

    # When signal is above threshold linear response
    idx = x_db > (threshold_db + (knee_db / 2))
    x_sc_above = threshold_db + ((x_db - threshold_db) / ratio)
    x_sc[idx] = x_sc_above[idx]

    # Output of gain computer
    g_c = x_sc - x_db

    # Implementation of attack/release ballistics
    # Using both attack and release time constants for more accurate behavior
    g_c_smoothed = np.zeros_like(g_c)
    g_c_smoothed[0, 0] = g_c[0, 0]  # Initialize first sample

    # Apply attack/release filter sample by sample
    for t in range(1, seq_len):
        # Determine whether to use attack or release coefficient
        # If current gain reduction is more negative than previous, use attack (faster)
        # Otherwise use release (slower)
        if g_c[0, t] < g_c_smoothed[0, t-1]:
            alpha = alpha_A
        else:
            alpha = alpha_R

        # First-order IIR filter: y[n] = (1-alpha) * x[n] + alpha * y[n-1]
        g_c_smoothed[0, t] = (1 - alpha) * g_c[0, t] + alpha * g_c_smoothed[0, t-1]

    # Add makeup gain in dB
    g_s = g_c_smoothed + makeup_gain_db

    # Convert dB gains back to linear
    g_lin = 10 ** (g_s / 20.0)

    # Apply time-varying gain and makeup gain to all channels
    y = np.zeros_like(x)
    for ch in range(chs):
        y[ch] = x[ch] * g_lin[0]

    return y
