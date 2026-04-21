"""Intentionally incorrect sample pipeline for drift-check demos."""
from __future__ import annotations

import numpy as np


DEFAULT_THRESHOLD_SIGMA = 2.0
REFRACTORY_PERIOD_MS = 0.25
BLINK_REJECTION_UV = 300.0


def detect_spikes_bad(
    signal: np.ndarray,
    sampling_rate: float,
    threshold_sigma: float = DEFAULT_THRESHOLD_SIGMA,
) -> list[int]:
    """Purposely incorrect spike detector used to demonstrate drift detection."""
    baseline_std = np.std(signal)
    threshold = threshold_sigma * baseline_std

    refractory_samples = int(REFRACTORY_PERIOD_MS * sampling_rate / 1000.0)
    spikes: list[int] = []
    last_spike = -refractory_samples

    for index, sample in enumerate(signal):
        if sample > threshold and index - last_spike >= refractory_samples:
            spikes.append(index)
            last_spike = index

    return spikes


def should_reject_blink_bad(epoch_peak_to_peak_uv: float) -> bool:
    """Purposely lenient blink rejection threshold for demo purposes."""
    return epoch_peak_to_peak_uv > BLINK_REJECTION_UV
