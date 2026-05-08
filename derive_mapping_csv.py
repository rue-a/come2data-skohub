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
CONCEPTS_STUD_DOMAIN = (
    "www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik"
)
DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")
DESTATIS_STUD = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_STUD_DOMAIN}/")


# --- helpers ---
def shorten_uri(uri: str) -> str:
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]


def is_stud_uri(uri: str) -> bool:
    return uri.startswith(str(DESTATIS_STUD))


def is_pers_uri(uri: str) -> bool:
    return uri.startswith(str(DESTATIS_PERS))


# Collect matches w/ aligned IDs ↔ labels, ordered by ID
def collect_matches(subject, predicate):
    id_to_label = {}
    for obj in combined.objects(subject, predicate):
        u = str(obj)
        if not is_pers_uri(u):
            continue
        sid = shorten_uri(u)
        lbl = next(
            (
                l
                for l in combined.objects(obj, SKOS.prefLabel)
                if getattr(l, "language", None) == "de"
            ),
            None,
        )
        id_to_label[sid] = str(lbl) if lbl else ""
    ids = sorted(id_to_label.keys())
    labels = [id_to_label[i] for i in ids]
    return ";".join(ids), ";".join(labels)


# Hierarchical sort key:
#   NN  → (top=NN, mid=-1, depth=0, bot=-1)
#   NN.MMM → (top=NN, mid=MMM, depth=1, bot=-1)
#   NN.MMM.QQQQ → (top=NN, mid=MMM, depth=2, bot=QQQQ)
_pat = re.compile(r"^(?P<top>\d{2})(?:\.(?P<mid>\d{3}))?(?:\.(?P<bot>\d{4}))?$")


def sort_key(stud_id: str):
    m = _pat.match(stud_id.strip())
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
for c_stud in set(combined.subjects(SKOS.prefLabel, None)):
    if not is_stud_uri(str(c_stud)):
        continue

    label_stud = next(
        (
            l
            for l in combined.objects(c_stud, SKOS.prefLabel)
            if getattr(l, "language", None) == "de"
        ),
        None,
    )

    exact_ids, exact_labels = collect_matches(c_stud, SKOS.exactMatch)
    close_ids, close_labels = collect_matches(c_stud, SKOS.closeMatch)

    rows.append(
        {
            "studierende_concept_id": shorten_uri(str(c_stud)),
            "studierende_concept_label": str(label_stud) if label_stud else "",
            "close_match_personal_ids": close_ids,
            "close_match_personal_labels": close_labels,
            "exact_match_personal_ids": exact_ids,
            "exact_match_personal_labels": exact_labels,
        }
    )

df = pd.DataFrame(rows)

# --- hierarchical sort by the first column ---
df["__key"] = df["studierende_concept_id"].apply(sort_key)
df = df.sort_values(by="__key").drop(columns="__key")

# Save
out_file = Path("published_vocabs/match_table.csv")
out_file.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_file, index=False, encoding="utf-8")
print(f"Table written to {out_file}")
