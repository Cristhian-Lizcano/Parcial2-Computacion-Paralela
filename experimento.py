"""Validacion y mediciones del examen (partes II y III). Solo biblioteca estandar.

Uso:  python3 experimento.py [--reps 7] [--threads 1 2 4 8 12]

Compila ambos programas, verifica la reproducibilidad (mismos aciertos para
todo p, toda planificacion y tamanos no divisibles), mide T(1) con el
programa secuencial de referencia y T(p) con la version OpenMP, y escribe en
datos/: tiempos_crudos.csv, resumen.csv, resultados.json, validacion.txt y
lscpu.txt.
"""
import argparse
import csv
import datetime
import json
import math
import os
import platform
import random
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATOS = ROOT / 'datos'
SEMILLA = 2191050
CFLAGS = ['-O2', '-Wall', '-Wextra', '-Wpedantic', '-Werror', '-fopenmp']


def compilar():
    for fuente, binario in [('montecarlo.c', 'montecarlo'),
                            ('montecarlo_secuencial.c', 'montecarlo_secuencial')]:
        subprocess.run(['gcc', *CFLAGS, fuente, '-o', binario, '-lm'],
                       cwd=ROOT, check=True)


def ejecutar(N, p=None, sched='static', chunk=0, modo='parallel'):
    """Devuelve dict con pi, aciertos, hilos y segundos."""
    env = os.environ.copy()
    env['OMP_DYNAMIC'] = 'FALSE'
    env.pop('OMP_PROC_BIND', None)
    env.pop('OMP_PLACES', None)
    if modo == 'reference':
        cmd = [str(ROOT / 'montecarlo_secuencial'), str(N), str(SEMILLA)]
    else:
        cmd = [str(ROOT / 'montecarlo'), str(N), str(p), str(SEMILLA), sched, str(chunk)]
    out = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True).stdout
    pi = float(re.search(r'Estimacion de pi: ([\d.]+)', out).group(1))
    hits, n = map(int, re.search(r'Aciertos: (\d+) de (\d+)', out).groups())
    hilos = int(re.search(r'Hilos: (\d+)', out).group(1))
    seg = float(re.search(r'Tiempo: ([\d.]+)', out).group(1))
    assert n == N
    if modo != 'reference':
        assert hilos == p, ('Equipo distinto al solicitado', hilos, p)
    return dict(N=N, p=1 if modo == 'reference' else p, schedule=sched, chunk=chunk,
                mode=modo, hits=hits, pi=pi, seconds=seg)


