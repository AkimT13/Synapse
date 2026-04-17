"""Core filtering and frequency-domain analysis for EEG signals."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt


NYQUIST_SAFETY_MARGIN = 0.9


def bandpass_filter(
    signal: np.ndarray,
    sampling_rate: float,
    low_hz: float,
    high_hz: float,
    order: int = 4,
) -> np.ndarray:
    """Apply a zero-phase Butterworth bandpass filter to a raw EEG signal.

    Frequencies outside [low_hz, high_hz] are attenuated. Uses filtfilt so
    that no phase distortion is introduced into the timing of spikes or
    evoked potentials.
    """
    nyquist = sampling_rate / 2.0
    if high_hz >= nyquist * NYQUIST_SAFETY_MARGIN:
        raise ValueError(
            f"high_hz={high_hz} exceeds Nyquist safety margin at {sampling_rate} Hz"
        )
    low = low_hz / nyquist
    high = high_hz / nyquist
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, signal)


def notch_filter(signal: np.ndarray, sampling_rate: float, mains_hz: float = 60.0) -> np.ndarray:
    """Remove mains electrical interference (typically 60 Hz in North America)."""
    nyquist = sampling_rate / 2.0
    quality = 30.0
    b, a = butter(2, [(mains_hz - 1) / nyquist, (mains_hz + 1) / nyquist], btype="bandstop")
    return filtfilt(b, a, signal)


def compute_power_spectrum(signal: np.ndarray, sampling_rate: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequencies_hz, power) using a periodogram."""
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    power = (np.abs(fft_vals) ** 2) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate)
    return freqs, power


def band_power(
    signal: np.ndarray,
    sampling_rate: float,
    low_hz: float,
    high_hz: float,
) -> float:
    """Total power in a frequency band, useful for alpha/beta/gamma quantification."""
    freqs, power = compute_power_spectrum(signal, sampling_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    return float(np.sum(power[mask]))
