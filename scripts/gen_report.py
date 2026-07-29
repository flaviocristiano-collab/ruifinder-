"""Generate a professional 'Scheda Intermediario' PDF report from RUI data."""
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                HRFlowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

INK = colors.HexColor("#0F0F11")
SIGNAL = colors.HexColor("#FF4500")
ELECTRIC = colors.HexColor("#0055FF")
MUTED = colors.HexColor("#6B6B72")
LIGHT = colors.HexColor("#F4F4F5")
BORDER = colors.HexColor("#E4E4E7")

d = json.load(open("/tmp/example.json"))

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontName="Helvetica-Bold",
                    fontSize=22, textColor=INK, spaceAfter=2, leading=25)
OVER = ParagraphStyle("OVER", fontName="Helvetica-Bold", fontSize=7.5,
                      textColor=SIGNAL, spaceAfter=6, leading=10)
LABEL = ParagraphStyle("LABEL", fontName="Helvetica-Bold", fontSize=7,
                       textColor=MUTED, leading=10)
VAL = ParagraphStyle("VAL", fontName="Helvetica", fontSize=10, textColor=INK, leading=13)
SEC = ParagraphStyle("SEC", fontName="Helvetica-Bold", fontSize=12, textColor=INK,
                     spaceBefore=14, spaceAfter=8, leading=14)
CELL = ParagraphStyle("CELL", fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11)
CELLB = ParagraphStyle("CELLB", fontName="Helvetica-Bold", fontSize=8.5, textColor=INK, leading=11)
SMALL = ParagraphStyle("SMALL", fontName="Helvetica", fontSize=7.5, textColor=MUTED, leading=10)

SECTION_LABELS = {"A": "Agenti", "B": "Broker / Mediatori", "C": "Produttori diretti",
                  "D": "Banche e Intermediari finanziari", "E": "Collaboratori / Addetti",
                  "U": "Addetti fuori sede"}

story = []

# ---- Header band
title = d["display_name"]
sec = d["section"]
stato = "OPERATIVO" if not d.get("inoperativo") else "INATTIVO"
stato_col = colors.HexColor("#128A54") if not d.get("inoperativo") else colors.HexColor("#B45309")

header_tbl = Table([[
    Paragraph("REGISTRO UNICO DEGLI INTERMEDIARI · IVASS", OVER),
]], colWidths=[170*mm])
header_tbl.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
story.append(header_tbl)
story.append(Paragraph(title, H1))
meta = Table([[
    Paragraph(f'<b>SEZ. {sec}</b> · {SECTION_LABELS.get(sec, sec)}', VAL),
    Paragraph(f'<font color="#{stato_col.hexval()[2:]}"><b>● {stato}</b></font>', ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=9, alignment=TA_RIGHT)),
]], colWidths=[120*mm, 50*mm])
meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                          ("LEFTPADDING", (0, 0), (0, 0), 0),
                          ("RIGHTPADDING", (-1, 0), (-1, 0), 0)]))
story.append(meta)
story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=2, color=SIGNAL))
story.append(Spacer(1, 10))


