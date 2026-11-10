"""EPC_T: a test-label-free operator preserving raw event classifications.

This file contains no original station data, model predictions, or row IDs.
It can be executed standalone with NumPy to verify the exact invariant.
"""
from __future__ import annotations
import numpy as np


def event_preserving_correction(raw_rain, corrected_rain, threshold_mm):
    raw = np.asarray(raw_rain, dtype=float)
    corrected = np.asarray(corrected_rain, dtype=float)
    threshold = float(threshold_mm)
    if threshold <= 0 or not np.isfinite(threshold):
        raise ValueError("threshold_mm must be finite and positive")
    if raw.shape != corrected.shape:
        raise ValueError("raw and corrected must have matching shapes")
    if not np.isfinite(raw).all() or not np.isfinite(corrected).all() or (raw < 0).any():
        raise ValueError("Input rain must be finite; raw rainfall must be nonnegative")
    below = np.nextafter(threshold, 0.0)
    return np.where(raw >= threshold, raw,
                    np.minimum(np.maximum(corrected, 0.0), below))


def _selftest():
    rng = np.random.default_rng(4349)
    raw = rng.gamma(shape=1.2, scale=16, size=30000)
    model = np.maximum(0, raw * rng.uniform(0, 1.8, len(raw)) + rng.normal(0, 6, len(raw)))
    for threshold in (1, 10, 20, 50):
        epc = event_preserving_correction(raw, model, threshold)
        for tested_event_threshold in (threshold, max(threshold, 20), max(threshold, 50)):
            assert np.array_equal(epc >= tested_event_threshold,
                                  raw >= tested_event_threshold)
        assert np.all(epc >= 0)
        assert np.array_equal(epc[raw >= threshold], raw[raw >= threshold])
    print("PASS: exact raw-event mask invariance for four fixed thresholds")


if __name__ == "__main__":
    _selftest()
