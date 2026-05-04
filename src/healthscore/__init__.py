"""Organ-level composite scoring core (architecture_spec.md).

Phase 0 surface: enums, errors, types, normalise, aggregate primitives.
The core is a pure function `(inputs, config) -> AggregationOutput`. I/O,
persistence, networking, time-of-day, and randomness (other than what is
passed in explicitly) are forbidden inside the core. This is what makes
the core Sobol-perturbable without modification (see harness seam in
later phases).
"""

__version__ = "0.1.0-phase0"
