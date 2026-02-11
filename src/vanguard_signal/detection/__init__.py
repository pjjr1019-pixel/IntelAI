"""
Anomaly Detection Engine — STL, Isolation Forest, CUSUM, Velocity, Correlation, and ensemble scoring.

This package is the analytical core of Vanguard Signal.  It takes
aggregated time-series data from the signal layer and produces
decomposed, explainable anomaly scores.

Sub-modules
-----------
base_detector         – Abstract interface for all detectors
stl_detector          – Seasonal-Trend Decomposition using LOESS
iforest_detector      – Isolation Forest for point anomaly detection
cusum_detector        – Cumulative Sum Control Chart for mean-shift detection
velocity_detector     – Rate-of-change (derivative) anomaly detection
correlation_detector  – Cross-keyword co-movement detection
ensemble              – Weighted combination of all four per-entity detectors
aggregator            – Converts NormalizedEvents into SignalTimeSeries rows
pipeline              – End-to-end orchestrator: aggregate → detect → score → alert
evidence              – Auto-generates evidence chains and alert summaries
"""
