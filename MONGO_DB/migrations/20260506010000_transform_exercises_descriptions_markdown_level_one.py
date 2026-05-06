# ruff: noqa: E501  -- markdown paragraphs are stored verbatim, not wrapped
"""Replace level-1 exercise descriptions with markdown content from Trénink vězně.

For each level-1 exercise, the short plain-text description is replaced with the
`## Provedení` and `## Cvičení pod drobnohledem` sections from the source book
(MONGO_DB/books/trening_vezne/Level_1.md). The previous descriptions are
preserved verbatim for rollback.
"""

from mongodb_migrations.base import BaseMigration

_PUSHUPS_LEVEL_1_NEW = """## Provedení

Postavte se proti zdi, chodidla mějte u sebe. Položte dlaně naplocho na zeď. To je počáteční poloha (obr. 1). Ruce jsou rovné a roztažené na šířku ramen, dlaně jsou ve výšce prsou.

Ohněte ramena a lokty, dokud se čelo jemně nedotkne zdi. To je konečná poloha (obr. 2). Dostaňte se zpět do počáteční polohy a opakujte.

## Cvičení pod drobnohledem

Kliky o zeď jsou první ze série deseti cviků, potřebných k dokonalému zvládnutí kliků. Je to první stupeň, a proto je nejjednodušší.

Každý zdravý člověk by měl dokázat provést tento cvik bez jakýchkoli problémů. Kliky o zeď také patří do terapeutické série kliků, užitečných pro každého, kdo se zotavuje po úraze nebo po operaci a snaží se uzdravit a pomalu obnovit svou sílu. K chronickým a akutním úrazům jsou náchylné především lokty, zápěstí a ramena, zejména citlivé rotátorové manžety v rameni. Toto cvičení dané oblasti jemně aktivuje, stimuluje, zlepšuje jejich prokrvení a svalový tonus. Začátečníci musí vždy začínat velmi citlivě, aby dali svým schopnostem možnost se rozvíjet co nejpřirozeněji. Proto by měli začít s tímto cvičením.
"""

_SQUATS_LEVEL_1_NEW = """## Provedení

S ohnutými koleny se položte na záda. Vykopněte a dostaňte nohy do vzduchu za pomoci rukou. Když dosáhnete této polohy, podepřete si bedra rukama. Ramena stále spočívají na zemi. Ocitnete se ve „stoji na ramenou“, opírat se budete o ramena, horní část zad a o zadní strany paží. Uvědomte si, že se v těchto místech musíte neustále podpírat a že nesmíte zatěžovat krk. Vaše tělo musí být rovné, neohýbejte kyčle. To je počáteční poloha (obr. 21). Udržujte trup rovný, a zároveň se ohněte v kyčlích a kolenou tak, aby se kolena dotkla čela. To je konečná poloha (obr. 22). Natáhněte nohy dozadu tak, aby se trup ocitl v počáteční poloze. Opakujte.

## Cvičení pod drobnohledem

Dřepy ve stoji na ramenou jsou skvělé přípravné cvičení pro každého, kdo chce s dřepy začít. Vzhledem k obrácené poloze cviku nespočívá na kolenou a bedrech prakticky žádná váha, což z něj dělá ideální rehabilitační cvičení pro lidi s poraněnými zády nebo koleny – pomáhá jim vrátit se zpátky ke sportům, pro které je pohyb nohou důležitý. Technicky vzato jsou dřepy ve stoji na ramenou náročnější pro horní část těla než pro spodní. Ale zároveň uvolňují ztuhlé klouby, zvyšují rozsah pohybu, a především nasměrují začátečníky k dokonalé formě.
"""

