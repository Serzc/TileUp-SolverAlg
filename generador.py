"""Generador de instancias TileUp parametrizado por N, K, M y semilla.

  python generador.py N K M --semilla S [--vmax 4] [-o archivo]
  python generador.py --lote        # regenera el conjunto de instancias/
"""
import argparse
import os
import random

LOTE = [  # (N, K, M). K alto respecto a N*N: con pocos colores el juego es trivial
    (3, 5, 30),       # (una estrategia voraz mantiene <= K celdas ocupadas).
    (3, 6, 30),
    (4, 8, 60),
    (4, 10, 60),
    (5, 12, 100),
    (5, 15, 100),
    (6, 20, 150),
    (7, 30, 200),
]
SEMILLAS = (1, 2, 3)


def generar(n, k, m, semilla, vmax=4):
    rng = random.Random(semilla)
    fichas = [(rng.randint(1, k), rng.randint(1, vmax)) for _ in range(m)]
    lineas = [f"# TileUp -- N={n} K={k} M={m} semilla={semilla} vmax={vmax}",
              f"{n} {k}", f"{m}"]
    lineas += [f"{c} {v}" for c, v in fichas]
    return "\n".join(lineas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="?")
    ap.add_argument("k", type=int, nargs="?")
    ap.add_argument("m", type=int, nargs="?")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--vmax", type=int, default=4)
    ap.add_argument("-o", "--salida")
    ap.add_argument("--lote", action="store_true")
    ap.add_argument("--dir", default="instancias")
    a = ap.parse_args()
    if a.lote:
        os.makedirs(a.dir, exist_ok=True)
        for n, k, m in LOTE:
            for s in SEMILLAS:
                ruta = os.path.join(a.dir, f"n{n}_k{k}_m{m}_s{s}.txt")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(generar(n, k, m, s, a.vmax))
                print(ruta)
        return
    if None in (a.n, a.k, a.m):
        ap.error("indique N K M o use --lote")
    txt = generar(a.n, a.k, a.m, a.semilla, a.vmax)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8") as f:
            f.write(txt)
    else:
        print(txt, end="")


if __name__ == "__main__":
    main()
