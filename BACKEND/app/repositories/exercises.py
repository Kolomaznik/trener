from collections.abc import Iterable

from pymongo.collection import Collection

from app.schemas.exercises import ExerciseDetail, ExerciseDocument, ExerciseListItem


class ExerciseRepository:
    def __init__(self, collection: Collection):
        self.collection = collection

    def ensure_indexes(self) -> None:
        self.collection.create_index("slug", unique=True)
        self.collection.create_index(
            [("metadata.category", 1), ("metadata.level", 1)],
            unique=True,
            name="category_level_unique",
        )

    def upsert_many(self, exercises: Iterable[ExerciseDocument]) -> int:
        count = 0
        for exercise in exercises:
            payload = exercise.model_dump(by_alias=True)
            self.collection.replace_one({"_id": payload["_id"]}, payload, upsert=True)
            count += 1
        return count

    def list_active(self) -> list[ExerciseListItem]:
        docs = self.collection.find({"metadata.is_active": True}).sort(
            [("metadata.category", 1), ("metadata.order", 1)]
        )
        items: list[ExerciseListItem] = []
        for doc in docs:
            model = ExerciseDocument.model_validate(doc)
            items.append(
                ExerciseListItem(
                    slug=model.slug,
                    name=model.name,
                    category=model.metadata.category,
                    level=model.metadata.level,
                    muscle_load=model.muscle_load,
                    short_description=short_description(model.description),
                    has_video=bool(model.media.video_url),
                )
            )
        return items

    def get_active_by_slug(self, slug: str) -> ExerciseDetail | None:
        doc = self.collection.find_one({"slug": slug, "metadata.is_active": True})
        if not doc:
            return None
        model = ExerciseDocument.model_validate(doc)
        return ExerciseDetail(
            slug=model.slug,
            name=model.name,
            description=model.description,
            muscle_load=model.muscle_load,
            performance_criteria=model.performance_criteria,
            timing=model.timing,
            steps=model.steps,
            media=model.media,
            progression=model.progression,
            metadata=model.metadata,
        )


def short_description(value: str) -> str:
    if len(value) <= 160:
        return value
    return f"{value[:157]}..."
