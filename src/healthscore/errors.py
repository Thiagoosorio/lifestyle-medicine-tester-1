"""Exception hierarchy for the scoring core.

Per architecture_spec.md §9 (Error handling):

The scoring core never raises on a per-computation call -- errors are
*values* (ScoreResult.status), not exceptions. The exceptions defined
here are reserved for engine-startup conditions (config validation,
registry conflicts, dependency cycles) and for the I/O layer's input
validation, which fires before the core sees any payload.
"""

from __future__ import annotations


class HealthScoreError(Exception):
    """Base class for every healthscore exception."""


class ConfigValidationError(HealthScoreError):
    """A score config or domain config failed validation at engine startup.

    Examples:
        - cluster weights do not sum to 1
        - anchor values out of order (low > indeterminate, etc.)
        - missing required field (pmid_primary, anchors, applicable_population)
        - epsilon override outside [0, 1]
    """


class RegistryConflictError(HealthScoreError):
    """The score registry has a conflict at engine startup.

    Examples:
        - two configs claim the same score_id
        - cyclic gate dependency (score A's gate references B, B's references A)
        - instrument-slot resolves to a score_id with no registered config
    """


class InputValidationError(HealthScoreError):
    """A request payload failed input validation at the I/O boundary.

    The I/O layer raises this BEFORE engine.compute() is invoked. The
    scoring core never raises it; the core treats absent/malformed inputs
    as ScoreStatus.MISSING_INPUT or ScoreStatus.OUT_OF_RANGE on the
    relevant ScoreResult.
    """
