"""Comparacion experimental de los agentes sobre el mismo conjunto de instancias.

Corre cada agente sobre cada instancia con varias semillas, valida cada solucion
con el verificador independiente y reporta las metricas con su dispersion.

  python experimentos/comparacion.py                      # todo, limite 10 s, 3 semillas
  python experimentos/comparacion.py --limite 5 --semillas 3
  python experimentos/comparacion.py --agentes evolutivo --patron "instancias/n5*.txt"
  python experimentos/comparacion.py --reanudar          # continua una corrida interrumpida
  python experimentos/comparacion.py --solo-resumen      # rehace el .md desde el CSV

Escribe tres cosas:
  experimentos/comparacion.csv          una fila por corrida
  experimentos/comparacion_resumen.md   tabla por instancia y agente, con media y desviacion
  experimentos/soluciones/*.sol         la solucion de cada corrida, para re-verificarla
"""
import argparse
import csv
import glob
import os
import statistics
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import verificador  # noqa: E402
from agentes import AGENTES  # noqa: E402
from tileup.instancia import leer_instancia  # noqa: E402
from tileup.juego import jugar  # noqa: E402

CAMPOS = ["instancia", "n", "k", "m", "agente", "semilla", "estado", "colocadas",
          "ocupadas", "mayor", "tiempo_s", "esfuerzo", "legal", "solucion"]


def una_corrida(ruta, nombre_agente, semilla, limite, dir_sol):
    """Ejecuta un agente en una instancia, guarda la solucion y la valida."""
    inst = leer_instancia(ruta)
    base = os.path.splitext(os.path.basename(ruta))[0]
    sol = os.path.join(dir_sol, f"{base}__{nombre_agente}_s{semilla}.sol")
    r = jugar(inst, AGENTES[nombre_agente], semilla=semilla, limite_s=limite,
              salida=sol, verbose=False)
    # Validacion independiente: el verificador vuelve a leer ambos archivos.
    n, k, fichas = verificador.leer_instancia(ruta)
    jugadas, resumen = verificador.leer_solucion(sol)
    v = verificador.verificar(n, k, fichas, jugadas, resumen)
    if not v["legal"]:
        print(f"  !! solucion ILEGAL: {sol} -> {v['errores']}", file=sys.stderr)
    return {
        "instancia": base, "n": inst.n, "k": inst.k, "m": inst.m,
        "agente": nombre_agente, "semilla": semilla, "estado": r["estado"],
        "colocadas": r["colocadas"], "ocupadas": r["ocupadas"], "mayor": r["mayor"],
        "tiempo_s": round(r["tiempo_s"], 3), "esfuerzo": r["esfuerzo"],
        "legal": int(v["legal"]), "solucion": os.path.relpath(sol, RAIZ),
    }


def md(x):
    """Formatea media y desviacion. Con una sola corrida omite la desviacion."""
    if len(x) < 2:
        return f"{x[0]:g}"
    return f"{statistics.fmean(x):.1f} ± {statistics.pstdev(x):.1f}"


