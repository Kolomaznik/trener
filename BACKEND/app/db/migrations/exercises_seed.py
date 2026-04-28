import json
import re
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from app.db.client import get_exercises_collection
from app.repositories.exercises import ExerciseRepository
from app.schemas.exercises import ExerciseDocument, ExerciseMetadata, Media, MuscleLoad, Progression, Tempo

DEFAULT_SOURCE_PATH = Path(__file__).resolve().parent.parent / "seed_data" / "exercises_source.json"

MUSCLE_INTENSITY_HINTS = {
    "Hrudník": 4,
    "Tricepsy": 3,
    "Ramena": 3,
    "Střed těla": 3,
    "kvadricepsy": 4,
    "hamstringy": 3,
    "Hýžd": 4,
    "Lýtka": 2,
    "Spodní záda": 3,
    "břišní": 3,
}


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    without_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", without_diacritics).strip("-").lower()
    return slug


def parse_tempo(raw_tempo: str) -> Tempo:
    match = re.search(r"Tempo\s+(\d+)-(\d+)-(\d+)-(\d+)", raw_tempo)
    if not match:
        return Tempo(raw=raw_tempo)
    ecc, pause_bottom, conc, pause_top = map(int, match.groups())
    return Tempo(
        eccentric_seconds=ecc,
        pause_bottom_seconds=pause_bottom,
        concentric_seconds=conc,
        pause_top_seconds=pause_top,
        raw=raw_tempo,
    )


def split_steps(description: str) -> list[str]:
    chunks = [part.strip() for part in description.split(".")]
    return [chunk for chunk in chunks if chunk]


def infer_intensity(muscle_name: str) -> int:
    for hint, intensity in MUSCLE_INTENSITY_HINTS.items():
        if hint.lower() in muscle_name.lower():
            return intensity
    return 3


def transform_source(source: dict) -> list[ExerciseDocument]:
    book = source["kniha"]
    raw_categories = source["cviky"]
    now = datetime.now(UTC)
    transformed: list[ExerciseDocument] = []

    for category, entries in raw_categories.items():
        ordered = sorted(entries, key=lambda item: item["uroven"])

        for index, entry in enumerate(ordered):
            level = entry["uroven"]
            level_suffix = f"u{level}"
            slug = f"{slugify(category)}-{level_suffix}-{slugify(entry['nazev'])}"

            previous_slug = None
            next_slug = None
            if index > 0:
                prev = ordered[index - 1]
                previous_slug = f"{slugify(category)}-u{prev['uroven']}-{slugify(prev['nazev'])}"
            if index < len(ordered) - 1:
                nxt = ordered[index + 1]
                next_slug = f"{slugify(category)}-u{nxt['uroven']}-{slugify(nxt['nazev'])}"

            transformed.append(
                ExerciseDocument(
                    _id=slug,
                    slug=slug,
                    name=entry["nazev"],
                    description=entry["popis"],
                    muscle_load=[
                        MuscleLoad(name=muscle, intensity=infer_intensity(muscle))
                        for muscle in entry["svalove_partie"]
                    ],
                    performance_criteria=entry.get("kriteria_vykonu", {}),
                    timing=parse_tempo(entry["casovani_tempo"]),
                    steps=split_steps(entry["popis"]),
                    media=Media(video_url=entry.get("odkaz_na_ukazku"), images=[]),
                    progression=Progression(
                        previous_slug=previous_slug,
                        next_slug=next_slug,
                        unlock_condition=(
                            None
                            if not previous_slug
                            else f"Dokončit {ordered[index - 1]['nazev']} v požadovaném výkonu"
                        ),
                    ),
                    metadata=ExerciseMetadata(
                        source_book=book,
                        category=category,
                        level=level,
                        order=index + 1,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    ),
                )
            )

    validate_chain_integrity(transformed)
    return transformed


def validate_chain_integrity(exercises: list[ExerciseDocument]) -> None:
    if not exercises:
        return

    slug_set = {exercise.slug for exercise in exercises}
    if len(slug_set) != len(exercises):
        raise ValueError("Duplicate exercise slug detected.")

    grouped: dict[str, list[ExerciseDocument]] = defaultdict(list)
    for exercise in exercises:
        grouped[exercise.metadata.category].append(exercise)

    for category, items in grouped.items():
        levels = sorted(item.metadata.level for item in items)
        expected = list(range(1, len(levels) + 1))
        if levels != expected:
            raise ValueError(
                f"Category '{category}' must contain contiguous levels starting at 1."
            )

    for exercise in exercises:
        links = [exercise.progression.previous_slug, exercise.progression.next_slug]
        for link in links:
            if link and link not in slug_set:
                raise ValueError(f"Exercise '{exercise.slug}' references unknown slug '{link}'.")

    visited: set[str] = set()
    stack: set[str] = set()

    by_slug = {exercise.slug: exercise for exercise in exercises}

    def dfs(slug: str) -> None:
        if slug in stack:
            raise ValueError(f"Cycle detected in exercise chain at '{slug}'.")
        if slug in visited:
            return
        visited.add(slug)
        stack.add(slug)
        next_slug = by_slug[slug].progression.next_slug
        if next_slug:
            dfs(next_slug)
        stack.remove(slug)

    for exercise in exercises:
        dfs(exercise.slug)


def load_source(path: Path = DEFAULT_SOURCE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_exercises(source: dict | None = None) -> int:
    payload = source or load_source()
    exercises = transform_source(payload)
    repository = ExerciseRepository(get_exercises_collection())
    repository.ensure_indexes()
    return repository.upsert_many(exercises)


def main() -> None:
    inserted = seed_exercises()
    print(f"Seed completed. Upserted records: {inserted}")


if __name__ == "__main__":
    main()
