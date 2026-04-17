# EEG Acquisition Guidelines

## Sampling Rate Requirements

EEG signals must be sampled at a minimum of **256 Hz** to capture the full
bandwidth of physiological activity (delta through gamma) without aliasing.
For studies targeting high-gamma (>60 Hz) or single-unit activity, use
1000 Hz or higher.

A signal digitized below 256 Hz cannot be reliably band-pass filtered at
40 Hz because the Nyquist frequency falls too close to the passband edge.
Analyses relying on frequencies above half the sampling rate are invalid.

## Electrode Impedance

Electrode-scalp impedance must remain below **10 kΩ** throughout the
recording session. Higher impedance values introduce thermal noise that
obscures cortical signals, particularly in the beta and gamma ranges.

## Reference Scheme

Always apply a consistent reference. Common choices are:

- **Linked mastoids** — symmetric, minimal bias for midline analyses.
- **Average reference** — appropriate when dense electrode montages
  (64+ channels) are used.
- **REST** — computational reference-free transformation for source
  localization studies.

Mixing reference schemes across subjects in a group analysis is invalid.

## Mains Interference

Recordings conducted without a Faraday cage must apply a notch filter at
**60 Hz** (North America) or **50 Hz** (Europe/Asia) before any further
processing. A 1 Hz wide band-stop filter is sufficient for typical
recording environments.
