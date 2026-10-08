"""Barrido de parametros del agente evolutivo (procedimiento explicito).

Varia un parametro a la vez desde una configuracion base, sobre un conjunto de
instancias de calibracion y varias semillas, y escribe un CSV con el resultado.

  python experimentos/barrido_evolutivo.py --limite 3 --semillas 3 -o barrido.csv

Las instancias de calibracion NO son las del informe final: se usan K altos para
que el problema no sature. La metrica es la fraccion de fichas colocadas y las
celdas ocupadas, promediadas entre semillas, con su desviacion.
"""
import argparse
import csv
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentes.evolutivo import PARAMETROS, evolutivo  # noqa: E402
from generador import generar  # noqa: E402
from tileup.instancia import parsear_instancia  # noqa: E402
from tileup.juego import jugar  # noqa: E402

CALIBRACION = [(3, 9, 30), (4, 16, 60), (5, 25, 100), (6, 30, 150)]
REJILLA = {
    "poblacion": [12, 24, 48, 96],
    "torneo": [2, 3, 5],
    "p_mut_gen": [0.3, 0.5, 1.0],
    "sigma_ini": [0.3, 0.6, 1.2],
    "sigma_fin": [0.01, 0.05, 0.2],
    "p_cruce": [0.0, 0.6, 0.9],
    "elitismo": [1, 2, 4],
    "ventana": [0, 4, 8, 16],
}


def medir(par, instancias, semillas, limite):
    frac, ocup = [], []
    for inst in instancias:
        for s in range(1, semillas + 1):
            r = jugar(inst, lambda j, sem, lim: evolutivo(j, sem, lim, par=par),
                      semilla=s, limite_s=limite, verbose=False)
            frac.append(r["colocadas"] / r["M"])
            ocup.append(r["ocupadas"] / (inst.n * inst.n))
    return frac, ocup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=float, default=3.0)
    ap.add_argument("--semillas", type=int, default=3)
    ap.add_argument("-o", "--salida", default="experimentos/barrido_evolutivo.csv")
    ap.add_argument("--solo", nargs="*", help="parametros a barrer (por defecto todos)")
    a = ap.parse_args()

    instancias = [parsear_instancia(generar(n, k, m, 100 + i))
                  for i, (n, k, m) in enumerate(CALIBRACION)]
    filas = []
    claves = a.solo or list(REJILLA)
    for clave in claves:
        for valor in REJILLA[clave]:
            t0 = time.perf_counter()
            frac, ocup = medir({clave: valor}, instancias, a.semillas, a.limite)
            filas.append({
                "parametro": clave, "valor": valor,
                "base": PARAMETROS.get(clave),
                "frac_media": round(statistics.fmean(frac), 4),
                "frac_desv": round(statistics.pstdev(frac), 4),
                "ocup_media": round(statistics.fmean(ocup), 4),
                "corridas": len(frac),
                "segundos": round(time.perf_counter() - t0, 1),
            })
            print(filas[-1], flush=True)
    with open(a.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print("escrito", a.salida)


if __name__ == "__main__":
    main()
