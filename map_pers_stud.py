from rdflib import Graph, Namespace
from rdflib.namespace import SKOS, DCTERMS
from fuzzywuzzy import fuzz

# Basis-URL
HOSTING_DOMAIN = "https://rue-a.github.io/destatis-personal-vocab"
CONCEPTS_PERS_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/personal-stellenstatistik"
)
CONCEPTS_STUD_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik"
)


# Load both graphs
g_personal = Graph()
g_personal.parse("personal_23/destatis_personal_skos.ttl", format="turtle")

g_studierende = Graph()
g_studierende.parse("studierende_23/destatis_studierende_skos.ttl", format="turtle")


DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")
DESTATIS_STUD = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_STUD_DOMAIN}/")
g_personal.bind("skos", SKOS)
g_personal.bind("dcterms", DCTERMS)
g_personal.bind("destatispersonal", DESTATIS_PERS)
g_personal.bind("destatisstudierende", DESTATIS_STUD)

g_studierende.bind("skos", SKOS)
g_studierende.bind("dcterms", DCTERMS)
g_studierende.bind("destatispersonal", DESTATIS_PERS)
g_studierende.bind("destatisstudierende", DESTATIS_STUD)


# Mapping configuration
MATCH_THRESHOLD = 85


# Track unmatched concepts
unmatched = []

# Iterate over g_studierende concepts and compare to g_personal
for c_stud in g_studierende.subjects(SKOS.prefLabel, None):
    label_stud = next(
        (
            l
            for l in g_studierende.objects(c_stud, SKOS.prefLabel)
            if l.language == "de"
        ),
        None,
    )
    notation_stud = next(
        (n for n in g_studierende.objects(c_stud, SKOS.notation)), None
    )
    if not (label_stud and notation_stud):
        continue

    matched = False
    for c_pers in g_personal.subjects(SKOS.prefLabel, None):
        label_pers = next(
            (
                l
                for l in g_personal.objects(c_pers, SKOS.prefLabel)
                if l.language == "de"
            ),
            None,
        )
        notation_pers = next(
            (n for n in g_personal.objects(c_pers, SKOS.notation)), None
        )
        if not (label_pers and notation_pers):
            continue

        score = fuzz.token_sort_ratio(str(label_pers), str(label_stud))

        if score >= MATCH_THRESHOLD:
            matched = True
            if len(str(notation_pers)) == 2 and len(str(notation_stud)) == 2:
                g_studierende.add((c_stud, SKOS.exactMatch, c_pers))
                g_personal.add((c_pers, SKOS.exactMatch, c_stud))
                print(
                    f"exactMatch (Top): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
                )
            elif len(str(notation_pers)) == 3 and len(str(notation_stud)) == 2:
                g_studierende.add((c_stud, SKOS.exactMatch, c_pers))
                g_personal.add((c_pers, SKOS.exactMatch, c_stud))
                print(
                    f"exactMatch (Mid): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
                )
            else:
                g_studierende.add((c_stud, SKOS.closeMatch, c_pers))
                g_personal.add((c_pers, SKOS.closeMatch, c_stud))
                print(
                    f"closeMatch (Bottom): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
                )
            break

    if not matched:
        unmatched.append((str(notation_stud), str(label_stud)))

# Serialize combined result
g_personal.serialize("published_vocabs/destatis_personal_skos.ttl", format="turtle")
g_studierende.serialize(
    "published_vocabs/destatis_studierende_skos.ttl", format="turtle"
)
print("Combined graph with bidirectional mappings written to published_vocabs.")

# Write unmatched mappings to CSV
print("\nUnmatched study concepts:")
unmatched = list(set(unmatched))
for unmatch in unmatched:
    print(f"Unmatched: {unmatch[0]} | {unmatch[1]}")
