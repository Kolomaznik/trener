"""Add level_coefficient and height_multiplier to all existing exercise documents.

level_coefficient: fraction of body weight moved (exercise difficulty).
height_multiplier: range of motion expressed as a fraction of body height.
"""

from mongodb_migrations.base import BaseMigration

# Per-exercise overrides (id → {level_coefficient, height_multiplier}).
# Exercises not listed here get sensible family-level defaults defined below.
_EXERCISE_OVERRIDES: dict[str, dict] = {
    # ── Kliky (Push-ups) ──────────────────────────────────────────────────────
    "pushups_level_1": {"level_coefficient": 0.20, "height_multiplier": 0.40},
    "pushups_level_2": {"level_coefficient": 0.35, "height_multiplier": 0.40},
    "pushups_level_3": {"level_coefficient": 0.49, "height_multiplier": 0.40},
    "pushups_level_4": {"level_coefficient": 0.54, "height_multiplier": 0.40},
    "pushups_level_5": {"level_coefficient": 0.64, "height_multiplier": 0.40},
    "pushups_level_6": {"level_coefficient": 0.68, "height_multiplier": 0.40},
    "pushups_level_7": {"level_coefficient": 0.72, "height_multiplier": 0.40},
    "pushups_level_8": {"level_coefficient": 0.78, "height_multiplier": 0.40},
    "pushups_level_9": {"level_coefficient": 0.84, "height_multiplier": 0.40},
    "pushups_level_10": {"level_coefficient": 0.90, "height_multiplier": 0.40},
    # ── Dřepy (Squats) ────────────────────────────────────────────────────────
    "squats_level_1": {"level_coefficient": 0.25, "height_multiplier": 0.50},
    "squats_level_2": {"level_coefficient": 0.40, "height_multiplier": 0.50},
    "squats_level_3": {"level_coefficient": 0.55, "height_multiplier": 0.50},
    "squats_level_4": {"level_coefficient": 0.65, "height_multiplier": 0.50},
    "squats_level_5": {"level_coefficient": 0.75, "height_multiplier": 0.50},
    "squats_level_6": {"level_coefficient": 0.80, "height_multiplier": 0.50},
    "squats_level_7": {"level_coefficient": 0.85, "height_multiplier": 0.50},
    "squats_level_8": {"level_coefficient": 0.90, "height_multiplier": 0.50},
    "squats_level_9": {"level_coefficient": 0.95, "height_multiplier": 0.50},
    "squats_level_10": {"level_coefficient": 1.00, "height_multiplier": 0.50},
    # ── Shyby (Pull-ups) ──────────────────────────────────────────────────────
    "pullups_level_1": {"level_coefficient": 0.30, "height_multiplier": 0.55},
    "pullups_level_2": {"level_coefficient": 0.45, "height_multiplier": 0.55},
    "pullups_level_3": {"level_coefficient": 0.60, "height_multiplier": 0.55},
    "pullups_level_4": {"level_coefficient": 0.70, "height_multiplier": 0.55},
    "pullups_level_5": {"level_coefficient": 0.80, "height_multiplier": 0.55},
    "pullups_level_6": {"level_coefficient": 0.85, "height_multiplier": 0.55},
    "pullups_level_7": {"level_coefficient": 0.90, "height_multiplier": 0.55},
    "pullups_level_8": {"level_coefficient": 0.95, "height_multiplier": 0.55},
    "pullups_level_9": {"level_coefficient": 1.00, "height_multiplier": 0.55},
    "pullups_level_10": {"level_coefficient": 1.00, "height_multiplier": 0.55},
    # ── Zdvihy nohou (Leg raises) ─────────────────────────────────────────────
    "legraises_level_1": {"level_coefficient": 0.20, "height_multiplier": 0.30},
    "legraises_level_2": {"level_coefficient": 0.30, "height_multiplier": 0.30},
    "legraises_level_3": {"level_coefficient": 0.40, "height_multiplier": 0.30},
    "legraises_level_4": {"level_coefficient": 0.50, "height_multiplier": 0.30},
    "legraises_level_5": {"level_coefficient": 0.60, "height_multiplier": 0.30},
    "legraises_level_6": {"level_coefficient": 0.65, "height_multiplier": 0.30},
    "legraises_level_7": {"level_coefficient": 0.70, "height_multiplier": 0.30},
    "legraises_level_8": {"level_coefficient": 0.75, "height_multiplier": 0.30},
    "legraises_level_9": {"level_coefficient": 0.80, "height_multiplier": 0.30},
    "legraises_level_10": {"level_coefficient": 0.85, "height_multiplier": 0.30},
    # ── Mosty (Bridges) ───────────────────────────────────────────────────────
    "bridges_level_1": {"level_coefficient": 0.30, "height_multiplier": 0.25},
    "bridges_level_2": {"level_coefficient": 0.45, "height_multiplier": 0.25},
    "bridges_level_3": {"level_coefficient": 0.55, "height_multiplier": 0.25},
    "bridges_level_4": {"level_coefficient": 0.65, "height_multiplier": 0.25},
    "bridges_level_5": {"level_coefficient": 0.75, "height_multiplier": 0.25},
    "bridges_level_6": {"level_coefficient": 0.80, "height_multiplier": 0.25},
    "bridges_level_7": {"level_coefficient": 0.85, "height_multiplier": 0.25},
    "bridges_level_8": {"level_coefficient": 0.90, "height_multiplier": 0.25},
    "bridges_level_9": {"level_coefficient": 0.95, "height_multiplier": 0.25},
    "bridges_level_10": {"level_coefficient": 1.00, "height_multiplier": 0.25},
    # ── Kliky ve stojce (HSPU) ────────────────────────────────────────────────
    "hspu_level_1": {"level_coefficient": 0.50, "height_multiplier": 0.45},
    "hspu_level_2": {"level_coefficient": 0.60, "height_multiplier": 0.45},
    "hspu_level_3": {"level_coefficient": 0.70, "height_multiplier": 0.45},
    "hspu_level_4": {"level_coefficient": 0.78, "height_multiplier": 0.45},
    "hspu_level_5": {"level_coefficient": 0.85, "height_multiplier": 0.45},
    "hspu_level_6": {"level_coefficient": 0.90, "height_multiplier": 0.45},
    "hspu_level_7": {"level_coefficient": 0.93, "height_multiplier": 0.45},
    "hspu_level_8": {"level_coefficient": 0.95, "height_multiplier": 0.45},
    "hspu_level_9": {"level_coefficient": 0.98, "height_multiplier": 0.45},
    "hspu_level_10": {"level_coefficient": 1.00, "height_multiplier": 0.45},
}

# Default fallback values applied to any exercise not listed above.
_DEFAULT_COEFFICIENTS = {"level_coefficient": 0.50, "height_multiplier": 0.50}


class Migration(BaseMigration):
    def upgrade(self):
        # Apply per-exercise overrides first.
        for exercise_id, coefficients in _EXERCISE_OVERRIDES.items():
            self.db.exercises.update_one(
                {"id": exercise_id},
                {"$set": coefficients},
            )

        # Apply defaults to any exercise that still lacks the fields.
        self.db.exercises.update_many(
            {
                "level": {"$exists": True},
                "family": {"$exists": True},
                "level_coefficient": {"$exists": False},
            },
            {"$set": _DEFAULT_COEFFICIENTS},
        )

    def downgrade(self):
        self.db.exercises.update_many(
            {},
            {"$unset": {"level_coefficient": "", "height_multiplier": ""}},
        )
