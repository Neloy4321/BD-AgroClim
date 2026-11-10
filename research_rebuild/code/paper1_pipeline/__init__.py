"""Reproducible CSV-only audit and station-withheld climate correction."""
from .core import Config, load_inputs, foundation, terrain_diagnostics
from .experiments import run_experiments, summarize_experiments
from .reporting import make_figures, reconstruct
