from destatis_personal_23.pers_tables2skos import create_pers_skos
from destatis_studierende_23.stud_tables2skos import create_stud_skos
from destatis_mapping.mapping import create_mapping
from rdflib import Namespace

# ---------- Config ----------
HOSTING_DOMAIN = "https://rue-a.github.io/come2data-skohub"
CONCEPTS_PERS_DOMAIN = "personal"
CONCEPTS_STUD_DOMAIN = "studierende"

DESTATIS_PERS = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_PERS_DOMAIN}/")
DESTATIS_STUD = Namespace(f"{HOSTING_DOMAIN}/{CONCEPTS_STUD_DOMAIN}/")

MAPPING_TABLE = "destatis_mapping/mapping_table.csv"
OUT_PERSONAL = "published_vocabs/destatis_personal_skos.ttl"
OUT_STUD = "published_vocabs/destatis_studierende_skos.ttl"
OUT_COMBINED = "published_vocabs/destatis_combined_skos.ttl"
# ----------------------------

g_personal = create_pers_skos(DESTATIS_PERS)
g_studierende = create_stud_skos(DESTATIS_STUD)
create_mapping(
    g_personal,
    g_studierende,
    DESTATIS_PERS,
    DESTATIS_STUD,
    MAPPING_TABLE,
    OUT_COMBINED,
)