_PULLUPS_LEVEL_1_NEW = """## Provedení

Najděte si nějakou vertikální základnu, na které se dokážete udržet. Měla by být bezpečná a umožnit vám pohodlný úchop, takže navrhuji dveřní rám nebo vysoké zábradlí. Postavte se blízko základny, špičky vašich chodidel by měly být 7 až 15 cm daleko. Uchopte základnu tak, aby vám to bylo pohodlné. Ideálně by vaše ruce měly být na šířku ramen od sebe, ale stačí, když budete stát tak, aby to bylo symetrické. Toto je počáteční poloha (obr. 41). Díky blízkosti základny budou vaše paže ohnuté. Teď nechte váhu vašeho těla, aby se za pomoci mírného „opření“ posunula dozadu. Přitom roztahujte paže tak, aby na konci byly téměř rovné a vaše tělo směřovalo úhlopříčně dozadu. Toto je konečná poloha (obr. 42). V tomto bodě budete cítit mírný tah v horní části zad a možná i v pažích. Udělejte krátkou pauzu, než se přitáhnete zpět do počáteční polohy. To provedete stažením lopatek, paže nechte lehce ohnuté. Na chvíli si odpočiňte a cvik opakujte.

## Cvičení pod drobnohledem

Vertikální shyb je velmi jemný cvik, ideální pro sportovce, kteří se pokoušejí obnovit sílu svých zad a paží po nějakém zranění, například ramene, bicepsu nebo lokte. Zvyšuje průtok krve a obnovuje dřívější úroveň protažení. Je to také skvělé cvičení pro jakéhokoliv začátečníka. Malá intenzita umožňuje sportovcům, kteří začínají se shyby, aby přišli na to, že v ramenou a horní části zad opravdu mají svaly.
"""

_LEGRAISES_LEVEL_1_NEW = """## Provedení

Sedněte si na kraj židle nebo postele. Mírně se zakloňte, uchopte rukama okraj sedadla a narovnejte nohy. Chodidla jsou spolu s patami několik centimetrů od podlahy. To je počáteční poloha (obr. 61). Pomalu zvedejte kolena nahoru a k sobě, až budou asi 15–25 cm od vašeho hrudníku. Vydechněte a souběžně přitahujte kolena. Pohyb ukončíte úplným výdechem, vaše břišní svaly by v té chvíli měly být pevně stažené. To je konečná poloha (obr. 62). Udělejte vteřinovou pauzu a pak se vraťte do počáteční polohy. Nadechněte se, když natahujete nohy. Vaše chodidla by měla opsat přímku a neměla by se dotknout podlahy, dokud cvik neukončíte. Celou dobu mějte zaťažené břicho. Odolejte nutkání rychle cvik zopakovat, mezi opakováním se musíte pořádně nadechnout.

## Cvičení pod drobnohledem

Přitahování kolen je ideálním cvičením pro začátečníky. Vede ke správnému postavení páteře, trénuje břišní svaly a posiluje přitahovače kyčlí. Většině lidí také připadá lehké, a tedy představuje skvělou příležitost, jak obecně zlepšit svou techniku. Důležitý je plynulý pohyb, správný dechový rytmus a pevně zaťažené břicho.
"""

_BRIDGES_LEVEL_1_NEW = """## Provedení

Položte se na záda, nohy mějte natažené a ruce zkřížené na břiše. Natáhněte chodidla a ohněte kolena tak, aby byly vaše holeně téměř rovnoběžné se zemí a chodidla ležela naplocho na zemi. Ta by od sebe měla být vzdálená na šířku ramen, případně méně, podle toho, jakou máte postavu. Paty by měly být asi 15–20 cm od hýždí. To je počáteční poloha (obr. 83). Přitlačte chodidla k zemi a zvedněte kyčle a záda tak, aby váha těla spočívala jen na ramenou a chodidlech. V tomto stadiu jsou stehna a trup v jedné přímce a kyčle se neprohýbají. To je konečná poloha (obr. 84). V poloze nahoře se na chvíli zastavte a provádějte pohyby v opačném pořadí, abyste se vrátili zpět do počáteční polohy. Pak cvičení opakujte. Když jdete nahoru, vydechujte, když jdete dolů, nadechujte se.

## Cvičení pod drobnohledem

Krátké mosty zahrnují zvedání se za pomoci dolních končetin a patří k těm nejmírnějším způsobům, jak začít s tréninkem zad, protože v běžném životě obvykle aktivujete zádové svaly prostřednictvím nohou, například při chůzi, předklonu atd. Držení trupu zpříma na vrcholu krátkého pohybu v mostu stimuluje páteř a svaly kyčlí, aniž by přímo obratle zatěžoval jakýkoliv tlak. Proto je toto cvičení skvělou terapií pro ty, kteří trpí poraněním plotének.
"""

