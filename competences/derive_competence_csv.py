#!/usr/bin/env python3
"""
Build a hierarchical CSV (ID, label, parent ID) from the first three columns:
Kompetenzfeld, Teilkompetenz, Lehrinhalte.

The order is hierarchical:
01, 01.001, 01.001.0001, 01.001.0002, … 01.002, …, 02, 02.001, 02.001.0001, …
"""

import pandas as pd
from collections import OrderedDict

# ---------- CONFIG ----------
INPUT_PATH = "20250704_Framework_DataLiteracy_C2D_v05.xlsx"  # your Excel file
SHEET = 0  # can also be sheet name, e.g. "Sheet1"
OUTPUT_CSV = "competence_hierarchy.csv"
# ----------------------------


def find_header_row(xls_path: str, sheet) -> int:
    probe = pd.read_excel(xls_path, sheet_name=sheet, header=None, nrows=30)
    target = ("Kompetenzfeld", "Teilkompetenz", "Lehrinhalte")
    for i in range(len(probe)):
        row_vals = tuple(
            (str(v).strip() if pd.notna(v) else "") for v in probe.iloc[i, :3].tolist()
        )
        if row_vals == target:
            return i
    return 6  # fallback that matches your workbook


def load_three_columns(xls_path: str, sheet) -> pd.DataFrame:
    hdr = find_header_row(xls_path, sheet)
    df = pd.read_excel(xls_path, sheet_name=sheet, header=hdr)
    df = df.iloc[:, :3].copy()
    df.columns = ["Kompetenzfeld", "Teilkompetenz", "Lehrinhalte"]

    # Remove repeated header row
    mask_header_repeat = df["Kompetenzfeld"].astype(str).str.strip().eq(
        "Kompetenzfeld"
    ) & df["Teilkompetenz"].astype(str).str.strip().eq("Teilkompetenz")
    df = df[~mask_header_repeat]

    # Normalize
    for col in ["Kompetenzfeld", "Teilkompetenz", "Lehrinhalte"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].mask(df[col].isin(["", "nan"]), other=pd.NA)

    # Forward-fill hierarchy
    df["Kompetenzfeld"] = df["Kompetenzfeld"].ffill()
    df["Teilkompetenz"] = df["Teilkompetenz"].ffill()
    df = df.dropna(subset=["Kompetenzfeld"])

    return df


def build_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    kompetenzfelder = OrderedDict()
    teilkompetenzen = OrderedDict()
    lehrinhalte_map = OrderedDict()

    # Level 1
    for kf in df["Kompetenzfeld"]:
        if pd.isna(kf):
            continue
        kf = str(kf)
        if kf not in kompetenzfelder:
            kompetenzfelder[kf] = f"{len(kompetenzfelder) + 1:02d}"

    # Level 2
    for _, row in df.dropna(subset=["Teilkompetenz"]).iterrows():
        kf = str(row["Kompetenzfeld"])
        tk = str(row["Teilkompetenz"])
        key = (kf, tk)
        if key not in teilkompetenzen:
            parent_id = kompetenzfelder[kf]
            count_tk_under_kf = sum(1 for (pkf, _tk) in teilkompetenzen if pkf == kf)
            teilkompetenzen[key] = f"{parent_id}.{count_tk_under_kf + 1:02d}"

    # Level 3
    for _, row in df.dropna(subset=["Lehrinhalte"]).iterrows():
        kf = str(row["Kompetenzfeld"])
        tk = str(row["Teilkompetenz"]) if pd.notna(row["Teilkompetenz"]) else None
        li = str(row["Lehrinhalte"]).strip()
        if li.lower() in {"inhalte", "lehrinhalte"}:
            continue

        key_tk = (kf, tk)
        if key_tk not in teilkompetenzen and tk is not None:
            parent_id = kompetenzfelder[kf]
            count_tk_under_kf = sum(1 for (pkf, _tk) in teilkompetenzen if pkf == kf)
            teilkompetenzen[key_tk] = f"{parent_id}.{count_tk_under_kf + 1:02d}"

        tk_id = teilkompetenzen.get(key_tk)
        if tk_id is None:
            continue

        key_li = (kf, tk, li)
        if key_li not in lehrinhalte_map:
            count_li_under_tk = sum(
                1 for (pkf, ptk, _pli) in lehrinhalte_map if (pkf, ptk) == key_tk
            )
            lehrinhalte_map[key_li] = f"{tk_id}.{count_li_under_tk + 1:02d}"

    # Ordered rows: KF → TK → LI
    rows = []
    for kf_label, kf_id in kompetenzfelder.items():
        rows.append({"ID": kf_id, "label": kf_label, "parent ID": ""})

        for (kf, tk_label), tk_id in teilkompetenzen.items():
            if kf != kf_label:
                continue
            rows.append({"ID": tk_id, "label": tk_label, "parent ID": kf_id})

            for (pkf, ptk, li_label), li_id in lehrinhalte_map.items():
                if (pkf, ptk) == (kf_label, tk_label):
                    rows.append({"ID": li_id, "label": li_label, "parent ID": tk_id})

    return pd.DataFrame(rows, columns=["ID", "label", "parent ID"])


def main():
    df = load_three_columns(INPUT_PATH, SHEET)
    out_df = build_hierarchy(df)
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"Wrote {len(out_df)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
