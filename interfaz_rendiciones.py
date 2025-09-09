#!/usr/bin/env python3
"""Interfaz gráfica para explorar rendiciones y puntajes.

Este módulo carga los mismos datos utilizados por ``consolidar_rendiciones``
pero además almacena la fecha de rendición extraída de la columna
``DataExported``. La interfaz permite visualizar qué estudiantes rindieron cada
examen, quiénes no y revisar el detalle individual de cada alumno.

Dependencias: solo se utiliza la librería estándar ``tkinter``.
"""

from __future__ import annotations

import csv
from itertools import chain
from pathlib import Path
from typing import Dict, Set

import tkinter as tk
from tkinter import ttk

# Directorio de entrada reutilizado desde ``consolidar_rendiciones``
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "csv_ensayos"


def reunir_datos() -> tuple[dict[str, dict[str, object]], Set[str]]:
    """Lee los CSV con puntajes y fechas de rendición."""
    estudiantes: dict[str, dict[str, object]] = {}
    examenes: Set[str] = set()

    archivos = [
        p for p in INPUT_DIR.rglob("*") if p.is_file() and p.suffix.lower() == ".csv"
    ]
    if not archivos:
        print(f"No se encontraron archivos CSV en {INPUT_DIR}")

    for ruta in sorted(archivos):
        with ruta.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            primera = next(reader, None)
            if primera is None:
                examen = ruta.stem.split("-")[1]
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
                fecha = fila.get("DataExported", "").strip()

                info = estudiantes.setdefault(
                    sid, {"FirstName": nombre, "LastName": apellido, "examenes": {}}
                )
                info["FirstName"] = info.get("FirstName") or nombre
                info["LastName"] = info.get("LastName") or apellido
                examenes_est: Dict[str, Dict[str, object]] = info["examenes"]  # type: ignore[assignment]
                examenes_est[examen] = {"score": puntaje, "fecha": fecha}
    return estudiantes, examenes


class Interfaz:
    """Ventana principal de la aplicación."""

    def __init__(self, root: tk.Tk, estudiantes: dict, examenes: Set[str]) -> None:
        self.root = root
        self.estudiantes = estudiantes
        self.examenes = sorted(examenes)

        self.exam_var = tk.StringVar()
        self.filtro_var = tk.StringVar(value="todos")

        combo = ttk.Combobox(root, values=self.examenes, textvariable=self.exam_var, state="readonly")
        combo.pack(fill="x", padx=5, pady=5)
        combo.bind("<<ComboboxSelected>>", self.actualizar_listas)

        frame_rb = ttk.Frame(root)
        frame_rb.pack(fill="x", padx=5, pady=5)
        for valor, texto in [("todos", "Todos"), ("rindieron", "Rindieron"), ("norindieron", "No rindieron")]:
            ttk.Radiobutton(frame_rb, text=texto, variable=self.filtro_var, value=valor, command=self.aplicar_filtro).pack(side="left", padx=5)

        frame_lists = ttk.Frame(root)
        frame_lists.pack(fill="both", expand=True, padx=5, pady=5)
        self.lb_rind = tk.Listbox(frame_lists)
        self.lb_no = tk.Listbox(frame_lists)
        self.lb_rind.pack(side="left", fill="both", expand=True)
        self.lb_no.pack(side="left", fill="both", expand=True)

        self.lb_rind.bind("<<ListboxSelect>>", self.mostrar_detalle)
        self.lb_no.bind("<<ListboxSelect>>", self.mostrar_detalle)

        self.ids_rind: list[str] = []
        self.ids_no: list[str] = []

        if self.examenes:
            self.exam_var.set(self.examenes[0])
            self.actualizar_listas()
        self.aplicar_filtro()

    def actualizar_listas(self, event: object | None = None) -> None:
        examen = self.exam_var.get()
        rindieron: list[tuple[str, float, str]] = []
        no_rindieron: list[tuple[str, str]] = []

        for sid, info in self.estudiantes.items():
            nombre = f"{info['FirstName']} {info['LastName']}".strip()
            exs: Dict[str, Dict[str, object]] = info["examenes"]  # type: ignore[assignment]
            if examen in exs:
                puntaje = float(exs[examen]["score"])
                rindieron.append((nombre, puntaje, sid))
            else:
                no_rindieron.append((nombre, sid))

        rindieron.sort(key=lambda t: t[0])
        no_rindieron.sort(key=lambda t: t[0])

        self.lb_rind.delete(0, tk.END)
        self.ids_rind = []
        for nombre, puntaje, sid in rindieron:
            self.lb_rind.insert(tk.END, f"{nombre} - {puntaje}")
            self.ids_rind.append(sid)

        self.lb_no.delete(0, tk.END)
        self.ids_no = []
        for nombre, sid in no_rindieron:
            self.lb_no.insert(tk.END, nombre)
            self.ids_no.append(sid)

    def aplicar_filtro(self) -> None:
        filtro = self.filtro_var.get()
        for widget in (self.lb_rind, self.lb_no):
            widget.pack_forget()
        if filtro == "todos":
            self.lb_rind.pack(side="left", fill="both", expand=True)
            self.lb_no.pack(side="left", fill="both", expand=True)
        elif filtro == "rindieron":
            self.lb_rind.pack(side="left", fill="both", expand=True)
        else:
            self.lb_no.pack(side="left", fill="both", expand=True)

    def mostrar_detalle(self, event: object) -> None:
        widget = event.widget
        if widget.curselection():
            idx = widget.curselection()[0]
        else:
            return
        sid = self.ids_rind[idx] if widget is self.lb_rind else self.ids_no[idx]
        info = self.estudiantes[sid]
        nombre = f"{info['FirstName']} {info['LastName']}".strip()

        top = tk.Toplevel(self.root)
        top.title(nombre)
        tree = ttk.Treeview(top, columns=("examen", "puntaje", "fecha"), show="headings")
        tree.heading("examen", text="Examen")
        tree.heading("puntaje", text="Puntaje")
        tree.heading("fecha", text="Fecha")
        tree.pack(fill="both", expand=True, padx=5, pady=5)

        exs: Dict[str, Dict[str, object]] = info["examenes"]  # type: ignore[assignment]
        for examen, datos in sorted(exs.items()):
            tree.insert("", tk.END, values=(examen, datos.get("score", ""), datos.get("fecha", "")))


def main() -> None:
    estudiantes, examenes = reunir_datos()
    root = tk.Tk()
    root.title("Rendiciones")
    Interfaz(root, estudiantes, examenes)
    root.mainloop()


if __name__ == "__main__":
    main()
