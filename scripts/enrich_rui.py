"""Enrich DB with collaboratori, cariche, collab accessori, resp distrib for complete profiles."""
import csv, os, sys
from pathlib import Path
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

csv.field_size_limit(sys.maxsize)
DATA = Path("/app/rui_data")
load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def read_csv(name):
    with open(DATA / name, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=";"):
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def g(r, k):
    return (r.get(k) or "").strip()


def main():
    # COLLABORATORI: link intermediary (A/B/D) -> collaborators (E). Store both directions.
    coll = db.collaboratori
    coll.drop()
    batch = []
    total = 0
    for r in read_csv("ELENCO_COLLABORATORI.csv"):
        inter = g(r, "NUM_ISCR_INTERMEDIARIO")
        c1 = g(r, "NUM_ISCR_COLLABORATORI_I_LIV")
        c2 = g(r, "NUM_ISCR_COLLABORATORI_II_LIV")
        collab = c2 or c1
        if not inter or not collab:
            continue
        batch.append({
            "intermediario": inter,
            "collaboratore": collab,
            "livello": g(r, "LIVELLO"),
            "qualifica": g(r, "QUALIFICA_RAPPORTO"),
        })
        if len(batch) >= 10000:
            coll.insert_many(batch); total += len(batch); batch = []
    if batch:
        coll.insert_many(batch); total += len(batch)
    coll.create_index([("intermediario", ASCENDING)])
    coll.create_index([("collaboratore", ASCENDING)])
    print("collaboratori:", total)

    # CARICHE: responsabile activity linking PF <-> PG
    car = db.cariche
    car.drop()
    cbatch = []
    for r in read_csv("ELENCO_CARICHE.csv"):
        pf = g(r, "NUMERO_ISCRIZIONE_RUI_PF")
        pg = g(r, "NUMERO_ISCRIZIONE_RUI_PG")
        if not pf and not pg:
            continue
        cbatch.append({
            "pf": pf, "pg": pg,
            "qualifica": g(r, "QUALIFICA_INTERMEDIARIO"),
            "responsabile": g(r, "RESPONSABILE"),
        })
    if cbatch:
        car.insert_many(cbatch)
    car.create_index([("pf", ASCENDING)])
    car.create_index([("pg", ASCENDING)])
    print("cariche:", len(cbatch))

    # COLLAB ACCESSORI extra info
    acc = db.collab_accessori
    acc.drop()
    abatch = []
    for r in read_csv("ELENCO_COLLABACCESSORI.csv"):
        num = g(r, "NUMERO_ISCRIZIONE_E")
        if not num:
            continue
        abatch.append({
            "rui_number": num,
            "ragione_sociale": g(r, "RAGIONE_SOCIALE"),
            "cognome_nome": g(r, "COGNOME_NOME"),
            "sede_legale": g(r, "SEDE_LEGALE"),
            "luogo_nascita": g(r, "LUOGO_NASCITA"),
        })
    if abatch:
        acc.insert_many(abatch)
    acc.create_index([("rui_number", ASCENDING)])
    print("collab_accessori:", len(abatch))

    # RESP DISTRIB SEZ D
    rd = db.resp_distrib
    rd.drop()
    rbatch = []
    for r in read_csv("ELENCO_RESP_DISTRIB_SEZ_D.csv"):
        num = g(r, "NUMERO_ISCRIZIONE_D")
        if not num:
            continue
        rbatch.append({
            "rui_number": num,
            "ragione_sociale": g(r, "RAGIONE_SOCIALE"),
            "responsabile": g(r, "COGNOME_NOME_RESPONSABILE"),
        })
    if rbatch:
        rd.insert_many(rbatch)
    rd.create_index([("rui_number", ASCENDING)])
    print("resp_distrib:", len(rbatch))
    print("DONE")


if __name__ == "__main__":
    main()
