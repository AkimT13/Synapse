# Digital Filtering Constraints for EEG

## Nyquist Rule

The highest frequency that can be reliably analyzed in a digital signal
is half the sampling rate — the **Nyquist frequency**. Any filter whose
upper cutoff approaches the Nyquist frequency must be used with caution;
as a rule of thumb, the upper cutoff should not exceed **90%** of the
Nyquist frequency to avoid aliasing and filter instability.

For a 256 Hz sampling rate the Nyquist is 128 Hz, so filter cutoffs
must not exceed roughly 115 Hz.

## Zero-Phase Filtering

For any analysis that depends on event timing — ERPs, spike-triggered
averages, phase coupling — filters must be applied in a **zero-phase
configuration** (e.g. `scipy.signal.filtfilt`). A conventional causal
filter introduces a group delay that shifts every event backward in time.

Zero-phase filters double the effective filter order, so the filter
specification should account for this when choosing order parameters.

## Typical Passbands

| Application         | Low (Hz) | High (Hz) |
|---------------------|----------|-----------|
| ERP analysis        | 0.1      | 30        |
| Alpha/beta activity | 0.5      | 40        |
| Gamma activity      | 30       | 90        |
| Spike extraction    | 300      | 5000      |

## Order Selection

Butterworth filter order should be between **2 and 8**. Higher orders
produce sharper roll-off but amplify transient artifacts at the signal
boundaries. Most physiological analyses are well served by order 4.

## Alpha Band

The alpha rhythm is defined as oscillatory activity between **8 and
13 Hz**, dominant in posterior channels during eyes-closed rest. Alpha
power is the standard proxy for cortical inhibition and drowsiness.
