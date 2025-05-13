# %%
import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal, XSD
from rdflib.namespace import RDF, SKOS, DCTERMS

# Basis-URL
HOSTING_DOMAIN = "https://rue-a.github.io/come2data-skohub"
CONCEPTS_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik"
)
BASE_URL = f"{HOSTING_DOMAIN}/{CONCEPTS_DOMAIN}"

# CSV-Dateien laden
fg_df = pd.read_csv("studierende_23/fg.csv", dtype=str)
fg_df["id"] = fg_df["id"].str.zfill(2)
stb_df = pd.read_csv("studierende_23/stb.csv", dtype=str)
stb_df["id"] = stb_df["id"].str.zfill(2)
stb_df["parent_id"] = stb_df["parent_id"].str.zfill(2)
stf_df = pd.read_csv("studierende_23/stf.csv", dtype=str)
stf_df["id"] = stf_df["id"].str.zfill(3)
stf_df["parent_id"] = stf_df["parent_id"].str.zfill(2)
stf_df["isced_id"] = stf_df["isced_id"].str.zfill(4)


# RDF Graph vorbereiten
g = Graph()
DESTATIS = Namespace(BASE_URL + "/")
ISCED = Namespace("https://publications.europa.eu/resource/authority/snb/isced-f/")
g.bind("skos", SKOS)
g.bind("dcterms", DCTERMS)
g.bind("destatis", DESTATIS)
g.bind("isced", ISCED)


# ConceptScheme erzeugen
g.add((DESTATIS.scheme, RDF.type, SKOS.ConceptScheme))
g.add(
    (
        DESTATIS.scheme,
        DCTERMS.title,
        Literal(
            "Systematik der Fächergruppen, Studienbereiche und Studienfächer",
            lang="de",
        ),
    )
)
g.add(
    (
        DESTATIS.scheme,
        DCTERMS.title,
        Literal(
            "Classification System of Subject Groups, Study Areas, and Fields of Study",
            lang="en",
        ),
    )
)

g.add((DESTATIS.scheme, DCTERMS.creator, Literal("Statistisches Bundesamt", lang="de")))
g.add((DESTATIS.scheme, DCTERMS.created, Literal("2024-01-11", datatype=XSD.date)))
g.add((DESTATIS.scheme, DCTERMS.license, Literal("Unbekannt", lang="de")))

# Fächergruppen (FG)
for _, row in fg_df.iterrows():
    fg_id = row["id"]
    fg_label = row["label"]
    fg_uri = URIRef(f"{DESTATIS}{fg_id}")

    g.add((fg_uri, RDF.type, SKOS.Concept))
    g.add((fg_uri, SKOS.prefLabel, Literal(fg_label, lang="de")))
    g.add((fg_uri, SKOS.notation, Literal(fg_id)))
    g.add((fg_uri, SKOS.topConceptOf, DESTATIS.scheme))
    g.add((DESTATIS.scheme, SKOS.hasTopConcept, fg_uri))
    g.add((fg_uri, SKOS.inScheme, DESTATIS.scheme))


# Studienbereiche (STB)
for _, row in stb_df.iterrows():
    luf_id = row["id"]
    luf_label = row["label"]
    fg_id = row["parent_id"]
    luf_uri = URIRef(f"{DESTATIS}{fg_id}.{luf_id}")
    fg_uri = URIRef(f"{DESTATIS}{fg_id}")

    g.add((luf_uri, RDF.type, SKOS.Concept))
    g.add((luf_uri, SKOS.prefLabel, Literal(luf_label, lang="de")))
    g.add((luf_uri, SKOS.notation, Literal(f"{luf_id}")))
    g.add((luf_uri, SKOS.broader, fg_uri))
    g.add((fg_uri, SKOS.narrower, luf_uri))
    g.add((luf_uri, SKOS.inScheme, DESTATIS.scheme))


# Studienfächer (STF)
for _, row in stf_df.iterrows():
    fgb_id = row["id"]
    fgb_label = row["label"]
    luf_id = row["parent_id"]
    fg_id = stb_df.query(f"id == '{luf_id}'")["parent_id"].values[0]
    isced_id = row["isced_id"]

    fgb_uri = URIRef(f"{DESTATIS}{fg_id}.{luf_id}.{fgb_id}")
    luf_uri = URIRef(f"{DESTATIS}{fg_id}.{luf_id}")
    isced_uri = URIRef(f"{ISCED}{isced_id}")

    g.add((fgb_uri, RDF.type, SKOS.Concept))
    g.add((fgb_uri, SKOS.prefLabel, Literal(fgb_label, lang="de")))
    g.add((fgb_uri, SKOS.notation, Literal(f"{fgb_id}")))
    g.add((fgb_uri, SKOS.broader, luf_uri))
    g.add((luf_uri, SKOS.narrower, fgb_uri))
    g.add((fgb_uri, SKOS.inScheme, DESTATIS.scheme))
    g.add((fgb_uri, SKOS.exactMatch, isced_uri))


# g.serialize("destatis_personal_skos.ttl", format="turtle")
print("SKOS-Hierarchie wurde erfolgreich erstellt.")

# %%
# translations

from fuzzywuzzy import fuzz

source_graph = Graph()
source_graph.parse("studierende_23/hochschulfaechersystematik.ttl", format="turtle")

# Load missing translations from CSV
missing_df = pd.read_csv("studierende_23/missing_translations.csv", dtype=str)


# Iterate over concepts in destatis graph
for concept in g.subjects(RDF.type, SKOS.Concept):
    notation = next((n for n in g.objects(concept, SKOS.notation)), None)
    de_label = next(
        (l for l in g.objects(concept, SKOS.prefLabel) if l.language == "de"),
        None,
    )

    if not (notation and de_label):
        continue

    matched = False
    # Search for match in source graph
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
            print(f"Matched: {notation} | {de_label} ~ {source_de_label}")
            g.add((concept, SKOS.prefLabel, Literal(str(source_en_label), lang="en")))
            matched = True
            break

    # If not matched, check CSV fallback
    if not matched:
        row = missing_df[missing_df["notation"] == str(notation)]
        if not row.empty:
            en_translation = row.iloc[0]["en"]
            g.add((concept, SKOS.prefLabel, Literal(en_translation, lang="en")))
            print(f"CSV fallback used: {notation} | {de_label} → {en_translation}")

# Print concepts without English label
print("\nConcepts without English translation:")
for concept in g.subjects(RDF.type, SKOS.Concept):
    has_en = any(l.language == "en" for l in g.objects(concept, SKOS.prefLabel))
    if not has_en:
        notation = next(g.objects(concept, SKOS.notation), None)
        de_label = next(
            (l for l in g.objects(concept, SKOS.prefLabel) if l.language == "de"),
            None,
        )
        print(f"Missing EN: {notation} | {de_label}")

# Serialize result
g.serialize("studierende_23/destatis_studierende_skos.ttl", format="turtle")
