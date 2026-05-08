from rdflib import Graph, Namespace
from rdflib.namespace import SKOS, DCTERMS
from fuzzywuzzy import fuzz
from pathlib import Path

# ---------- Config ----------
HOSTING_DOMAIN = "https://rue-a.github.io/come2data-skohub"
CONCEPTS_PERS_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/personal-stellenstatistik"
)
CONCEPTS_STUD_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik"
)
IN_PERSONAL = "personal_23/destatis_personal_skos.ttl"
IN_STUD = "studierende_23/destatis_studierende_skos.ttl"
OUT_COMBINED = "published_vocabs/destatis_combined_skos.ttl"

MATCH_THRESHOLD = 95
# ----------------------------

# Load source graphs
g_personal = Graph().parse(IN_PERSONAL, format="turtle")
g_studierende = Graph().parse(IN_STUD, format="turtle")

# Namespaces
DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")
DESTATIS_STUD = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_STUD_DOMAIN}/")
ISCED = Namespace("https://publications.europa.eu/resource/authority/snb/isced-f/")

# Build one combined graph
combined = Graph()
for prefix, ns in [
    ("skos", SKOS),
    ("dcterms", DCTERMS),
    ("dpers", DESTATIS_PERS),
    ("dstud", DESTATIS_STUD),
    ("isced", ISCED),
]:
    combined.bind(prefix, ns)

# Add all triples from both graphs into the combined graph
for t in g_personal:
    combined.add(t)
for t in g_studierende:
    combined.add(t)


# Helper to get German prefLabel + notation
def get_de_pref_label(g: Graph, s):
    label = next(
        (
            l
            for l in g.objects(s, SKOS.prefLabel)
            if getattr(l, "language", None) == "de"
        ),
        None,
    )
    notation = next((n for n in g.objects(s, SKOS.notation)), None)
    # notation == id
    return label, notation


# unmatched = set()

# # Iterate over STUDIERENDE concepts and compare to PERSONAL concepts
# # (we only add mapping triples to the *combined* graph)
# for c_stud in set(g_studierende.subjects(SKOS.prefLabel, None)):
#     label_stud, notation_stud = get_de_pref_label(g_studierende, c_stud)
#     if not (label_stud and notation_stud):
#         continue

#     matched = False
#     for c_pers in set(g_personal.subjects(SKOS.prefLabel, None)):
#         label_pers, notation_pers = get_de_pref_label(g_personal, c_pers)

#         if not (label_pers and notation_pers):
#             continue

#         score = fuzz.token_sort_ratio(str(label_pers), str(label_stud))
#         if score >= MATCH_THRESHOLD:
#             matched = True

#             np, ns = str(notation_pers), str(notation_stud)

#             # Decide mapping strength based on code-length relationship
#             if len(np) == 2 and len(ns) == 2:
#                 combined.add((c_stud, SKOS.exactMatch, c_pers))
#                 combined.add((c_pers, SKOS.exactMatch, c_stud))
#                 print(
#                     f"exactMatch (Top): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
#                 )
#             elif len(np) == 3 and len(ns) == 3:
#                 combined.add((c_stud, SKOS.exactMatch, c_pers))
#                 combined.add((c_pers, SKOS.exactMatch, c_stud))
#                 print(
#                     f"exactMatch (Mid): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
#                 )
#             elif len(np) == 4 and len(ns) == 4:
#                 combined.add((c_stud, SKOS.closeMatch, c_pers))
#                 combined.add((c_pers, SKOS.closeMatch, c_stud))
#                 print(
#                     f"closeMatch (Bottom): {label_stud} ({notation_stud}) ↔ {label_pers} ({notation_pers})"
#                 )
#             break

#     if not matched:
#         unmatched.add((str(notation_stud), str(label_stud)))

# Ensure output dir exists
Path(OUT_COMBINED).parent.mkdir(parents=True, exist_ok=True)

# Serialize only ONE graph containing everything
combined.serialize(OUT_COMBINED, format="turtle")
print(f"\nCombined graph (vocabularies + mappings) written to: {OUT_COMBINED}")

# Print unmatched
if unmatched:
    print("\nUnmatched study concepts:")
    for code, label in sorted(unmatched):
        print(f"Unmatched: {code} | {label}")
else:
    print("\nAll study concepts matched at the given threshold.")