def validar(threads):
    lineas = []
    for N in [1, 2, 7, 101, 10003, 1000000]:
        ref = ejecutar(N, modo='reference')['hits']
        for p in threads:
            for sched, chunk in [('static', 0), ('static', 17), ('dynamic', 17)]:
                r = ejecutar(N, p, sched, chunk)
                assert r['hits'] == ref, (N, p, sched, chunk, r['hits'], ref)
        lineas.append(f'N={N}: {ref} aciertos en el secuencial; identicos con p in '
                      f'{threads} y planificaciones static,0 / static,17 / dynamic,17')
    (DATOS / 'validacion.txt').write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    return lineas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=100000000)
    ap.add_argument('--reps', type=int, default=7)
    ap.add_argument('--threads', type=int, nargs='+', default=[1, 2, 4, 8, 12])
    args = ap.parse_args()
    DATOS.mkdir(exist_ok=True)

    compilar()
    lscpu = subprocess.run(['lscpu'], capture_output=True, text=True, check=True).stdout
    (DATOS / 'lscpu.txt').write_text(lscpu, encoding='utf-8')
    validacion = validar(args.threads)
    print('\n'.join(validacion), flush=True)

    # Calentamiento (no se registra).
    ejecutar(args.N, modo='reference')
    for p in args.threads:
        ejecutar(args.N, p)

    configs = [(1, 'static', 0, 'reference')]
    configs += [(p, 'static', 0, 'parallel') for p in args.threads]
    pmax = max(args.threads)
    configs += [(pmax, 'static', 4096, 'parallel'), (pmax, 'dynamic', 4096, 'parallel'),
                (pmax, 'dynamic', 1, 'parallel')]
    filas = []
    for rep in range(1, args.reps + 1):
        orden = configs.copy()
        random.Random(SEMILLA + rep).shuffle(orden)
        for p, sched, chunk, modo in orden:
            r = ejecutar(args.N, p, sched, chunk, modo)
            r['repetition'] = rep
            filas.append(r)
            print(f"rep={rep} {modo} p={p} {sched},{chunk}: {r['seconds']:.4f} s", flush=True)

    aciertos = {r['hits'] for r in filas}
    assert len(aciertos) == 1, aciertos
    hits = aciertos.pop()
    pi_est = 4.0 * hits / args.N

    def tiempos(modo, p=1, sched='static', chunk=0):
        return [r['seconds'] for r in filas
                if (r['mode'], r['p'], r['schedule'], r['chunk']) == (modo, p, sched, chunk)]

    T1 = statistics.median(tiempos('reference'))
    resumen = []
    for p in args.threads:
        t = tiempos('parallel', p)
        Tp = statistics.median(t)
        resumen.append(dict(p=p, T=Tp, S=T1 / Tp, E=T1 / Tp / p,
                            minimum=min(t), maximum=max(t)))
    # Fraccion secuencial s despejada de Amdahl con p=4 (III.2).
    S4 = next(r['S'] for r in resumen if r['p'] == 4)
    s = (1 / S4 - 1 / 4) / (1 - 1 / 4)
    for r in resumen:
        r['Amdahl'] = 1 / (s + (1 - s) / r['p'])
        r['KarpFlatt'] = None if r['p'] == 1 else (1 / r['S'] - 1 / r['p']) / (1 - 1 / r['p'])

    se = 4 * math.sqrt((math.pi / 4) * (1 - math.pi / 4) / args.N)
    modelo = re.search(r'Model name:\s*(.+)|Nombre del modelo:\s*(.+)', lscpu)
    meta = dict(
        timestamp_local=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        platform=platform.platform(),
        cpu=(modelo.group(1) or modelo.group(2)).strip() if modelo else None,
        logical_cpus=os.cpu_count(),
        compiler=subprocess.run(['gcc', '--version'], capture_output=True, text=True).stdout.splitlines()[0],
        flags=' '.join(CFLAGS),
        affinity='no fijada (OMP_PROC_BIND/OMP_PLACES sin definir)', dynamic_teams=False,
        seed=SEMILLA, N=args.N, repetitions=args.reps, threads=args.threads,
        timing='omp_get_wtime alrededor del ciclo; en la version paralela incluye la creacion del equipo y la reduccion',
        hits=hits, pi=pi_est, abs_error=abs(pi_est - math.pi), standard_error=se,
        z=(pi_est - math.pi) / se,
        T1_reference=T1, T1_openmp_1_thread=statistics.median(tiempos('parallel', 1)),
        serial_fraction_s=s, parallel_fraction_f=1 - s,
        S64=1 / (s + (1 - s) / 64), S_infinity=1 / s if s > 0 else None,
        schedule_comparison=[dict(p=pmax, schedule=sc, chunk=ch,
                                  median=statistics.median(tiempos('parallel', pmax, sc, ch)),
                                  minimum=min(tiempos('parallel', pmax, sc, ch)),
                                  maximum=max(tiempos('parallel', pmax, sc, ch)))
                             for sc, ch in [('static', 0), ('static', 4096), ('dynamic', 4096), ('dynamic', 1)]],
        summary=resumen)

    with (DATOS / 'tiempos_crudos.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    with (DATOS / 'resumen.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(resumen[0]))
        w.writeheader(); w.writerows(resumen)
    (DATOS / 'resultados.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n',
                                           encoding='utf-8')
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
