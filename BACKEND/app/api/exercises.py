from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/exercises", tags=["exercises"])

Level = Literal["beginner", "advanced", "expert"]
LEVEL_ORDER: tuple[Level, ...] = ("beginner", "advanced", "expert")


class ExerciseLevel(BaseModel):
    title: str
    reps: str
    note: str


class Exercise(BaseModel):
    id: str
    order: int
    category: str
    name: str
    description: str
    image: str
    muscles: list[str]
    frequency: str
    correct: list[str]
    incorrect: list[str]
    levels: dict[Level, ExerciseLevel]


class ExerciseListItem(BaseModel):
    id: str
    order: int
    category: str
    name: str
    description: str
    image: str
    available_levels: list[Level]
    next_exercise_id: str | None
    next_exercise_name: str | None


class ExerciseDetailResponse(BaseModel):
    id: str
    order: int
    category: str
    name: str
    description: str
    image: str
    muscles: list[str]
    frequency: str
    correct: list[str]
    incorrect: list[str]
    level: Level
    level_detail: ExerciseLevel
    level_order: list[Level]


EXERCISES: list[Exercise] = [
    Exercise(
        id="pushups",
        order=1,
        category="Kliky",
        name="Kliky",
        description="Základní tlakový cvik na hrudník, ramena a triceps.",
        image="/favicon.svg",
        muscles=["hrudník", "triceps", "ramena", "střed těla"],
        frequency="2–4x týdně",
        correct=["Rovná linie těla od hlavy po paty", "Kontrolovaný pohyb bez zhoupnutí"],
        incorrect=["Propadlá bedra", "Lokty příliš do stran"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="3 série po 8–12 opakováních",
                note="Zaměř se na techniku a plný rozsah pohybu.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="4 série po 12–20 opakováních",
                note="Přidej pomalejší negativní fázi nebo pauzu dole.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 20+ opakováních",
                note="Udržuj čistou techniku i při vysokém objemu.",
            ),
        },
    ),
    Exercise(
        id="squats",
        order=2,
        category="Dřepy",
        name="Dřepy",
        description="Základní cvik na nohy a sílu spodní části těla.",
        image="/favicon.svg",
        muscles=["kvadricepsy", "hýždě", "hamstringy", "střed těla"],
        frequency="2–4x týdně",
        correct=["Kolena sledují směr špiček", "Plná kontrola pohybu nahoru i dolů"],
        incorrect=["Zvedání pat od země", "Kulacení zad"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="3 série po 10–15 opakováních",
                note="Začni stabilním postojem na šířku ramen.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="4 série po 15–25 opakováních",
                note="Přidej pauzu ve spodní pozici pro vyšší kontrolu.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 25+ opakováních",
                note="Pracuj s vysokou kvalitou i únavou.",
            ),
        },
    ),
    Exercise(
        id="pullups",
        order=3,
        category="Shyby",
        name="Shyby",
        description="Tahový cvik rozvíjející záda, biceps a sílu úchopu.",
        image="/favicon.svg",
        muscles=["široký sval zádový", "biceps", "zadní delty", "předloktí"],
        frequency="2–3x týdně",
        correct=["Aktivní lopatky před tahem", "Brada nad hrazdu bez švihu"],
        incorrect=["Kipping a houpání", "Nedokončený rozsah pohybu"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="3 série po 3–6 opakováních",
                note="Použij asistenci a drž čistý tah.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="4 série po 6–10 opakováních",
                note="Kontroluj spouštění po každém opakování.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 10+ opakováních",
                note="Přidej tempo nebo izometrické výdrže.",
            ),
        },
    ),
    Exercise(
        id="leg-raises",
        order=4,
        category="Zvedání nohou",
        name="Zvedání nohou",
        description="Cvik na břišní svaly a přední stabilizaci trupu.",
        image="/favicon.svg",
        muscles=["přímý břišní sval", "ohýbače kyčlí", "hluboký stabilizační systém"],
        frequency="2–4x týdně",
        correct=["Bedra pod kontrolou", "Plynulý pohyb bez švihu"],
        incorrect=["Prohnutí v bedrech", "Nekontrolované spouštění nohou"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="3 série po 8–12 opakováních",
                note="Začni s pokrčenými koleny, pokud je potřeba.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="4 série po 12–18 opakováních",
                note="Drž nohy rovné a pohyb kontrolovaný.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 18+ opakováních",
                note="Přidej pauzu v horní fázi.",
            ),
        },
    ),
    Exercise(
        id="bridges",
        order=5,
        category="Mosty",
        name="Mosty",
        description="Cvik na zadní řetězec a mobilitu páteře.",
        image="/favicon.svg",
        muscles=["hýždě", "vztyčovače páteře", "hamstringy", "ramena"],
        frequency="2–3x týdně",
        correct=["Plynulý nástup do mostu", "Aktivní zapojení hýždí"],
        incorrect=["Tlak jen do beder", "Nedostatečná kontrola dechu"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="3 série po 6–10 opakováních",
                note="Začni glute bridge variantou na zemi.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="4 série po 10–15 opakováních",
                note="Postupně navyšuj rozsah a stabilitu ramen.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 15+ opakováních",
                note="Udržuj hladký přechod bez ztráty kontroly.",
            ),
        },
    ),
    Exercise(
        id="handstands",
        order=6,
        category="Stojky",
        name="Stojky",
        description="Cvik na sílu ramen, stabilitu a kontrolu těla.",
        image="/favicon.svg",
        muscles=["ramena", "triceps", "střed těla", "trapézy"],
        frequency="2–4x týdně",
        correct=["Aktivní ramena a zpevněný střed těla", "Kontrola rovnováhy přes prsty"],
        incorrect=["Přehnané prohnutí zad", "Pasivní ramena"],
        levels={
            "beginner": ExerciseLevel(
                title="Začátečník",
                reps="5 sérií po 20–30 s",
                note="Začni stojkou čelem ke zdi.",
            ),
            "advanced": ExerciseLevel(
                title="Pokročilý",
                reps="5 sérií po 30–45 s",
                note="Zařaď odlepy chodidel od zdi.",
            ),
            "expert": ExerciseLevel(
                title="Expert",
                reps="5 sérií po 45–60 s",
                note="Pracuj na volné stojce bez opory.",
            ),
        },
    ),
]


