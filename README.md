# Ensayos Zenit

Este repositorio contiene scripts de apoyo para el análisis de resultados
de cuestionarios.

## `procesar_respuestas.py`

Este script lee el archivo `quiz-M1 1 Moraleja 2025-full.csv` y genera
los siguientes resúmenes:

* `resumen_estudiantes.csv`: cantidad de respuestas correctas e
  incorrectas por estudiante. Solo se consideran las preguntas con
  puntaje (`PointsN` > 0).
* `dificultad_preguntas.csv`: índice de dificultad de cada pregunta
  calculado como `respuestas_correctas / total_estudiantes`.

Las preguntas con puntaje cero se excluyen del conteo de respuestas
correctas/incorrectas de los estudiantes, pero se evalúan igualmente al
calcular el índice de dificultad.

### Uso

```bash
python procesar_respuestas.py
```

Los archivos de salida se generan en la raíz del repositorio.

## `consolidar_rendiciones.py`

Recorre todos los archivos dentro de `csv_ensayos/` y genera
`resumen_rendiciones.csv`, donde para cada estudiante se indica qué
examen rindió, el puntaje obtenido y si aún no lo ha realizado (`NR`).

### Uso

```bash
python consolidar_rendiciones.py
```

## `proyeccion_correctas.py`

Estima cuántas preguntas correctas podría obtener cada estudiante en los
exámenes que todavía no ha rendido, basándose en su desempeño previo.
El resultado se guarda en `proyeccion_preguntas_correctas.csv`.

### Uso

```bash
python proyeccion_correctas.py
```
