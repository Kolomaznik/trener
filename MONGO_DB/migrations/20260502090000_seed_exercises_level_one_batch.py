from mongodb_migrations.base import BaseMigration

EXERCISES = [
    {
        "_id": "squats_level_1",
        "id": "squats_level_1",
        "name": "Dřepy ve svíčce",
        "english_name": "Shoulderstand Squats",
        "family": "Dřepy",
        "level": 1,
        "description": (
            "Tento cvik zcela odstraňuje zátěž z kolenních a kyčelních kloubů. "
            "Pomáhá promazat klouby, stimuluje krevní oběh v nohách a učí správné "
            "mechanice pohybu kyčlí bez gravitačního tlaku."
        ),
        "instructions": [
            (
                "Lehni si na záda, zvedni nohy do vzduchu a rukama si podepři "
                "bedra, abys dostal tělo do pozice svíčky."
            ),
            "Váha těla spočívá na horní části zad a ramenou, nikoliv na krku.",
            "S nádechem pomalu krč kolena a spouštěj je směrem k čelu.",
            "Ve spodní pozici (kolena blízko čela) pohyb na sekundu zastav.",
            "S výdechem plynule vytlač nohy zpět do propnutí směrem ke stropu.",
            "V horní pozici pohyb opět na sekundu zastav a zopakuj.",
        ],
        "media": {
            "youtube_tutorial": "https://www.youtube.com/watch?v=x0xN95l0zGE",
            "thumbnail_url": "https://img.youtube.com/vi/x0xN95l0zGE/hqdefault.jpg",
        },
        "cadence": {
            "eccentric_sec": 2,
            "pause_bottom_sec": 1,
            "concentric_sec": 2,
            "pause_top_sec": 1,
            "total_rep_time_sec": 6,
            "coach_note": (
                "Pohyb musí být kontrolovaný středem těla, nenech nohy padat gravitací."
            ),
        },
        "progression_goals": {
            "beginner": {"sets": 1, "reps": 10},
            "intermediate": {"sets": 2, "reps": 25},
            "mastery": {"sets": 3, "reps": 50},
            "coach_note": ("Po dosažení 3x50 přejdi na Dřepy s oporou (Jackknife Squats)."),
        },
        "muscle_engagement_percent": {
            "abs": 30,
            "lower_back": 30,
            "quadriceps": 20,
            "hamstrings": 10,
            "knees": 10,
        },
    },
    {
        "_id": "pullups_level_1",
        "id": "pullups_level_1",
        "name": "Svislé přítahy",
        "english_name": "Vertical Pulls",
        "family": "Shyby",
        "level": 1,
        "description": (
            "Základní kámen pro budování síly zad a úchopu. Připravuje lokty a "
            "ramena na tahové pohyby a učí správné retrakci lopatek."
        ),
        "instructions": [
            (
                "Postav se čelem k pevnému bodu (např. zárubeň dveří, sloup) zhruba "
                "na vzdálenost paží."
            ),
            "Chyť se okraje zárubně oběma rukama zhruba ve výšce hrudníku.",
            (
                "S nádechem pomalu povoluj paže a nech tělo naklonit dozadu, "
                "dokud nejsou paže téměř propnuté."
            ),
            "Zastav na vteřinu v protažení.",
            ("S výdechem se plynule přitáhni zpět, pohyb musí vycházet ze stažení lopatek k sobě."),
            "V horní fázi pohyb na vteřinu zastav a zopakuj.",
        ],
        "media": {
            "youtube_tutorial": "https://www.youtube.com/watch?v=a1_W_zWf2rY",
            "thumbnail_url": "https://img.youtube.com/vi/a1_W_zWf2rY/hqdefault.jpg",
        },
        "cadence": {
            "eccentric_sec": 2,
            "pause_bottom_sec": 1,
            "concentric_sec": 2,
            "pause_top_sec": 1,
            "total_rep_time_sec": 6,
            "coach_note": (
                "Soustřeď se na to, že jako první tahají svaly mezi lopatkami, až pak paže."
            ),
        },
        "progression_goals": {
            "beginner": {"sets": 1, "reps": 10},
            "intermediate": {"sets": 2, "reps": 20},
            "mastery": {"sets": 3, "reps": 40},
            "coach_note": (
                "Po zvládnutí 3x40 jsi připraven na Horizontální přítahy (Horizontal Pulls)."
            ),
        },
        "muscle_engagement_percent": {
            "lats": 30,
            "rhomboids": 25,
            "biceps": 20,
            "forearms": 15,
            "hands": 10,
        },
    },
    {
        "_id": "legraises_level_1",
        "id": "legraises_level_1",
        "name": "Přítahy kolen v sedě",
        "english_name": "Knee Tucks",
        "family": "Zdvihy nohou",
        "level": 1,
        "description": (
            "Bezpečný úvod do tréninku břišního svalstva. Chrání bederní páteř a "
            "plynule buduje sílu ohybačů kyčlí a přímého svalu břišního."
        ),
        "instructions": [
            "Sedni si na kraj židle nebo postele, nohy natažené mírně před sebou.",
            "Rukama se chytni za okraj pro stabilitu a mírně se zakloň dozadu.",
            ("S výdechem plynule přitáhni obě kolena směrem k hrudníku v rozmezí zhruba 15-20 cm."),
            "Ve chvíli největšího smrštění břicha pohyb na sekundu zastav.",
            ("S nádechem pomalu vracej nohy do výchozí pozice (natažené, ale nedotýkají se země)."),
            "Zastav na vteřinu a zopakuj.",
        ],
        "media": {
            "youtube_tutorial": "https://www.youtube.com/watch?v=1b-n5k5mD0U",
            "thumbnail_url": "https://img.youtube.com/vi/1b-n5k5mD0U/hqdefault.jpg",
        },
        "cadence": {
            "eccentric_sec": 2,
            "pause_bottom_sec": 1,
            "concentric_sec": 2,
            "pause_top_sec": 1,
            "total_rep_time_sec": 6,
            "coach_note": (
                "Zásadní je plynulost; nešvihej nohama, pohyb ovládej výhradně silou břicha."
            ),
        },
        "progression_goals": {
            "beginner": {"sets": 1, "reps": 10},
            "intermediate": {"sets": 2, "reps": 25},
            "mastery": {"sets": 3, "reps": 40},
            "coach_note": ("Až dosáhneš 3x40, přejdi na Zdvihy nohou vleže (Flat Knee Raises)."),
        },
        "muscle_engagement_percent": {
            "abs": 45,
            "hip_flexors": 45,
            "quadriceps": 10,
        },
    },
    {
        "_id": "bridges_level_1",
        "id": "bridges_level_1",
        "name": "Krátké mosty",
        "english_name": "Short Bridges",
        "family": "Mosty",
        "level": 1,
        "description": (
            "Tento cvik jemně probouzí zádový řetězec, učí správné aktivaci hýždí "
            "a odstraňuje ztuhlost spodních zad, aniž by je zatěžoval extrémním ohybem."
        ),
        "instructions": [
            (
                "Lehni si na záda, pokrč kolena a chodidla polož celou plochou na "
                "zem zhruba na šířku ramen (blízko k hýždím)."
            ),
            "Ruce polož podél těla dlaněmi dolů.",
            (
                "S výdechem zatlač do pat a plynule zvedni pánev směrem nahoru, "
                "dokud tvá stehna a trup netvoří rovnou linii."
            ),
            "V horní pozici pevně stiskni hýždě a podrž pohyb 1 sekundu.",
            "S nádechem pomalu a kontrolovaně spouštěj pánev zpět na zem.",
            "Dole pohyb na sekundu zastav a opakuj.",
        ],
        "media": {
            "youtube_tutorial": "https://www.youtube.com/watch?v=8lT2-FzD_G8",
            "thumbnail_url": "https://img.youtube.com/vi/8lT2-FzD_G8/hqdefault.jpg",
        },
        "cadence": {
            "eccentric_sec": 2,
            "pause_bottom_sec": 1,
            "concentric_sec": 2,
            "pause_top_sec": 1,
            "total_rep_time_sec": 6,
            "coach_note": (
                "Dávej pozor, abys neprohýbal bedra příliš vysoko. Pohyb musí "
                "vycházet primárně z tlaku hýždí, ne ze zad."
            ),
        },
        "progression_goals": {
            "beginner": {"sets": 1, "reps": 10},
            "intermediate": {"sets": 2, "reps": 25},
            "mastery": {"sets": 3, "reps": 50},
            "coach_note": (
                "Až zvládneš 3x50 s pevnou pauzou nahoře, přejdi na Rovné mosty (Straight Bridges)."
            ),
        },
        "muscle_engagement_percent": {
            "glutes": 40,
            "hamstrings": 30,
            "lower_back": 20,
            "rhomboids": 10,
        },
    },
    {
        "_id": "hspu_level_1",
        "id": "hspu_level_1",
        "name": "Stojka na hlavě o zeď",
        "english_name": "Wall Headstands",
        "family": "Kliky ve stojce",
        "level": 1,
        "description": (
            "Základní příprava pro kompletní převrácené pozice. Zvyká mozek na "
            "prokrvení v pozici hlavou dolů a buduje statickou sílu krku, ramen "
            "a rovnováhu."
        ),
        "instructions": [
            "Polož si kousek od zdi polštář nebo srolovaný ručník.",
            (
                "Zaklekni, polož temeno hlavy na polštář a dlaně na zem tak, "
                "abys vytvořil s hlavou stabilní trojúhelník."
            ),
            "Jemně se odraz a vykopni nohy nahoru tak, aby se paty opřely o zeď.",
            "Zpevni celé tělo – od krku, přes břicho až po špičky prstů na nohou.",
            ("Pravidelně dýchej a drž pozici. Na konci opatrně spusť nohy dolů jedno po druhém."),
        ],
        "media": {
            "youtube_tutorial": "https://www.youtube.com/watch?v=4FqV_u_e2A8",
            "thumbnail_url": "https://img.youtube.com/vi/4FqV_u_e2A8/hqdefault.jpg",
        },
        "cadence": {
            "eccentric_sec": 0,
            "pause_bottom_sec": 0,
            "concentric_sec": 0,
            "pause_top_sec": 1,
            "total_rep_time_sec": 1,
            "coach_note": (
                "Cvik je statický (izometrický). Počet opakování (reps) v cílech "
                "znamená počet SEKUND výdrže."
            ),
        },
        "progression_goals": {
            "beginner": {"sets": 1, "reps": 30},
            "intermediate": {"sets": 1, "reps": 60},
            "mastery": {"sets": 1, "reps": 120},
            "coach_note": (
                "Po dosažení výdrže 2 minuty (120 sekund) jsi plně připraven na "
                "Kliky ve stojce - Vránu (Crow Stands)."
            ),
        },
        "muscle_engagement_percent": {
            "deltoids": 30,
            "trapezius": 20,
            "neck": 20,
            "hands": 10,
            "triceps": 10,
            "abs": 10,
        },
    },
]


class Migration(BaseMigration):
    def upgrade(self):
        for exercise in EXERCISES:
            self.db.exercises.update_one(
                {"_id": exercise["_id"]},
                {"$set": exercise},
                upsert=True,
            )

    def downgrade(self):
        self.db.exercises.delete_many({"_id": {"$in": [exercise["_id"] for exercise in EXERCISES]}})
