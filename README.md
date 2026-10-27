# Integración por Monte Carlo con OpenMP

Evaluación de programación paralela en memoria compartida (UIS, 28661). Semilla asignada: **2191050**. N = 10^8. Mediciones del 27 de octubre de 2026 en Linux (Ubuntu 24.04), Intel Core i5-12400F (6 núcleos, 12 hilos lógicos), GCC 13.3.0. El desarrollo contó con asistencia de IA.

## Archivos

- `montecarlo.c`: versión paralela OpenMP (`omp parallel for` + `reduction(+:dentro)`), con `rand_r` y salto de estado por hilo.
- `montecarlo_secuencial.c`: programa secuencial del enunciado con cronómetro y la semilla asignada; mide T(1).
- `experimento.py`: compila, valida la reproducibilidad y ejecuta el protocolo de medición (7 repeticiones, mediana). Regenera `datos/`.
- `grafica.py`: genera `documentos/grafica_speedup.png`.
- `generar_pdf.py`: convierte los Markdown de `documentos/` a PDF.
- `datos/`: `tiempos_crudos.csv`, `resumen.csv`, `resultados.json`, `validacion.txt`, `lscpu.txt`.
- `documentos/`: `informe_completo.md/.pdf` (parte IV + anexos con teoría, cálculos, datos y código) y `respuestas_partes_I_III.md/.pdf`.

## Compilación y uso

```sh
gcc -O2 -fopenmp montecarlo.c -o montecarlo -lm
gcc -O2 -fopenmp montecarlo_secuencial.c -o montecarlo_secuencial -lm

./montecarlo_secuencial 100000000            # T(1), semilla 2191050
./montecarlo 100000000 8                     # 8 hilos
OMP_NUM_THREADS=4 ./montecarlo 100000000     # hilos por variable de entorno
./montecarlo 100000000 12 2191050 dynamic 4096
```

Argumentos de `montecarlo`: `N [hilos] [semilla] [static|dynamic] [bloque]`. Ambos programas compilan sin advertencias con `-Wall -Wextra -Wpedantic -Werror`.

## Flujo aleatorio por hilo

`rand_r` de glibc avanza su estado con el LCG `s <- 1103515245*s + 12345 (mod 2^32)` tres veces por llamada. Las muestras se ven como una única secuencia global: la muestra `i` consume las llamadas `2i` y `2i+1`, es decir, arranca en el paso `6i`. Cada hilo salta algebraicamente (exponenciación binaria de la transformación afín) al paso del primer índice que recibe y desde ahí usa el `rand_r` de la biblioteca. Los tramos son disjuntos y están separados por `2N/p` llamadas; el conjunto de puntos no depende de `p` ni de la planificación, así que la estimación es idéntica para todo `p` y coincide con el programa secuencial (78542140 aciertos, pi = 3.1416856). El programa verifica al arrancar que el salto reproduce el estado real de `rand_r`.

## Resultados

| p | T(p) [s] | S(p) | E(p) |
| --- | --- | --- | --- |
| 1 | 0.633 | 1.000 | 1.000 |
| 2 | 0.318 | 1.990 | 0.995 |
| 4 | 0.160 | 3.949 | 0.987 |
| 8 | 0.093 | 6.769 | 0.846 |
| 12 | 0.066 | 9.586 | 0.799 |

Fracción secuencial estimada con p = 4: s = 0.0043. La caída de eficiencia a partir de p = 8 corresponde al hiperprocesamiento (6 núcleos físicos).

## Repetir

```sh
python3 experimento.py
python3 grafica.py
python3 generar_pdf.py
```

Los tiempos corresponden a este equipo y fecha; otra ejecución producirá valores distintos, pero los aciertos deben ser siempre 78542140 con la semilla 2191050.
