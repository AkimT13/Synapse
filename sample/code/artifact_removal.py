"""Remove non-neural artifacts from EEG recordings."""
from __future__ import annotations

import numpy as np


BLINK_VOLTAGE_THRESHOLD_UV = 100.0
MUSCLE_HIGH_FREQUENCY_CUTOFF_HZ = 30.0


def reject_blink_epochs(
    epochs: np.ndarray,
    threshold_microvolts: float = BLINK_VOLTAGE_THRESHOLD_UV,
) -> np.ndarray:
    """Drop epochs whose peak-to-peak voltage exceeds the blink threshold.

    Eye blinks typically produce deflections above 100 microvolts on
    frontal channels. Epochs exceeding this threshold on any channel are
    removed entirely rather than interpolated.
    """
    peak_to_peak = np.max(epochs, axis=-1) - np.min(epochs, axis=-1)
    keep = np.all(peak_to_peak < threshold_microvolts, axis=-1)
    return epochs[keep]


def regress_out_eog(
    eeg_signal: np.ndarray,
    eog_signal: np.ndarray,
) -> np.ndarray:
    """Remove eye-movement artifact via linear regression against EOG."""
    covariance = np.dot(eeg_signal, eog_signal)
    eog_variance = np.dot(eog_signal, eog_signal)
    if eog_variance == 0:
        return eeg_signal
    beta = covariance / eog_variance
    return eeg_signal - beta * eog_signal


def flag_muscle_contamination(
    signal: np.ndarray,
    sampling_rate: float,
    threshold_ratio: float = 0.5,
) -> bool:
    """Return True if high-frequency power dominates the signal.

    Muscle contamination manifests as broadband noise above 30 Hz. If the
    fraction of total power in this band exceeds threshold_ratio the epoch
    should be excluded from further analysis.
    """
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sampling_rate)
    power = np.abs(np.fft.rfft(signal)) ** 2
    high_mask = freqs >= MUSCLE_HIGH_FREQUENCY_CUTOFF_HZ
    total = np.sum(power)
    if total == 0:
        return False
    return (np.sum(power[high_mask]) / total) > threshold_ratio
