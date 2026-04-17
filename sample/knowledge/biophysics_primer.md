# Biophysics Primer

## The Action Potential

A neuron's action potential is a brief (~1 ms), stereotyped depolarization
that propagates along the axon. From the extracellular space it appears
as a sharp **negative deflection** of roughly 50 to 500 microvolts. The
amplitude depends on the distance between the neuron and the recording
electrode and on the geometry of the cell.

## Absolute Refractory Period

Immediately after firing, a neuron is physically unable to fire again for
about **1 to 2 milliseconds**. This is the absolute refractory period,
caused by inactivation of voltage-gated sodium channels.

Any spike-detection algorithm that reports two detections within this
window has failed — the second detection is always an artifact.

## EEG vs Extracellular Recording

EEG reflects the **summed synaptic activity** of large populations of
cortical pyramidal neurons, low-pass-filtered by the skull. Individual
action potentials are invisible in EEG because their high-frequency
content is attenuated by the tissue.

Extracellular recording with a fine electrode placed near the soma
captures the action potentials of nearby cells directly. The two signals
live in different frequency bands:

- **EEG**: 0.5 – 40 Hz is dominant.
- **Extracellular spikes**: 300 – 5000 Hz is dominant.

A recording system that hopes to analyze both must sample at 10 kHz or
higher and apply separate filters to each band.

## Units and Scales

| Quantity            | Typical scale |
|---------------------|---------------|
| EEG amplitude       | 1 – 100 μV    |
| Spike amplitude     | 50 – 500 μV   |
| Local field potential | 0.1 – 10 mV |
| EOG (blinks)        | 50 – 500 μV   |

All voltages are reported relative to the chosen reference electrode.