def kv_row(pairs):
    cells = []
    for label, val in pairs:
        cells.append([Paragraph(label.upper(), LABEL), Paragraph(str(val or "—"), VAL)])
    # arrange in 2 columns
    rows = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else [Paragraph("", LABEL), Paragraph("", VAL)]
        rows.append([
            Table([[left[0]], [left[1]]], colWidths=[82*mm]),
            Table([[right[0]], [right[1]]], colWidths=[82*mm]),
        ])
    t = Table(rows, colWidths=[85*mm, 85*mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


# ---- Identificativi
story.append(Paragraph("Dati identificativi", SEC))
story.append(kv_row([
    ("Numero RUI", d["rui_number"]),
    ("Data iscrizione", d.get("registration_date")),
    ("Tipo", "Persona fisica" if d.get("is_person") else "Società"),
    ("Attività (sez. A)", d.get("attivita_a") or "—"),
    ("Comune di nascita", f"{d.get('comune_nascita','')} {('('+d['provincia_nascita']+')') if d.get('provincia_nascita') else ''}".strip() or "—"),
    ("Data di nascita", d.get("data_nascita")),
]))

# ---- Sedi
sedi = d.get("sedi", [])
if sedi:
    story.append(Paragraph(f"Sedi ({len(sedi)})", SEC))
    rows = [[Paragraph("TIPO", LABEL), Paragraph("INDIRIZZO", LABEL),
             Paragraph("COMUNE", LABEL), Paragraph("CAP", LABEL)]]
    for s in sedi:
        rows.append([
            Paragraph((s.get("tipo") or "—"), CELL),
            Paragraph((s.get("indirizzo") or "—"), CELL),
            Paragraph(f"{s.get('comune','')} {('('+s['provincia']+')') if s.get('provincia') else ''}", CELL),
            Paragraph((s.get("cap") or "—"), CELL),
        ])
    t = Table(rows, colWidths=[38*mm, 62*mm, 48*mm, 22*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1, SIGNAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

# ---- Mandati
mand = d.get("mandati", [])
if mand:
    story.append(Paragraph(f"Mandati / Compagnie ({len(mand)})", SEC))
    rows = [[Paragraph("CODICE", LABEL), Paragraph("COMPAGNIA / IMPRESA MANDANTE", LABEL)]]
    for m in mand:
        rows.append([Paragraph(m.get("codice") or "—", CELL),
                     Paragraph(m.get("ragione_sociale") or "—", CELLB)])
    t = Table(rows, colWidths=[30*mm, 140*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1, ELECTRIC),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

# ---- Siti / contatti
web = d.get("websites", [])
if web:
    story.append(Paragraph("Contatti web", SEC))
    for w in web:
        story.append(Paragraph(f'<font color="#0055FF">{w}</font>', VAL))
        story.append(Spacer(1, 2))

# ---- Collaboratori
coll = d.get("collaboratori", [])
if coll:
    story.append(Paragraph(f"Collaboratori / Addetti ({len(coll)})", SEC))
    rows = [[Paragraph("N. RUI", LABEL), Paragraph("NOMINATIVO", LABEL),
             Paragraph("COMUNE", LABEL), Paragraph("STATO", LABEL)]]
    for c in coll:
        st = "Inattivo" if c.get("inoperativo") else "Operativo"
        rows.append([
            Paragraph(c.get("rui") or "—", CELL),
            Paragraph(c.get("name") or "—", CELLB),
            Paragraph(c.get("comune") or "—", CELL),
            Paragraph(st, SMALL),
        ])
    t = Table(rows, colWidths=[30*mm, 78*mm, 42*mm, 20*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
        ("LINEBELOW", (0, 0), (-1, 0), 1, SIGNAL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

# ---- Footer note
story.append(Spacer(1, 16))
story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
story.append(Spacer(1, 4))
gen = datetime.now().strftime("%d/%m/%Y %H:%M")
story.append(Paragraph(
    f"Report generato da <b>RUI Explorer</b> il {gen}. Fonte dati: IVASS — Registro Unico degli "
    f"Intermediari (dati pubblici). Documento a scopo informativo.", SMALL))


def footer(canvas, doc_):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20*mm, 12*mm, "RUI Explorer · Scheda Intermediario")
    canvas.drawRightString(190*mm, 12*mm, f"Pag. {doc_.page}")
    canvas.setFillColor(SIGNAL)
    canvas.rect(20*mm, 15*mm, 170*mm, 0.8, fill=1, stroke=0)
    canvas.restoreState()


doc = SimpleDocTemplate("/app/scheda_intermediario_esempio.pdf", pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=20*mm,
                        title=f"Scheda Intermediario — {title}")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF generated:", "/app/scheda_intermediario_esempio.pdf")
