#!/usr/bin/env python3
"""
generar_pdf_confortable.py — Genera PDF de nota de pedido CONFORTABLE SRL
=========================================================================
Para enviar al proveedor por WhatsApp.

USO:
  python3 generar_pdf_confortable.py              <- genera todos los meses en 1 PDF
  python3 generar_pdf_confortable.py ABR          <- solo abril
  python3 generar_pdf_confortable.py ABR MAY JUN  <- meses específicos

Genera: pedido_confortable_2026.pdf (en la carpeta actual)
"""

import sys
import os
from datetime import date
from fpdf import FPDF

# ── Datos del pedido (mismos que insertar_confortable.py) ──────────────

PROVEEDOR = "CONFORTABLE SRL"
CUIT = "30-70017508-8"
EMPRESA = "H4 SRL"
EMPRESA_DIR = "San Martín 456, Venado Tuerto, Santa Fe"

PEDIDOS_MES = {
    "ABR": [
        ("ALPARGATA REF. NEGRO S/EVA", "T41", 12, 5037.99),
        ("710 NEGRO ALP. REF. SUELA PVC", "T42", 6, 6867.84),
        ("710 NEGRO ALP. REF. SUELA PVC", "T43", 6, 5692.57),
        ("ALPARGATA REF. BORDO S/EVA", "T43", 12, 5037.99),
        ("ALPARGATA REF. VERDE S/EVA", "T36", 12, 4537.25),
        ("ALPARGATA REF. BLANCO S/EVA", "T41", 12, 5037.99),
    ],
    "MAY": [
        ("710 NEGRO ALP. REF. SUELA PVC", "T39", 6, 6867.84),
        ("710 NEGRO ALP. REF. SUELA PVC", "T44", 6, 5692.57),
        ("710 AZUL ALP. REF. SUELA PVC", "T38", 6, 6329.77),
        ("ALPARGATA REF. BORDO S/EVA", "T37", 12, 4537.25),
        ("ALPARGATA REF. BORDO S/EVA", "T40", 12, 5037.99),
        ("710 BORDO ALP. REF. SUELA PVC", "T42", 6, 6329.77),
        ("ALPARGATA REF. BORDO S/EVA", "T44", 12, 5037.99),
        ("710 VERDE ALP. REF. SUELA PVC", "T39", 6, 6329.77),
        ("ALPARGATA REF. VERDE S/EVA", "T42", 12, 5037.99),
        ("ALPARGATA REF. VERDE S/EVA", "T43", 12, 5037.99),
        ("710 VERDE ALP. REF. SUELA PVC", "T43", 6, 6329.77),
    ],
    "JUN": [
        ("ALPARGATA REF. NEGRO S/EVA", "T36", 12, 4537.25),
        ("ALPARGATA REF. NEGRO S/EVA", "T37", 12, 4537.25),
        ("710 NEGRO ALP. REF. SUELA PVC", "T37", 6, 5977.19),
        ("ALPARGATA REF. NEGRO S/EVA", "T40", 12, 5037.99),
        ("710 NEGRO ALP. REF. SUELA PVC", "T41", 6, 6867.84),
        ("ALPARGATA REF. NEGRO S/EVA", "T42", 12, 5037.99),
        ("ALPARGATA REF. AZUL S/EVA", "T44", 12, 5037.99),
        ("ALPARGATA REF. VERDE S/EVA", "T37", 12, 4537.25),
        ("710 VERDE ALP. REF. SUELA PVC", "T40", 6, 6329.77),
        ("ALPARGATA REF. BLANCO S/EVA", "T42", 12, 5037.99),
    ],
    "JUL": [
        ("ALPARGATA REF. NEGRO S/EVA", "T34", 12, 4537.25),
        ("710 AZUL ALP. REF. SUELA PVC", "T40", 6, 6450.80),
        ("710 AZUL ALP. REF. SUELA PVC", "T42", 6, 6329.77),
        ("ALPARGATA REF. VERDE S/EVA", "T41", 12, 5037.99),
        ("710 VERDE ALP. REF. SUELA PVC", "T42", 6, 6329.77),
    ],
    "AGO": [
        ("710 NEGRO ALP. REF. SUELA PVC", "T42", 6, 6867.84),
        ("ALPARGATA REF. AZUL S/EVA", "T37", 12, 4537.25),
        ("710 AZUL ALP. REF. SUELA PVC", "T44", 6, 6329.77),
        ("ALPARGATA REF. VERDE S/EVA", "T38", 12, 4537.25),
    ],
    "SEP": [
        ("ALPARGATA REF. NEGRO S/EVA", "T38", 12, 4537.25),
        ("ALPARGATA REF. AZUL S/EVA", "T39", 12, 5037.99),
        ("ALPARGATA REF. BORDO S/EVA", "T37", 12, 4537.25),
    ],
    "OCT": [
        ("710 NEGRO ALP. REF. SUELA PVC", "T39", 6, 6867.84),
        ("710 NEGRO ALP. REF. SUELA PVC", "T40", 6, 6867.84),
        ("ALPARGATA REF. BORDO S/EVA", "T41", 12, 5037.99),
        ("710 BORDO ALP. REF. SUELA PVC", "T41", 6, 6329.77),
        ("710 BORDO ALP. REF. SUELA PVC", "T42", 6, 6329.77),
        ("ALPARGATA REF. BORDO S/EVA", "T43", 12, 5037.99),
        ("710 VERDE ALP. REF. SUELA PVC", "T38", 6, 6329.77),
    ],
}

