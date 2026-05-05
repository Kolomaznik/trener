"""Backwards-compatible re-export of calculate_muscle_load.

The canonical implementation now lives in ``app.services.fitness_math``.
Import from there directly for new code.
"""

from app.services.fitness_math import calculate_muscle_load

__all__ = ["calculate_muscle_load"]
