import pandas as pd
from fuzzywuzzy import fuzz
from rdflib import Graph, Literal, Namespace, URIRef, XSD
from rdflib.namespace import DCTERMS, RDF, SKOS

ISCED = Namespace("https://publications.europa.eu/resource/authority/snb/isced-f/")
VANN = Namespace("http://purl.org/vocab/vann/")


def create_stud_skos(namespace: Namespace) -> Graph:
    """
    Builds the SKOS graph for the Destatis studenten-pruefungsstatistik classification.

    Loads the three-level hierarchy (Fächergruppe → Studienbereich → Studienfach)
    from CSV files, constructs SKOS concepts with ISCED exactMatch links, and
    enriches them with English labels from a reference TTL and a manual fallback CSV.

    Args:
        namespace: RDF Namespace used for all studenten-pruefungsstatistik concept URIs.

    Returns:
        An rdflib Graph containing the complete SKOS vocabulary.
    """
    fg_df = pd.read_csv("destatis_studierende_23/fg.csv", dtype=str)
    fg_df["id"] = fg_df["id"].str.zfill(2)
    stb_df = pd.read_csv("destatis_studierende_23/stb.csv", dtype=str)
    stb_df["id"] = stb_df["id"].str.zfill(2)
    stb_df["parent_id"] = stb_df["parent_id"].str.zfill(2)
    stf_df = pd.read_csv("destatis_studierende_23/stf.csv", dtype=str)
    stf_df["id"] = stf_df["id"].str.zfill(3)
    stf_df["parent_id"] = stf_df["parent_id"].str.zfill(2)
    stf_df["isced_id"] = stf_df["isced_id"].str.zfill(3)

    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("vann", VANN)
    g.bind("destatisstudierende", namespace)
    g.bind("isced", ISCED)

    # ConceptScheme
    g.add((namespace.scheme, RDF.type, SKOS.ConceptScheme))
    g.add(
        (
            namespace.scheme,
            DCTERMS.title,
            Literal(
                "Systematik der Fächergruppen, Studienbereiche und Studienfächer",
                lang="de",
            ),
        )
    )
    g.add(
        (
            namespace.scheme,
            DCTERMS.title,
            Literal(
                "Classification System of Subject Groups, Study Areas, and Fields of Study",
                lang="en",
            ),
        )
    )
    g.add(
        (
            namespace.scheme,
            DCTERMS.creator,
            Literal("Statistisches Bundesamt", lang="de"),
        )
    )
    g.add((namespace.scheme, DCTERMS.created, Literal("2024-01-11", datatype=XSD.date)))
    g.add(
        (
            namespace.scheme,
            DCTERMS.license,
            URIRef("https://www.govdata.de/dl-de/by-2-0"),
        )
    )
    g.add(
        (
            namespace.scheme,
            DCTERMS.description,
            Literal(
                "SKOS-Version der Systematik der Fächergruppen, Studienbereiche und Studienfächer (Destatis, 2023).",
                lang="de",
            ),
        )
    )
    g.add(
        (
            namespace.scheme,
            DCTERMS.description,
            Literal(
                "SKOS version of the Classification System of Subject Groups, Study Areas, and Fields of Study (Destatis, 2023).",
                lang="en",
            ),
        )
    )
    g.add(
        (
            namespace.scheme,
            VANN.preferredNamespaceUri,
            Literal(str(namespace), datatype=XSD.string),
        )
    )

    # Fächergruppen (FG)
    for _, row in fg_df.iterrows():
        fg_id = row["id"]
        fg_uri = URIRef(f"{namespace}{fg_id}")

        g.add((fg_uri, RDF.type, SKOS.Concept))
        g.add((fg_uri, SKOS.prefLabel, Literal(row["label"], lang="de")))
        g.add((fg_uri, SKOS.notation, Literal(fg_id)))
        g.add((fg_uri, SKOS.topConceptOf, namespace.scheme))
        g.add((namespace.scheme, SKOS.hasTopConcept, fg_uri))
        g.add((fg_uri, SKOS.inScheme, namespace.scheme))

    # Studienbereiche (STB)
    for _, row in stb_df.iterrows():
        stb_id = row["id"]
        fg_id = row["parent_id"]
        stb_uri = URIRef(f"{namespace}{fg_id}.{stb_id}")
        fg_uri = URIRef(f"{namespace}{fg_id}")

        g.add((stb_uri, RDF.type, SKOS.Concept))
        g.add((stb_uri, SKOS.prefLabel, Literal(row["label"], lang="de")))
        g.add((stb_uri, SKOS.notation, Literal(stb_id)))
        g.add((stb_uri, SKOS.broader, fg_uri))
        g.add((fg_uri, SKOS.narrower, stb_uri))
        g.add((stb_uri, SKOS.inScheme, namespace.scheme))

    # Studienfächer (STF)
    for _, row in stf_df.iterrows():
        stf_id = row["id"]
        stb_id = row["parent_id"]
        fg_id = stb_df.query(f"id == '{stb_id}'")["parent_id"].values[0]
        stf_uri = URIRef(f"{namespace}{fg_id}.{stb_id}.{stf_id}")
        stb_uri = URIRef(f"{namespace}{fg_id}.{stb_id}")
        isced_uri = URIRef(f"{ISCED}{row['isced_id']}")

        g.add((stf_uri, RDF.type, SKOS.Concept))
        g.add((stf_uri, SKOS.prefLabel, Literal(row["label"], lang="de")))
        g.add((stf_uri, SKOS.notation, Literal(stf_id)))
        g.add((stf_uri, SKOS.broader, stb_uri))
        g.add((stb_uri, SKOS.narrower, stf_uri))
        g.add((stf_uri, SKOS.inScheme, namespace.scheme))
        g.add((stf_uri, SKOS.exactMatch, isced_uri))

    print("SKOS hierarchy built (studierende).")

    # --- Enrich with English labels ---
    source_graph = Graph()
    source_graph.parse(
        "destatis_studierende_23/hochschulfaechersystematik.ttl", format="turtle"
    )
    missing_df = pd.read_csv(
        "destatis_studierende_23/missing_translations.csv", dtype=str
    )

    for concept in g.subjects(RDF.type, SKOS.Concept):
        notation = next((n for n in g.objects(concept, SKOS.notation)), None)
        de_label = next(
            (l for l in g.objects(concept, SKOS.prefLabel) if l.language == "de"), None
        )
        if not (notation and de_label):
            continue

        en_label = _find_en_label_in_source(source_graph, notation, de_label)
        if en_label:
            print(f"Matched: {notation} | {de_label} ~ {en_label}")
            g.add((concept, SKOS.prefLabel, Literal(en_label, lang="en")))
        else:
            fallback_row = missing_df[missing_df["notation"] == str(notation)]
            if not fallback_row.empty:
                en_translation = fallback_row.iloc[0]["en"]
                g.add((concept, SKOS.prefLabel, Literal(en_translation, lang="en")))
                print(f"CSV fallback used: {notation} | {de_label} → {en_translation}")

    print("\nConcepts without English translation:")
    for concept in g.subjects(RDF.type, SKOS.Concept):
        if not any(l.language == "en" for l in g.objects(concept, SKOS.prefLabel)):
            notation = next(g.objects(concept, SKOS.notation), None)
            de_label = next(
                (l for l in g.objects(concept, SKOS.prefLabel) if l.language == "de"),
                None,
            )
            print(f"  Missing EN: {notation} | {de_label}")

    return g


