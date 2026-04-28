from functools import lru_cache

from app.db.client import get_exercises_collection
from app.repositories.exercises import ExerciseRepository


@lru_cache
def get_exercise_repository() -> ExerciseRepository:
    collection = get_exercises_collection()
    repository = ExerciseRepository(collection)
    repository.ensure_indexes()
    return repository
