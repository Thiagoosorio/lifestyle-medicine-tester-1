"""Aggregation primitives for both Spec A and Spec B.

Both specs share common.weighted_geomean and common.normalise_for_geomean.
spec_a and spec_b are kept as separate modules with identical signatures so
they remain swappable -- if a future methodology revision diverges them at
organ level, only the spec_b module's organ function changes.
"""
