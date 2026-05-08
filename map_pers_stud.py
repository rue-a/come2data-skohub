import csv

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SKOS

# ---------- Config ----------
HOSTING_DOMAIN = "https://rue-a.github.io/come2data-skohub"
CONCEPTS_PERS_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/personal-stellenstatistik"
)
CONCEPTS_STUD_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik"
)
IN_PERSONAL = "destatis_personal_23/destatis_personal_skos.ttl"
IN_STUD = "destatis_studierende_23/destatis_studierende_skos.ttl"
OUT_PERSONAL = "mapping_results/destatis_personal_skos.ttl"
OUT_STUD = "mapping_results/destatis_studierende_skos.ttl"
OUT_COMBINED = "mapping_results/destatis_combined_skos.ttl"
MAPPING_TABLE = "mapping_table.csv"

# ----------------------------

DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")
DESTATIS_STUD = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_STUD_DOMAIN}/")


def parse_ids(cell: str) -> list[str]:
    """Split a CSV cell containing one or more semicolon-separated concept IDs."""
    if not cell or not cell.strip():
        return []
    return [id_.strip() for id_ in cell.split(";") if id_.strip()]


def add_symmetric_matches(
    g_subject: Graph,
    g_object: Graph,
    subject_uri: URIRef,
    predicate: URIRef,
    object_uris: list[URIRef],
) -> None:
    """
    Adds match triples in both directions for a symmetric SKOS mapping property.

    Symmetric SKOS mapping properties (exactMatch, closeMatch, relatedMatch) imply
    that if A matches B, then B matches A. This function writes both directions into
    their respective graphs.

    Args:
        g_subject:   Graph that owns the subject concept (receives subject→object triples).
        g_object:    Graph that owns the object concepts (receives object→subject triples).
        subject_uri: The concept URI to map from.
        predicate:   The SKOS mapping predicate (e.g. SKOS.exactMatch).
        object_uris: List of concept URIs in g_object to map to.
    """
    for obj_uri in object_uris:
        g_subject.add((subject_uri, predicate, obj_uri))
        g_object.add((obj_uri, predicate, subject_uri))


# Load source graphs
g_personal = Graph().parse(IN_PERSONAL, format="turtle")
g_studierende = Graph().parse(IN_STUD, format="turtle")

# Enrich both graphs with SKOS mapping relations from the mapping table
with open(MAPPING_TABLE, newline="", encoding="utf-8") as csv_file:
    for row in csv.DictReader(csv_file):
        stud_id = row["studierende_concept_id"].strip()
        if not stud_id:
            continue

        stud_uri = DESTATIS_STUD[stud_id]

        close_match_uris = [DESTATIS_PERS[i] for i in parse_ids(row["close_match_personal_ids"])]
        exact_match_uris = [DESTATIS_PERS[i] for i in parse_ids(row["exact_match_personal_ids"])]
        related_match_uris = [DESTATIS_PERS[i] for i in parse_ids(row["related_match_personal_ids"])]

        add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.closeMatch, close_match_uris)
        add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.exactMatch, exact_match_uris)
        add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.relatedMatch, related_match_uris)

# Build the combined graph before binding prefixes so all three share the same bindings.
g_combined = g_personal + g_studierende

# Bind canonical prefixes in all graphs before serializing.
# override=True rebinds the namespace URI away from the generic "destatis:" prefix
# that was set when the source files were parsed.
# replace=True ensures the new prefix name itself is not already mapped elsewhere.
for graph in (g_personal, g_studierende, g_combined):
    graph.bind("destatispersonal", DESTATIS_PERS, override=True, replace=True)
    graph.bind("destatisstudierende", DESTATIS_STUD, override=True, replace=True)

# Serialize enriched graphs
g_personal.serialize(OUT_PERSONAL, format="turtle")
g_studierende.serialize(OUT_STUD, format="turtle")
g_combined.serialize(OUT_COMBINED, format="turtle")

print(f"Enriched personal vocabulary written to:    {OUT_PERSONAL}")
print(f"Enriched studierende vocabulary written to: {OUT_STUD}")
print(f"Combined vocabulary written to:             {OUT_COMBINED}")