def resumen(filas, limite, semillas):
    """Agrupa por instancia y agente, y devuelve el texto Markdown."""
    claves, grupos = [], {}
    for f in filas:
        clave = (f["instancia"], f["agente"])
        if clave not in grupos:
            claves.append(clave)
            grupos[clave] = []
        grupos[clave].append(f)

    out = ["# Comparación experimental", "",
           f"Límite de tiempo: {limite:g} s por corrida. Semillas por configuración: {semillas}.",
           f"Generado por `experimentos/comparacion.py` el {time.strftime('%Y-%m-%d')}.", "",
           "Cada celda es la media entre semillas y su desviación estándar.",
           "`esfuerzo` son nodos expandidos en la búsqueda y evaluaciones de aptitud en el evolutivo.", "",
           "| Instancia | N | K | M | Agente | Colocadas | Ocupadas | Tiempo (s) | Esfuerzo | Legales |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for clave in claves:
        g = grupos[clave]
        p = g[0]
        out.append(
            f"| {p['instancia']} | {p['n']} | {p['k']} | {p['m']} | {p['agente']} | "
            f"{md([x['colocadas'] for x in g])} | {md([x['ocupadas'] for x in g])} | "
            f"{md([x['tiempo_s'] for x in g])} | {md([x['esfuerzo'] for x in g])} | "
            f"{sum(x['legal'] for x in g)}/{len(g)} |")

    out += ["", "## Resumen por agente", "",
            "| Agente | Instancias completadas | Corridas legales | Tiempo medio (s) |",
            "|---|---|---|---|"]
    for agente in sorted({f["agente"] for f in filas}):
        sub = [f for f in filas if f["agente"] == agente]
        completas = {f["instancia"] for f in sub if f["colocadas"] == f["m"]}
        instancias = {f["instancia"] for f in sub}
        out.append(f"| {agente} | {len(completas)}/{len(instancias)} | "
                   f"{sum(f['legal'] for f in sub)}/{len(sub)} | "
                   f"{statistics.fmean([f['tiempo_s'] for f in sub]):.1f} |")
    out += ["", "Una instancia cuenta como completada si el agente colocó las M fichas con",
            "todas las semillas probadas.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Comparacion experimental de agentes TileUp")
    ap.add_argument("--patron", default="instancias/n*_s1.txt",
                    help="patron de las instancias; por defecto una por configuracion de N,K,M")
    ap.add_argument("--agentes", nargs="*", default=["busqueda", "evolutivo"],
                    help="agentes a comparar")
    ap.add_argument("--semillas", type=int, default=3)
    ap.add_argument("--limite", type=float, default=10.0)
    ap.add_argument("--csv", default="experimentos/comparacion.csv")
    ap.add_argument("--md", default="experimentos/comparacion_resumen.md")
    ap.add_argument("--soluciones", default="experimentos/soluciones")
    ap.add_argument("--reanudar", action="store_true",
                    help="conserva el CSV y salta las corridas que ya estan en el")
    ap.add_argument("--solo-resumen", action="store_true",
                    help="no corre nada: rehace el resumen con el CSV que ya existe")
    a = ap.parse_args()

    for nombre in a.agentes:
        if nombre not in AGENTES:
            ap.error(f"agente desconocido: {nombre}. Disponibles: {', '.join(sorted(AGENTES))}")
    rutas = sorted(glob.glob(os.path.join(RAIZ, a.patron)))
    if not rutas:
        ap.error(f"el patron '{a.patron}' no encontro instancias")
    os.makedirs(os.path.join(RAIZ, a.soluciones), exist_ok=True)

    ruta_csv = os.path.join(RAIZ, a.csv)
    ruta_md = os.path.join(RAIZ, a.md)

    # El CSV se escribe fila por fila, asi que una interrupcion no pierde el trabajo.
    filas, hechas = [], set()
    if (a.reanudar or a.solo_resumen) and os.path.exists(ruta_csv):
        with open(ruta_csv, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                for clave in ("n", "k", "m", "semilla", "colocadas", "ocupadas",
                              "mayor", "esfuerzo", "legal"):
                    fila[clave] = int(fila[clave])
                fila["tiempo_s"] = float(fila["tiempo_s"])
                filas.append(fila)
                hechas.add((fila["instancia"], fila["agente"], fila["semilla"]))
        print(f"{len(filas)} corridas ya estaban en {a.csv}")

    if not a.solo_resumen:
        os.makedirs(os.path.join(RAIZ, a.soluciones), exist_ok=True)
        nuevo_csv = not (filas and os.path.exists(ruta_csv))
        salida = open(ruta_csv, "w" if nuevo_csv else "a", newline="", encoding="utf-8")
        escritor = csv.DictWriter(salida, fieldnames=CAMPOS)
        if nuevo_csv:
            escritor.writeheader()
            salida.flush()

        total = len(rutas) * len(a.agentes) * a.semillas
        print(f"{total} corridas: {len(rutas)} instancias x {len(a.agentes)} agentes "
              f"x {a.semillas} semillas")
        hecho, t0 = len(hechas), time.perf_counter()
        for ruta in rutas:
            base = os.path.splitext(os.path.basename(ruta))[0]
            for nombre in a.agentes:
                for sem in range(1, a.semillas + 1):
                    if (base, nombre, sem) in hechas:
                        continue
                    fila = una_corrida(ruta, nombre, sem, a.limite,
                                       os.path.join(RAIZ, a.soluciones))
                    filas.append(fila)
                    escritor.writerow(fila)
                    salida.flush()
                    hecho += 1
                    print(f"[{hecho}/{total}] {fila['instancia']:<16} {nombre:<10} s{sem} "
                          f"-> {fila['colocadas']}/{fila['m']} fichas, "
                          f"{fila['ocupadas']} ocupadas, {fila['tiempo_s']}s, "
                          f"esfuerzo {fila['esfuerzo']}", flush=True)
        salida.close()
        print(f"corridas hechas en esta pasada: {hecho - len(hechas)} "
              f"({time.perf_counter() - t0:.0f}s)")

    if not filas:
        ap.error("no hay corridas para resumir")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(resumen(filas, a.limite, a.semillas))

    ilegales = [x for x in filas if not x["legal"]]
    print(f"soluciones ilegales: {len(ilegales)}")
    print("escritos", a.csv, "y", a.md)
    return 1 if ilegales else 0


if __name__ == "__main__":
    sys.exit(main())
