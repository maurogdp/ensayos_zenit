#!/usr/bin/env python3
"""Genera un resumen de rendiciones y puntajes por estudiante.

Recorre todos los archivos CSV en ``csv_ensayos/`` y produce un archivo
``resumen_rendiciones.csv`` donde cada fila corresponde a un estudiante.
Los nombres de los exámenes aparecen en la primera fila y se rellena con
el puntaje obtenido o ``NR`` en caso de no rendido.
"""

from __future__ import annotations

import csv
from itertools import chain
from pathlib import Path
from typing import Dict, Set

import pandas as pd
from fpdf import FPDF

# Directorios base calculados respecto al archivo del script
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "csv_ensayos"
OUTPUT_FILE = BASE_DIR / "resumen_rendiciones.csv"


def reunir_datos() -> tuple[dict[str, dict[str, object]], Set[str]]:
    """Lee todos los CSV y consolida la información."""
    estudiantes: dict[str, dict[str, object]] = {}
    examenes: Set[str] = set()

    archivos = [
        p for p in INPUT_DIR.rglob("*") if p.is_file() and p.suffix.lower() == ".csv"
    ]
    if not archivos:
        print(f"No se encontraron archivos CSV en {INPUT_DIR}")

    for ruta in sorted(archivos):
        print(f"Procesando {ruta}")
        with ruta.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            primera = next(reader, None)

            if primera is None:
                partes = ruta.stem.split(" - ")
                examen = partes[1].strip() if len(partes) > 1 else ruta.stem
                examenes.add(examen)
                continue

            examen = (
                (primera.get("QuizName") or ruta.stem)
                .replace("\n", " ")
                .replace("\r", " ")
                .strip()
            )
            examenes.add(examen)

            for fila in chain([primera], reader):
                sid = fila.get("StudentID", "").strip()
                nombre = fila.get("FirstName", "").strip()
                apellido = fila.get("LastName", "").strip()
                try:
                    puntaje = float(fila.get("Earned Points", "") or 0)
                except ValueError:
                    puntaje = 0.0

                info = estudiantes.setdefault(
                    sid, {"FirstName": nombre, "LastName": apellido, "scores": {}}
                )
                info["FirstName"] = info.get("FirstName") or nombre
                info["LastName"] = info.get("LastName") or apellido
                scores: Dict[str, float] = info["scores"]  # type: ignore[assignment]
                scores[examen] = puntaje
    return estudiantes, examenes


def generar_resumen(
    estudiantes: dict[str, dict[str, object]], examenes: Set[str]
) -> list[dict[str, object]]:
    """Crea las filas para el CSV de salida.

    Cada fila contiene la información de un estudiante y una columna por
    examen con el puntaje obtenido o ``NR`` si no lo ha rendido.
    """
    filas: list[dict[str, object]] = []
    for sid, info in estudiantes.items():
        nombre = info["FirstName"]
        apellido = info["LastName"]
        scores: Dict[str, float] = info["scores"]  # type: ignore[assignment]
        fila: dict[str, object] = {
            "StudentID": sid,
            "FirstName": nombre,
            "LastName": apellido,
        }
        for examen in sorted(examenes):
            fila[examen] = scores.get(examen, "NR")
        filas.append(fila)
    filas.sort(key=lambda f: (str(f["LastName"]), str(f["FirstName"])))
    return filas


def escribir_csv(filas: list[dict[str, object]], examenes: Set[str]) -> None:
    campos = ["StudentID", "FirstName", "LastName", *sorted(examenes)]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def escribir_excel(filas: list[dict[str, object]], examenes: Set[str]) -> None:
    campos = ["StudentID", "FirstName", "LastName", *sorted(examenes)]
    df = pd.DataFrame(filas, columns=campos)
    df.to_excel(OUTPUT_FILE.with_suffix(".xlsx"), index=False)


def escribir_pdf(filas: list[dict[str, object]], examenes: Set[str]) -> None:
    campos = ["StudentID", "FirstName", "LastName", *sorted(examenes)]
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    page_width = pdf.w - 2 * pdf.l_margin
    col_width = page_width / len(campos)
    row_height = pdf.font_size * 1.5

    for campo in campos:
        pdf.cell(col_width, row_height, campo, border=1)
    pdf.ln(row_height)

    for fila in filas:
        for campo in campos:
            pdf.cell(col_width, row_height, str(fila.get(campo, "")), border=1)
        pdf.ln(row_height)
    pdf.output(str(OUTPUT_FILE.with_suffix(".pdf")))


def main() -> None:
    estudiantes, examenes = reunir_datos()
    resumen = generar_resumen(estudiantes, examenes)
    escribir_csv(resumen, examenes)
    escribir_excel(resumen, examenes)
    escribir_pdf(resumen, examenes)


if __name__ == "__main__":
    main()
