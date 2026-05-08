import csv

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SKOS


def create_mapping(
    g_personal: Graph,
    g_studierende: Graph,
    ns_pers: Namespace,
    ns_stud: Namespace,
    mapping_table_path: str,
    out_personal: str,
    out_stud: str,
    out_combined: str,
) -> Graph:
    """
    Enriches both vocabulary graphs with SKOS mapping relations and serializes
    the individual and combined outputs to Turtle files.

    Reads the mapping table CSV and adds skos:exactMatch, skos:closeMatch, and
    skos:relatedMatch triples in both directions (studierende → personal and
    personal → studierende). Then serializes all three result files.

    Args:
        g_personal:         SKOS graph for the personal-stellenstatistik vocabulary.
        g_studierende:      SKOS graph for the studenten-pruefungsstatistik vocabulary.
        ns_pers:            Namespace for personal-stellenstatistik concept URIs.
        ns_stud:            Namespace for studenten-pruefungsstatistik concept URIs.
        mapping_table_path: Path to the mapping CSV file.
        out_personal:       Output path for the enriched personal Turtle file.
        out_stud:           Output path for the enriched studierende Turtle file.
        out_combined:       Output path for the merged combined Turtle file.

    Returns:
        The combined rdflib Graph containing all triples from both vocabularies.
    """
    with open(mapping_table_path, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            stud_id = row["studierende_concept_id"].strip()
            if not stud_id:
                continue

            stud_uri = ns_stud[stud_id]
            close_match_uris = [ns_pers[i] for i in _parse_ids(row["close_match_personal_ids"])]
            exact_match_uris = [ns_pers[i] for i in _parse_ids(row["exact_match_personal_ids"])]
            related_match_uris = [ns_pers[i] for i in _parse_ids(row["related_match_personal_ids"])]

            _add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.closeMatch, close_match_uris)
            _add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.exactMatch, exact_match_uris)
            _add_symmetric_matches(g_studierende, g_personal, stud_uri, SKOS.relatedMatch, related_match_uris)

    g_combined = g_personal + g_studierende

    # Bind canonical prefixes in all three graphs before serializing.
    # override=True rebinds the namespace URI away from any generic prefix set during
    # graph construction; replace=True ensures the new prefix name is not already taken.
    for graph in (g_personal, g_studierende, g_combined):
        graph.bind("destatispersonal", ns_pers, override=True, replace=True)
        graph.bind("destatisstudierende", ns_stud, override=True, replace=True)

    g_personal.serialize(out_personal, format="turtle")
    g_studierende.serialize(out_stud, format="turtle")
    g_combined.serialize(out_combined, format="turtle")

    print(f"Enriched personal vocabulary written to:    {out_personal}")
    print(f"Enriched studierende vocabulary written to: {out_stud}")
    print(f"Combined vocabulary written to:             {out_combined}")

    return g_combined


def _parse_ids(cell: str) -> list[str]:
    """Split a CSV cell containing one or more semicolon-separated concept IDs."""
    if not cell or not cell.strip():
        return []
    return [id_.strip() for id_ in cell.split(";") if id_.strip()]


def _add_symmetric_matches(
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
