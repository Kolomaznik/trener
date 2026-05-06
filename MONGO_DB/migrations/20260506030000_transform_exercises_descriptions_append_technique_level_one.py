"""Append the ``## Zdokonalujte svou techniku`` section to level-1 descriptions.

Picks up the third source-book section for each level-1 exercise from
``MONGO_DB/books/trening_vezne/Level_1.md`` and appends it to the existing
two-section markdown description set by migration
``20260506010000_transform_exercises_descriptions_markdown_level_one``.

The append/strip is done atomically via aggregation-pipeline updates so
upgrade and downgrade only touch the description string, leaving any other
fields untouched.
"""

from mongodb_migrations.base import BaseMigration

_PUSHUPS_LEVEL_1_TECHNIQUE = (
    "Každý, kdo čte tuto knihu, by měl být schopný provést toto cvičení, pokud není "
    "tělesně postižený, těžce zraněný nebo nemocný. Pokud se zotavujeme po úraze nebo "
    "operaci, tento pohyb je dobrým testem možných slabin, které mohou během "
    "rehabilitace způsobit problémy."
)

_SQUATS_LEVEL_1_TECHNIQUE = (
    "Na první pokus se každému dotknout se čela koleny nepodaří. Snažte se je ohýbat "
    "co nejvíc a vaše klouby se při každém cvičení uvolní. Tato technika je prakticky "
    "nemožná pro lidi s nadváhou, protože jim překáží břicho. Než nadbytečná kila "
    "shodíte, cvičte raději s prázdným žaludkem."
)

_PULLUPS_LEVEL_1_TECHNIQUE = (
    "Toto by mělo být snadné cvičení, které by měl zvládnout doslova každý. Pokud se "
    "rehabilitujete po nějakém zranění a pohyb v dané oblasti (kde máte možná ještě "
    "stehy) se vám zdá příliš prudký, jednoduše omezte rozsah pohybu, zpevněte ramena "
    "a nenatahujte paže tak daleko."
)

_LEGRAISES_LEVEL_1_TECHNIQUE = (
    "Toto cvičení má v počáteční (natažené nohy) i konečné poloze (kolena přitažená "
    "k hrudi) stejnou obtížnost. Aby bylo cvičení trochu snazší, soustřeďte se na "
    "kratší rozsah pohybu. Až váš pas zesílí, postupně rozsah pohybu zvětšujte, dokud "
    "nebude provedení dokonalé."
)

_BRIDGES_LEVEL_1_TECHNIQUE = (
    "Většina lidí by měla udělat krátký most, aniž by se přitom museli moc namáhat. "
    "Pokud se zotavujete po zranění zad a toto cvičení pro vás představuje problém, "
    "jednoduše omezte rozsah pohybu tím, že budete pohyb provádět s několika polštáři, "
    "umístěnými pod kyčlemi."
)

_HSPU_LEVEL_1_TECHNIQUE = (
    "Většina lidí dokáže vydržet ve stoji na hlavě u zdi jen několik vteřin, a "
    "největší problém pro ně je se do ní vůbec dostat. Je potřeba se naučit, kolik "
    "síly je potřeba, aby se člověk dokázal vyhoupnout nahoru. Pokud je to pro vás "
    "obtížné, požádejte nějakého kamaráda, aby vám pomáhal nohy zvedat, dokud to "
    "nedokážete sami."
)


def _suffix(body: str) -> str:
    # Single leading \n combines with the trailing \n already in the stored
    # description to form one blank line — the standard markdown paragraph
    # break between the previous section and the new H2.
    return f"\n## Zdokonalujte svou techniku\n\n{body}\n"


SUFFIXES: dict[str, str] = {
    "pushups_level_1": _suffix(_PUSHUPS_LEVEL_1_TECHNIQUE),
    "squats_level_1": _suffix(_SQUATS_LEVEL_1_TECHNIQUE),
    "pullups_level_1": _suffix(_PULLUPS_LEVEL_1_TECHNIQUE),
    "legraises_level_1": _suffix(_LEGRAISES_LEVEL_1_TECHNIQUE),
    "bridges_level_1": _suffix(_BRIDGES_LEVEL_1_TECHNIQUE),
    "hspu_level_1": _suffix(_HSPU_LEVEL_1_TECHNIQUE),
}


class Migration(BaseMigration):
    def upgrade(self):
        for exercise_id, suffix in SUFFIXES.items():
            self.db.exercises.update_one(
                {"_id": exercise_id},
                [{"$set": {"description": {"$concat": ["$description", suffix]}}}],
            )

    def downgrade(self):
        for exercise_id, suffix in SUFFIXES.items():
            suffix_len = len(suffix)
            self.db.exercises.update_one(
                {"_id": exercise_id},
                [
                    {
                        "$set": {
                            "description": {
                                "$substrCP": [
                                    "$description",
                                    0,
                                    {
                                        "$subtract": [
                                            {"$strLenCP": "$description"},
                                            suffix_len,
                                        ]
                                    },
                                ]
                            }
                        }
                    }
                ],
            )
