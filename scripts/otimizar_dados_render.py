from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
BASE = DATA / "base_consulta_hs6_pais_completa.parquet"
CATALOGO_PAISES = DATA / "catalogo_paises.json"


def main() -> None:
    base = pd.read_parquet(BASE)
    base["HS6"] = base["HS6"].astype("string").str.zfill(6)
    base["ISO3"] = base["ISO3"].astype("string").str.upper()
    base = base.sort_values(["HS6", "score_exportai", "ISO3"], ascending=[True, False, True])

    tabela = pa.Table.from_pandas(base, preserve_index=False)
    pq.write_table(tabela, BASE, compression="snappy", row_group_size=5_000)

    paises = (
        base[["ISO3", "pais"]]
        .dropna(subset=["ISO3"])
        .drop_duplicates("ISO3")
        .sort_values("ISO3")
        .to_dict(orient="records")
    )
    CATALOGO_PAISES.write_text(json.dumps(paises, ensure_ascii=False, indent=2), encoding="utf-8")

    arquivo = pq.ParquetFile(BASE)
    print(f"Base otimizada: {arquivo.metadata.num_rows} linhas, {arquivo.metadata.num_row_groups} row groups")
    print(f"Catalogo de paises: {len(paises)} registros")


if __name__ == "__main__":
    main()
