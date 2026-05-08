from rdflib import Graph, Namespace
from rdflib.namespace import SKOS
import pandas as pd
from pathlib import Path
import re

# --- load graph ---
COMBINED_FILE = "published_vocabs/destatis_combined_skos.ttl"
combined = Graph()
combined.parse(COMBINED_FILE, format="turtle")

# Namespaces
HOSTING_DOMAIN = "https://rue-a.github.io/come2data-skohub"
CONCEPTS_PERS_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/personal-stellenstatistik"
)
DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")


# --- helpers ---
def shorten_uri(uri: str) -> str:
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]


# Hierarchical sort key
_pat = re.compile(r"^(?P<top>\d{2})(?:\.(?P<mid>\d{3}))?(?:\.(?P<bot>\d{4}))?$")


def sort_key(concept_id: str):
    m = _pat.match(concept_id.strip())
    if not m:
        return (10**9, 10**9, 10**9, 10**9)  # push non-conforming to end
    top = int(m.group("top"))
    mid = m.group("mid")
    bot = m.group("bot")
    if mid is None:
        return (top, -1, 0, -1)  # NN first
    if bot is None:
        return (top, int(mid), 1, -1)  # then NN.MMM
    return (top, int(mid), 2, int(bot))  # then NN.MMM.QQQQ (by QQQQ)


# --- build table ---
rows = []
for c_pers in set(combined.subjects(SKOS.prefLabel, None)):
    u = str(c_pers)
    if not u.startswith(str(DESTATIS_PERS)):
        continue

    cid = shorten_uri(u)

    label_de = next(
        (
            l
            for l in combined.objects(c_pers, SKOS.prefLabel)
            if getattr(l, "language", None) == "de"
        ),
        None,
    )
    label_en = next(
        (
            l
            for l in combined.objects(c_pers, SKOS.prefLabel)
            if getattr(l, "language", None) == "en"
        ),
        None,
    )

    broader = next(combined.objects(c_pers, SKOS.broader), None)
    broader_id = shorten_uri(str(broader)) if broader else ""

    rows.append(
        {
            "concept_id": cid,
            "label_de": str(label_de) if label_de else "",
            "label_en": str(label_en) if label_en else "",
            "parent_id": broader_id,
        }
    )

df = pd.DataFrame(rows)

# --- hierarchical sort ---
df["__key"] = df["concept_id"].apply(sort_key)
df = df.sort_values(by="__key").drop(columns="__key")

# Save
out_file = Path("published_vocabs/pers_table.csv")
out_file.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_file, index=False, encoding="utf-8")
print(f"Table written to {out_file}")
