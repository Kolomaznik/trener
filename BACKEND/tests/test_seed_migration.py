import mongomock

from app.db.migrations.exercises_seed import transform_source, validate_chain_integrity
from app.repositories.exercises import ExerciseRepository


SOURCE_FIXTURE = {
    "kniha": "Test book",
    "cviky": {
        "kliky": [
            {
                "uroven": 1,
                "nazev": "Klik 1",
                "popis": "Krok jedna. Krok dva.",
                "svalove_partie": ["Hrudník", "Tricepsy"],
                "kriteria_vykonu": {"zacatecnik": "1x10"},
                "casovani_tempo": "Tempo 2-1-2-1",
                "odkaz_na_ukazku": "https://example.com/1",
            },
            {
                "uroven": 2,
                "nazev": "Klik 2",
                "popis": "Krok A. Krok B.",
                "svalove_partie": ["Hrudník", "Ramena"],
                "kriteria_vykonu": {"zacatecnik": "1x15"},
                "casovani_tempo": "Tempo 2-1-2-1",
                "odkaz_na_ukazku": "https://example.com/2",
            },
        ]
    },
}


def test_seed_is_idempotent() -> None:
    docs = transform_source(SOURCE_FIXTURE)
    client = mongomock.MongoClient()
    collection = client["testdb"]["exercises"]
    repository = ExerciseRepository(collection)
    repository.ensure_indexes()

    inserted_first = repository.upsert_many(docs)
    inserted_second = repository.upsert_many(docs)

    assert inserted_first == 2
    assert inserted_second == 2
    assert collection.count_documents({}) == 2


def test_chain_validation_fails_for_missing_level() -> None:
    docs = transform_source(SOURCE_FIXTURE)
    docs[1].metadata.level = 3

    try:
        validate_chain_integrity(docs)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "contiguous levels" in str(error)


def test_chain_validation_fails_for_cycle() -> None:
    docs = transform_source(SOURCE_FIXTURE)
    docs[0].progression.previous_slug = docs[1].slug
    docs[1].progression.next_slug = docs[0].slug

    try:
        validate_chain_integrity(docs)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Cycle detected" in str(error)
