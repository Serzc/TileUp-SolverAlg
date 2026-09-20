"""Verificador independiente de soluciones TileUp.

No importa nada del motor (tileup/) ni de los agentes: reimplementa la lectura
de instancias y las reglas por su cuenta para arbitrar de forma independiente.

Uso:
  python verificador.py <instancia> <solucion> [--json] [--pasos]

Codigo de salida: 0 = solucion legal, 1 = solucion ilegal, 2 = archivo mal formado.
"""
import argparse
import json
import sys
from collections import deque


class FormatoError(Exception):
    pass


def _tokens(ruta):
    """Lineas utiles (num, tokens, texto_original) ignorando vacias y comentarios."""
    try:
        with open(ruta, encoding="utf-8") as f:
            crudas = f.read().splitlines()
    except OSError as e:
        raise FormatoError(f"no se pudo leer '{ruta}': {e.strerror}")
    return crudas


def leer_instancia(ruta):
    utiles = []
    for num, linea in enumerate(_tokens(ruta), 1):
        s = linea.split("#", 1)[0].split()
        if s:
            utiles.append((num, s))
    try:
        (l1, t1), (l2, t2) = utiles[0], utiles[1]
    except IndexError:
        raise FormatoError("instancia: faltan las lineas 'N K' y 'M'")

    def ints(num, t, k):
        if len(t) != k:
            raise FormatoError(f"instancia linea {num}: se esperaban {k} enteros")
        try:
            return [int(x) for x in t]
        except ValueError:
            raise FormatoError(f"instancia linea {num}: valor no entero")

    n, k = ints(l1, t1, 2)
    (m,) = ints(l2, t2, 1)
    if n < 1 or k < 1 or m < 0:
        raise FormatoError("instancia: N y K deben ser >= 1 y M >= 0")
    resto = utiles[2:]
    if len(resto) != m:
        raise FormatoError(f"instancia: M={m} pero hay {len(resto)} fichas")
    fichas = []
    for num, t in resto:
        c, v = ints(num, t, 2)
        if not (1 <= c <= k) or v < 1:
            raise FormatoError(f"instancia linea {num}: ficha invalida ({c}, {v})")
        fichas.append((c, v))
    return n, k, fichas


def leer_solucion(ruta):
    jugadas, resumen = [], None
    lineas = _tokens(ruta)
    for num, linea in enumerate(lineas, 1):
        s = linea.strip()
        if not s:
            continue
        if s.startswith("#"):
            resumen = (num, s)
            continue
        if resumen is not None:
            raise FormatoError(f"solucion linea {num}: hay jugadas despues de la linea de resumen")
        t = s.split()
        if len(t) != 3:
            raise FormatoError(f"solucion linea {num}: se esperaban 3 enteros 'ficha fila col'")
        try:
            jugadas.append((num, int(t[0]), int(t[1]), int(t[2])))
        except ValueError:
            raise FormatoError(f"solucion linea {num}: valor no entero")
    datos_resumen = None
    if resumen:
        datos_resumen = {}
        for par in resumen[1].lstrip("#").split():
            if "=" in par:
                clave, val = par.split("=", 1)
                try:
                    datos_resumen[clave.strip()] = int(val)
                except ValueError:
                    pass
    return jugadas, datos_resumen


def verificar(n, k, fichas, jugadas, resumen=None, pasos=False):
    """Reproduce la partida. Devuelve un dict con el veredicto y las metricas."""
    tablero = {}          # (fila, col) -> [color, valor]
    errores, avisos, traza = [], [], []
    m = len(fichas)
    legales = 0

    for idx, (num, fi, fila, col) in enumerate(jugadas):
        if idx >= m:
            errores.append(f"linea {num}: ya se colocaron las {m} fichas; jugada sobrante")
            break
        if len(tablero) == n * n:
            errores.append(f"linea {num}: el tablero esta lleno, la partida ya termino en derrota")
            break
        if fi != idx:
            errores.append(f"linea {num}: se esperaba la ficha {idx}, se indica {fi}")
            break
        if not (0 <= fila < n and 0 <= col < n):
            errores.append(f"linea {num}: celda ({fila},{col}) fuera del tablero {n}x{n}")
            break
        if (fila, col) in tablero:
            errores.append(f"linea {num}: celda ({fila},{col}) ya ocupada")
            break

        color, valor = fichas[idx]
        tablero[(fila, col)] = [color, valor]
        # BFS de la componente del mismo color que contiene la celda colocada
        grupo, cola, visto = [], deque([(fila, col)]), {(fila, col)}
        while cola:
            r, c = cola.popleft()
            grupo.append((r, c))
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (r + dr, c + dc)
                if q not in visto and q in tablero and tablero[q][0] == color:
                    visto.add(q)
                    cola.append(q)
        if len(grupo) >= 2:
            suma = sum(tablero[g][1] for g in grupo)
            for g in grupo:
                del tablero[g]
            tablero[(fila, col)] = [color, suma]
        if pasos:
            traza.append(f"ficha {idx} ({color},{valor}) -> ({fila},{col})  "
                         f"grupo={len(grupo)} valor={tablero[(fila, col)][1]} ocupadas={len(tablero)}")
        legales += 1

    colocadas_legales = legales
    ocupadas = len(tablero)
    mayor = max((v for _, v in tablero.values()), default=0)

    if not errores:
        if colocadas_legales == m:
            estado = "victoria"
        elif ocupadas == n * n:
            estado = "derrota"
        else:
            estado = "incompleta"
            avisos.append(f"la solucion se detiene en la ficha {colocadas_legales} con "
                          f"{n * n - ocupadas} celdas libres")
        if resumen is None:
            avisos.append("falta la linea de resumen '# colocadas=.. ocupadas=.. mayor=..'")
        else:
            reales = {"colocadas": colocadas_legales, "ocupadas": ocupadas, "mayor": mayor}
            for clave, real in reales.items():
                if clave not in resumen:
                    avisos.append(f"el resumen no incluye '{clave}'")
                elif resumen[clave] != real:
                    errores.append(f"resumen incoherente: {clave}={resumen[clave]} pero la "
                                   f"reproduccion da {real}")
    else:
        estado = "ilegal"

    return {
        "legal": not errores, "estado": estado, "M": m,
        "colocadas": colocadas_legales, "ocupadas": ocupadas, "mayor": mayor,
        "errores": errores, "avisos": avisos, "traza": traza,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verificador independiente de TileUp")
    ap.add_argument("instancia")
    ap.add_argument("solucion")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--pasos", action="store_true", help="mostrar la partida paso a paso")
    a = ap.parse_args(argv)
    try:
        n, k, fichas = leer_instancia(a.instancia)
        jugadas, resumen = leer_solucion(a.solucion)
    except FormatoError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    r = verificar(n, k, fichas, jugadas, resumen, pasos=a.pasos)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for t in r["traza"]:
            print(t)
        print(f"{'LEGAL' if r['legal'] else 'ILEGAL'}  estado={r['estado']}  "
              f"colocadas={r['colocadas']}/{r['M']}  ocupadas={r['ocupadas']}  mayor={r['mayor']}")
        for e in r["errores"]:
            print(f"  error: {e}")
        for w in r["avisos"]:
            print(f"  aviso: {w}")
    return 0 if r["legal"] else 1


if __name__ == "__main__":
    sys.exit(main())
