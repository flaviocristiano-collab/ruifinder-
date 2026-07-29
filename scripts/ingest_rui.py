"""Ingest IVASS RUI public CSVs into MongoDB with geocoded offices."""
import csv, json, os, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient, ASCENDING, TEXT
from dotenv import load_dotenv

csv.field_size_limit(sys.maxsize)
DATA = Path("/app/rui_data")
load_dotenv("/app/backend/.env")

client = MongoClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

SECTION_LABELS = {
    "A": "Agenti",
    "B": "Broker / Mediatori",
    "C": "Produttori diretti",
    "D": "Banche e Intermediari finanziari",
    "E": "Collaboratori / Addetti",
    "F": "Imprese UE (stabilimento)",
    "U": "Addetti fuori sede",
}


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().strip()


def read_csv(name, delimiter=";"):
    path = DATA / name
    with open(path, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=delimiter):
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def load_coords():
    with open(DATA / "comune_coords.json", encoding="utf-8") as f:
        return json.load(f)


def main():
    coords = load_coords()
    print(f"Loaded {len(coords)} comune coordinates")

    # --- SEDI grouped by intermediary ---
    sedi_by_int = {}
    for r in read_csv("ELENCO_SEDI.csv"):
        rui = (r.get("NUMERO_ISCRIZIONE_INT") or "").strip()
        if not rui:
            continue
        comune = (r.get("COMUNE_SEDE") or "").strip()
        prov = (r.get("PROVINCIA_SEDE") or "").strip()
        c = coords.get(norm(comune))
        sede = {
            "tipo": (r.get("TIPO_SEDE") or "").strip(),
            "comune": comune,
            "provincia": prov,
            "cap": (r.get("CAP_SEDE") or "").strip(),
            "indirizzo": (r.get("INDIRIZZO_SEDE") or "").strip(),
            "lat": c["lat"] if c else None,
            "lng": c["lng"] if c else None,
        }
        sedi_by_int.setdefault(rui, []).append(sede)
    print(f"Sedi for {len(sedi_by_int)} intermediaries")

    # --- MANDATI grouped ---
    mand_by_int = {}
    for r in read_csv("ELENCO_MANDATI.csv"):
        rui = (r.get("MATRICOLA") or "").strip()
        if not rui:
            continue
        mand_by_int.setdefault(rui, []).append({
            "codice": (r.get("CODICE_COMPAGNIA") or "").strip(),
            "ragione_sociale": (r.get("RAGIONE_SOCIALE") or "").strip(),
        })
    print(f"Mandati for {len(mand_by_int)} intermediaries")

    # --- WEBSITES grouped ---
    web_by_int = {}
    for r in read_csv("ELENCO_SITO_INTERNET.csv"):
        rui = (r.get("NUMERO_ISCRIZIONE") or "").strip()
        url = (r.get("WEB_URL") or "").strip()
        if rui and url:
            web_by_int.setdefault(rui, []).append(url)
    print(f"Websites for {len(web_by_int)} intermediaries")

    # --- INTERMEDIARI ---
    coll = db.intermediari
    coll.drop()
    batch = []
    total = 0
    for r in read_csv("ELENCO_INTERMEDIARI.csv"):
        rui = r.get("NUMERO_ISCRIZIONE_RUI", "").strip()
        if not rui:
            continue
        section = rui[0].upper()
        cognome_nome = (r.get("COGNOME_NOME") or "").strip()
        ragione = (r.get("RAGIONE_SOCIALE") or "").strip()
        is_person = bool(cognome_nome) and not ragione
        display_name = cognome_nome if cognome_nome else ragione
        display_name = " ".join(display_name.split())

        sedi = sedi_by_int.get(rui, [])
        mandati = mand_by_int.get(rui, [])
        websites = web_by_int.get(rui, [])

        prov = (r.get("PROVINCIA_NASCITA") or "").strip()
        comune = (r.get("COMUNE_NASCITA") or "").strip()
        loc = None
        for s in sedi:
            if s["lat"] is not None:
                loc = {"lat": s["lat"], "lng": s["lng"], "comune": s["comune"], "provincia": s["provincia"]}
                break
        if sedi:
            prov = sedi[0]["provincia"] or prov
            comune = sedi[0]["comune"] or comune
        if loc is None:
            c = coords.get(norm(comune))
            if c:
                loc = {"lat": c["lat"], "lng": c["lng"], "comune": comune, "provincia": prov}

        doc = {
            "rui_number": rui,
            "section": section,
            "section_label": SECTION_LABELS.get(section, section),
            "display_name": display_name,
            "name_norm": norm(display_name),
            "is_person": is_person,
            "registration_date": (r.get("DATA_ISCRIZIONE") or "").strip(),
            "inoperativo": (r.get("INOPERATIVO") or "0").strip() == "1",
            "stato": (r.get("STATO") or "").strip(),
            "comune_nascita": (r.get("COMUNE_NASCITA") or "").strip(),
            "provincia_nascita": (r.get("PROVINCIA_NASCITA") or "").strip(),
            "data_nascita": (r.get("DATA_NASCITA") or "").strip(),
            "attivita_a": (r.get("ATTIVITA_ESERCITATA_SEZ_A") or "").strip(),
            "attivita_b": (r.get("ATTIVITA_ESERCITATA_SEZ_B") or "").strip(),
            "provincia": (prov or "").upper(),
            "comune": comune,
            "loc": loc,
            "sedi": sedi,
            "mandati": mandati,
            "mandate_norm": [norm(m["ragione_sociale"]) for m in mandati],
            "websites": websites,
        }
        batch.append(doc)
        if len(batch) >= 5000:
            coll.insert_many(batch)
            total += len(batch)
            batch = []
            print(f"  inserted {total}")
    if batch:
        coll.insert_many(batch)
        total += len(batch)
    print(f"TOTAL intermediari inserted: {total}")

    print("Creating indexes...")
    coll.create_index([("rui_number", ASCENDING)])
    coll.create_index([("section", ASCENDING)])
    coll.create_index([("provincia", ASCENDING)])
    coll.create_index([("comune", ASCENDING)])
    coll.create_index([("name_norm", ASCENDING)])
    coll.create_index([("inoperativo", ASCENDING)])
    print("Done. Counts by section:")
    for s in coll.aggregate([{"$group": {"_id": "$section", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}]):
        print("  ", s["_id"], s["n"])
    client.close()


if __name__ == "__main__":
    main()
