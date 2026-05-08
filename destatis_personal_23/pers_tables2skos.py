import pandas as pd
from fuzzywuzzy import fuzz
from rdflib import Graph, Literal, Namespace, URIRef, XSD
from rdflib.namespace import DCTERMS, RDF, SKOS


def create_pers_skos(namespace: Namespace) -> Graph:
    """
    Builds the SKOS graph for the Destatis personal-stellenstatistik classification.

    Loads the three-level hierarchy (Fächergruppe → Lehr-/Forschungsbereich →
    Fachgebiet) from CSV files, constructs SKOS concepts, and enriches them with
    English labels sourced from a reference TTL file and a manual fallback CSV.

    Args:
        namespace: RDF Namespace used for all personal-stellenstatistik concept URIs.

    Returns:
        An rdflib Graph containing the complete SKOS vocabulary.
    """
    fg_df = pd.read_csv("destatis_personal_23/fg.csv", dtype=str)
    fg_df["id"] = fg_df["id"].str.zfill(2)
    luf_df = pd.read_csv("destatis_personal_23/luf.csv", dtype=str)
    luf_df["id"] = luf_df["id"].str.zfill(3)
    luf_df["parent_id"] = luf_df["parent_id"].str.zfill(2)
    fgb_df = pd.read_csv("destatis_personal_23/fgb.csv", dtype=str)
    fgb_df["id"] = fgb_df["id"].str.zfill(4)
    fgb_df["parent_id"] = fgb_df["parent_id"].str.zfill(3)

    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("destatispersonal", namespace)

    # ConceptScheme
    g.add((namespace.scheme, RDF.type, SKOS.ConceptScheme))
    g.add(
        (
            namespace.scheme,
            DCTERMS.title,
            Literal(
                "Systematik der Fächergruppen, Lehr- und Forschungsbereiche und Fachgebiete",
                lang="de",
            ),
        )
    )
    g.add(
        (
            namespace.scheme,
            DCTERMS.title,
            Literal(
                "Classification System of Subject Groups, Teaching and Research Areas, and Fields of Expertise",
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
            Literal(
                "© Statistisches Bundesamt (Destatis), 2024. Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenagabe gestatted.",
                lang="de",
            ),
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

    # Lehr- und Forschungsbereiche (LuF)
    for _, row in luf_df.iterrows():
        luf_id = row["id"]
        fg_id = row["parent_id"]
        luf_uri = URIRef(f"{namespace}{fg_id}.{luf_id}")
        fg_uri = URIRef(f"{namespace}{fg_id}")

        g.add((luf_uri, RDF.type, SKOS.Concept))
        g.add((luf_uri, SKOS.prefLabel, Literal(row["label"], lang="de")))
        g.add((luf_uri, SKOS.notation, Literal(luf_id)))
        g.add((luf_uri, SKOS.broader, fg_uri))
        g.add((fg_uri, SKOS.narrower, luf_uri))
        g.add((luf_uri, SKOS.inScheme, namespace.scheme))

    # Fachgebiete (FGB)
    for _, row in fgb_df.iterrows():
        fgb_id = row["id"]
        luf_id = row["parent_id"]
        fg_id = luf_df.query(f"id == '{luf_id}'")["parent_id"].values[0]
        fgb_uri = URIRef(f"{namespace}{fg_id}.{luf_id}.{fgb_id}")
        luf_uri = URIRef(f"{namespace}{fg_id}.{luf_id}")

        g.add((fgb_uri, RDF.type, SKOS.Concept))
        g.add((fgb_uri, SKOS.prefLabel, Literal(row["label"], lang="de")))
        g.add((fgb_uri, SKOS.notation, Literal(fgb_id)))
        g.add((fgb_uri, SKOS.broader, luf_uri))
        g.add((luf_uri, SKOS.narrower, fgb_uri))
        g.add((fgb_uri, SKOS.inScheme, namespace.scheme))

    print("SKOS hierarchy built (personal).")

    # --- Enrich with English labels ---
    source_graph = Graph()
    source_graph.parse(
        "destatis_personal_23/faecherklassifikation_skos_en.ttl", format="turtle"
    )
    missing_df = pd.read_csv("destatis_personal_23/missing_translations.csv", dtype=str)

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

    _ns = _Namespace("https://rue-a.github.io/come2data-skohub/personal/")
    create_pers_skos(_ns).serialize(
        "destatis_personal_23/destatis_personal_skos.ttl", format="turtle"
    )