def _find_en_label_in_source(
    source_graph: Graph, notation: str, de_label: str
) -> str | None:
    """
    Searches source_graph for a concept whose notation and German label fuzzy-match
    the given values, and returns its English label if found.

    Args:
        source_graph: Reference graph containing bilingual labels.
        notation:     Notation string to match exactly.
        de_label:     German label used for fuzzy matching (threshold: 85).

    Returns:
        The English label string, or None if no match was found.
    """
    for source_concept in source_graph.subjects(RDF.type, SKOS.Concept):
        source_notation = next(
            (n for n in source_graph.objects(source_concept, SKOS.notation)), None
        )
        source_de_label = next(
            (
                l
                for l in source_graph.objects(source_concept, SKOS.prefLabel)
                if l.language == "de"
            ),
            None,
        )
        source_en_label = next(
            (
                l
                for l in source_graph.objects(source_concept, SKOS.prefLabel)
                if l.language == "en"
            ),
            None,
        )
        if not (source_notation and source_de_label and source_en_label):
            continue
        if (
            str(notation) == str(source_notation)
            and fuzz.token_sort_ratio(str(de_label), str(source_de_label)) >= 85
        ):
            return str(source_en_label)
    return None


if __name__ == "__main__":
    from rdflib import Namespace as _Namespace

    _ns = _Namespace("https://rue-a.github.io/come2data-skohub/studierende/")
    create_stud_skos(_ns).serialize(
        "destatis_studierende_23/destatis_studierende_skos.ttl", format="turtle"
    )