FECHAS_ENTREGA = {
    "ABR": date(2026, 4, 19),
    "MAY": date(2026, 5, 19),
    "JUN": date(2026, 6, 19),
    "JUL": date(2026, 7, 19),
    "AGO": date(2026, 8, 19),
    "SEP": date(2026, 9, 19),
    "OCT": date(2026, 10, 19),
}

MESES_NOMBRE = {
    "ABR": "Abril", "MAY": "Mayo", "JUN": "Junio", "JUL": "Julio",
    "AGO": "Agosto", "SEP": "Septiembre", "OCT": "Octubre",
}


class PDFPedido(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "NOTA DE PEDIDO", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"{EMPRESA}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pag {self.page_no()}/{{nb}}", align="C")


def generar_pdf(meses_filtro=None):
    if meses_filtro is None:
        meses_filtro = ["ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT"]

    pdf = PDFPedido()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    for mes in meses_filtro:
        if mes not in PEDIDOS_MES:
            print(f"  WARN: mes '{mes}' no encontrado, saltando")
            continue

        items = PEDIDOS_MES[mes]
        fecha_ent = FECHAS_ENTREGA[mes]

        pdf.add_page()

        # Info proveedor
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(30, 7, "Proveedor:", new_x="END")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"  {PROVEEDOR}  (CUIT: {CUIT})", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(30, 7, "Entrega:", new_x="END")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"  {MESES_NOMBRE[mes]} 2026 - {fecha_ent.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(30, 7, "Fecha:", new_x="END")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"  {date.today().strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

        # Tabla header
        col_w = [8, 80, 18, 14, 28, 30]  # #, Descripcion, Talle, Cant, Precio, Subtotal
        headers = ["#", "Descripcion", "Talle", "Cant", "Precio", "Subtotal"]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(60, 60, 60)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            align = "C" if i in (0, 2, 3) else ("R" if i >= 4 else "L")
            pdf.cell(col_w[i], 8, h, border=1, fill=True, align=align)
        pdf.ln()

        # Tabla rows
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        total_pares = 0
        total_monto = 0

        for idx, (desc, talle, cant, precio) in enumerate(items, 1):
            subtotal = cant * precio
            total_pares += cant
            total_monto += subtotal

            bg = idx % 2 == 0
            if bg:
                pdf.set_fill_color(240, 240, 240)

            pdf.cell(col_w[0], 7, str(idx), border=1, align="C", fill=bg)
            pdf.cell(col_w[1], 7, desc, border=1, fill=bg)
            pdf.cell(col_w[2], 7, talle, border=1, align="C", fill=bg)
            pdf.cell(col_w[3], 7, str(cant), border=1, align="C", fill=bg)
            pdf.cell(col_w[4], 7, f"${precio:,.2f}", border=1, align="R", fill=bg)
            pdf.cell(col_w[5], 7, f"${subtotal:,.2f}", border=1, align="R", fill=bg)
            pdf.ln()

        # Totales
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        sum_desc = col_w[0] + col_w[1] + col_w[2]
        pdf.cell(sum_desc, 8, "TOTAL", border=1, align="R", fill=True)
        pdf.cell(col_w[3], 8, str(total_pares), border=1, align="C", fill=True)
        pdf.cell(col_w[4], 8, "", border=1, fill=True)
        pdf.cell(col_w[5], 8, f"${total_monto:,.2f}", border=1, align="R", fill=True)
        pdf.ln()

        # Observaciones
        pdf.ln(6)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, f"Entrega programada: {fecha_ent.strftime('%d/%m/%Y')}  |  {total_pares} pares  |  {len(items)} items",
                 new_x="LMARGIN", new_y="NEXT")

    # Resumen general (ultima pagina)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 12, "RESUMEN GENERAL", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(60, 60, 60)
    pdf.set_text_color(255, 255, 255)
    for h, w in [("Mes", 40), ("Entrega", 35), ("Items", 20), ("Pares", 20), ("Monto", 40)]:
        align = "C" if h in ("Items", "Pares") else ("R" if h == "Monto" else "L")
        pdf.cell(w, 8, h, border=1, fill=True, align=align)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    gran_pares = 0
    gran_monto = 0

    for mes in meses_filtro:
        if mes not in PEDIDOS_MES:
            continue
        items = PEDIDOS_MES[mes]
        pares = sum(r[2] for r in items)
        monto = sum(r[2] * r[3] for r in items)
        gran_pares += pares
        gran_monto += monto

        pdf.cell(40, 7, MESES_NOMBRE[mes], border=1)
        pdf.cell(35, 7, FECHAS_ENTREGA[mes].strftime("%d/%m/%Y"), border=1)
        pdf.cell(20, 7, str(len(items)), border=1, align="C")
        pdf.cell(20, 7, str(pares), border=1, align="C")
        pdf.cell(40, 7, f"${monto:,.2f}", border=1, align="R")
        pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 8, "TOTAL", border=1, fill=True, align="R")
    pdf.cell(35, 8, f"{len(meses_filtro)} meses", border=1, fill=True, align="C")
    nitems = sum(len(PEDIDOS_MES[m]) for m in meses_filtro if m in PEDIDOS_MES)
    pdf.cell(20, 8, str(nitems), border=1, fill=True, align="C")
    pdf.cell(20, 8, str(gran_pares), border=1, fill=True, align="C")
    pdf.cell(40, 8, f"${gran_monto:,.2f}", border=1, fill=True, align="R")
    pdf.ln()

    # Firma
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(80, 6, "_" * 35, align="C")
    pdf.cell(80, 6, "_" * 35, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 6, "Firma Comprador", align="C")
    pdf.cell(80, 6, "Firma Proveedor", align="C")

    # Guardar
    out_dir = os.path.dirname(os.path.abspath(__file__))
    sufijo = "_".join(meses_filtro).lower() if len(meses_filtro) < 7 else "completo"
    filename = f"pedido_confortable_2026_{sufijo}.pdf"
    filepath = os.path.join(out_dir, filename)
    pdf.output(filepath)
    print(f"\n  PDF generado: {filepath}")
    print(f"  {gran_pares} pares | ${gran_monto:,.2f} | {len(meses_filtro)} entregas")
    return filepath


if __name__ == "__main__":
    meses = [m.upper() for m in sys.argv[1:]] if len(sys.argv) > 1 else None
    generar_pdf(meses)
