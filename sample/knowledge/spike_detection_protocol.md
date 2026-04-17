# Spike Detection Protocol

## Threshold Criteria

Action potentials in extracellular recordings must be detected using a
threshold of **3 to 5 standard deviations** below the baseline mean.
Values less than 3σ produce an excessive false-positive rate from
thermal noise; values above 5σ miss low-amplitude units.

The recommended default is **4σ**, which balances sensitivity with
precision for single-unit recordings from cortical tissue.

> Extracellular spikes are predominantly **negative-going** because the
> extracellular space is the reference. Detection logic must compare
> against a negative threshold, not a positive one.

## Refractory Period

After a spike is detected, the next detection must be suppressed for
**at least 1 millisecond**. Biologically, no neuron can fire two action
potentials within its absolute refractory period. Detections within 1 ms
of each other are artifacts of the thresholding algorithm and must be
collapsed.

## Spike Sorting Window

When cutting waveforms for downstream sorting, use a symmetric window of
**1 to 1.5 milliseconds** centered on the threshold-crossing sample. At
a 32 kHz sampling rate, this corresponds to roughly 32 to 48 samples.

Windows cut too narrow lose the repolarization phase; windows cut too
wide include noise between spikes.

## Firing Rate Bounds

Physiologically plausible firing rates for cortical pyramidal neurons
range from **0.1 Hz to 50 Hz** under normal conditions. Rates above
200 Hz almost always indicate contamination from a nearby unit or a
multi-unit cluster that has not been properly isolated.