_HSPU_LEVEL_1_NEW = """## Provedení

Najděte si nějakou pevnou zeď. K jejímu úpatí položte polštář nebo smotaný ručník, tam si budete opírat hlavu. Klekněte si, položte dlaně na zem a hlavu na polštář. Měli byste být asi 15–20 cm od zdi a dlaně by od hlavy měly být na šířku ramen. Koleno své silnější nohy přitáhněte k příslušnému lokti a druhou nohu narovnejte tak, aby se koleno zvedlo ze země (obr. 107). Silnější nohou zatlačte do země a druhou nohou vykopněte do vzduchu tak, aby se obě nohy zvedly ke zdi. Až se dotknete zdi, nohy pomalu narovnejte, tělo by mělo být v jedné přímce (obr. 108). Ústa jsou zavřená, dýchejte nosem. Chvíli setrvejte nahoře, pak ohněte nohy a pomalu a plynule je spusťte dolů.

## Cvičení pod drobnohledem

Každý, kdo se chce naučit klik ve stojce, musí nejdřív zvládnout obrácenou polohu. Stoj na hlavě u zdi je pro začátek nejlepší. Stačí trocha praxe, aby se cévy a orgány trupu a hlavy náhlé změně gravitace snadno přizpůsobily. Také je to dobré cvičení pro rovnováhu a posílení ramenních svalů, protože celé tělo je vlastně nad hlavou, kde ho udržují primárně ramena.
"""


# Original short plain-text descriptions, preserved for rollback.
_PUSHUPS_LEVEL_1_OLD = (
    "Ideální rehabilitační a přípravný cvik. Buduje základní sílu a zpevňuje "
    "šlachy a klouby horní poloviny těla bez rizika přetížení."
)

_SQUATS_LEVEL_1_OLD = (
    "Tento cvik zcela odstraňuje zátěž z kolenních a kyčelních kloubů. "
    "Pomáhá promazat klouby, stimuluje krevní oběh v nohách a učí správné "
    "mechanice pohybu kyčlí bez gravitačního tlaku."
)

_PULLUPS_LEVEL_1_OLD = (
    "Základní kámen pro budování síly zad a úchopu. Připravuje lokty a "
    "ramena na tahové pohyby a učí správné retrakci lopatek."
)

_LEGRAISES_LEVEL_1_OLD = (
    "Bezpečný úvod do tréninku břišního svalstva. Chrání bederní páteř a "
    "plynule buduje sílu ohybačů kyčlí a přímého svalu břišního."
)

_BRIDGES_LEVEL_1_OLD = (
    "Tento cvik jemně probouzí zádový řetězec, učí správné aktivaci hýždí "
    "a odstraňuje ztuhlost spodních zad, aniž by je zatěžoval extrémním ohybem."
)

_HSPU_LEVEL_1_OLD = (
    "Základní příprava pro kompletní převrácené pozice. Zvyká mozek na "
    "prokrvení v pozici hlavou dolů a buduje statickou sílu krku, ramen "
    "a rovnováhu."
)


DESCRIPTIONS: dict[str, dict[str, str]] = {
    "pushups_level_1": {"new": _PUSHUPS_LEVEL_1_NEW, "old": _PUSHUPS_LEVEL_1_OLD},
    "squats_level_1": {"new": _SQUATS_LEVEL_1_NEW, "old": _SQUATS_LEVEL_1_OLD},
    "pullups_level_1": {"new": _PULLUPS_LEVEL_1_NEW, "old": _PULLUPS_LEVEL_1_OLD},
    "legraises_level_1": {"new": _LEGRAISES_LEVEL_1_NEW, "old": _LEGRAISES_LEVEL_1_OLD},
    "bridges_level_1": {"new": _BRIDGES_LEVEL_1_NEW, "old": _BRIDGES_LEVEL_1_OLD},
    "hspu_level_1": {"new": _HSPU_LEVEL_1_NEW, "old": _HSPU_LEVEL_1_OLD},
}


class Migration(BaseMigration):
    def upgrade(self):
        for exercise_id, content in DESCRIPTIONS.items():
            self.db.exercises.update_one(
                {"_id": exercise_id},
                {"$set": {"description": content["new"]}},
            )

    def downgrade(self):
        for exercise_id, content in DESCRIPTIONS.items():
            self.db.exercises.update_one(
                {"_id": exercise_id},
                {"$set": {"description": content["old"]}},
            )
