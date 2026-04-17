# Artifact Handling

## Eye Blinks

Eye blinks produce large slow deflections, typically **100–250 microvolts
peak-to-peak** on frontal channels. Any epoch where peak-to-peak voltage
exceeds **100 μV** on any channel must be excluded from analysis, or the
blink must be regressed out using a simultaneously recorded EOG channel.

Interpolating across a blink without reference to EOG introduces
systematic error into the affected channels and is not acceptable for
ERP studies.

## Eye Movements

Horizontal eye movements are best handled by regression against the EOG
signal. The regression coefficient is:

    β = cov(EEG, EOG) / var(EOG)

with the corrected EEG computed as `EEG - β * EOG`. This is a per-trial
computation; do not estimate a single β across an entire session because
electrode drift changes the coupling.

## Muscle Activity

EMG contamination appears as broadband activity above **30 Hz**. A useful
diagnostic is the ratio of power above 30 Hz to total power: epochs
where this ratio exceeds **0.5** are almost certainly muscle-dominated
and should be flagged for exclusion.

Simple high-pass filtering does **not** remove muscle artifact because
the contamination is broadband; rejection is the correct treatment.

## Movement Artifacts

Sudden movement or electrode shift creates step discontinuities or large
DC offsets. These are best identified visually during quality control,
but an automated heuristic is to flag any sample where the derivative
exceeds **50 μV per sample** at a 1 kHz sampling rate.