ORDERED_EXERCISES = sorted(EXERCISES, key=lambda exercise: exercise.order)
EXERCISES_BY_ID = {exercise.id: exercise for exercise in ORDERED_EXERCISES}
NEXT_EXERCISE_ID_BY_ID = {
    current.id: ORDERED_EXERCISES[index + 1].id if index + 1 < len(ORDERED_EXERCISES) else None
    for index, current in enumerate(ORDERED_EXERCISES)
}
NEXT_EXERCISE_NAME_BY_ID = {
    exercise_id: (EXERCISES_BY_ID[next_id].name if next_id else None)
    for exercise_id, next_id in NEXT_EXERCISE_ID_BY_ID.items()
}


@router.get("", response_model=list[ExerciseListItem])
def list_exercises() -> list[ExerciseListItem]:
    return [
        ExerciseListItem(
            id=exercise.id,
            order=exercise.order,
            category=exercise.category,
            name=exercise.name,
            description=exercise.description,
            image=exercise.image,
            available_levels=list(LEVEL_ORDER),
            next_exercise_id=NEXT_EXERCISE_ID_BY_ID[exercise.id],
            next_exercise_name=NEXT_EXERCISE_NAME_BY_ID[exercise.id],
        )
        for exercise in ORDERED_EXERCISES
    ]


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
def get_exercise_detail(exercise_id: str, level: Level = "beginner") -> ExerciseDetailResponse:
    exercise = EXERCISES_BY_ID.get(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    level_data = exercise.levels[level]
    return ExerciseDetailResponse(
        id=exercise.id,
        order=exercise.order,
        category=exercise.category,
        name=exercise.name,
        description=exercise.description,
        image=exercise.image,
        muscles=exercise.muscles,
        frequency=exercise.frequency,
        correct=exercise.correct,
        incorrect=exercise.incorrect,
        level=level,
        level_detail=level_data,
        level_order=list(LEVEL_ORDER),
    )
