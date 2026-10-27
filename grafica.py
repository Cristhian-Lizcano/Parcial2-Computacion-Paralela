"""Grafica S(p) medido, ideal y Amdahl a partir de datos/resultados.json."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

m = json.load(open('datos/resultados.json'))
T1 = m['T1_reference']
ps = [r['p'] for r in m['summary']]
S = [T1 / r['T'] if r['p'] > 1 else 1.0 for r in m['summary']]
A = [r['Amdahl'] for r in m['summary']]
s = m['serial_fraction_s']

fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150)
ax.plot(ps, ps, '--', color='#888', label='Ideal lineal S(p) = p')
ax.plot(ps, A, ':s', color='#d95f02', label=f'Amdahl, s = {s*100:.2f} % (ajustada con p = 4)')
ax.plot(ps, S, '-o', color='#1b9e77', label='Medido, T(1)/T(p)')
for p, v in zip(ps, S):
    ax.annotate(f'{v:.2f}', (p, v), textcoords='offset points', xytext=(6, -10), fontsize=8)
ax.set_xlabel('p (hilos)'); ax.set_ylabel('Speedup S(p)'); ax.set_xticks(ps)
ax.set_title(f"Monte Carlo OpenMP, N = 10^8, {m['cpu']}", fontsize=9)
ax.grid(alpha=0.3); ax.legend(fontsize=8); fig.tight_layout()
fig.savefig('documentos/grafica_speedup.png')
print('documentos/grafica_speedup.png')
