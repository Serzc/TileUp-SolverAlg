"""Punto de arranque de una partida: con un agente o jugada por una persona."""
import os
import random
import sys
import time
from typing import Callable, List, Optional, Tuple

from .instancia import Instancia, leer_instancia
from .motor import JugadaIlegal, TileUp

Plan = List[Tuple[int, int]]
# Un agente es cualquier callable: agente(juego, semilla, limite_s) -> (plan, esfuerzo)
#   juego     : TileUp recien reiniciado (el agente puede clonarlo / usar step+deshacer)
#   plan      : lista de (fila, col) en el orden de la secuencia
#   esfuerzo  : int (nodos expandidos, evaluaciones de aptitud, ...)
Agente = Callable[[TileUp, int, float], Tuple[Plan, int]]


def _habilitar_ansi() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # activa secuencias ANSI en la consola de Windows
    return True


def _jugar_humano(juego: TileUp, ver_proximas: int = 5) -> None:
    color = _habilitar_ansi()
    print("TileUp - modo humano. Escriba 'fila col' para colocar, 'u' deshacer, 'q' salir.")
    while not juego.terminado:
        print()
        print(juego.render(color=color))
        c, v = juego.ficha_actual()
        prox = juego.fichas[juego.siguiente + 1: juego.siguiente + 1 + ver_proximas]
        print(f"Ficha {juego.siguiente}/{len(juego.fichas) - 1}: color={c} valor={v}"
              f"   proximas: {' '.join(f'{a}:{b}' for a, b in prox) or '-'}")
        print(f"Ocupadas {juego.ocupadas}/{juego.n * juego.n}")
        try:
            txt = input("> ").strip().lower()
        except EOFError:
            txt = "q"
        if txt in ("q", "quit", "salir"):
            break
        if txt in ("u", "undo", "deshacer"):
            try:
                juego.deshacer()
            except JugadaIlegal as e:
                print(f"! {e}")
            continue
        partes = txt.replace(",", " ").split()
        if len(partes) != 2 or not all(p.lstrip("-").isdigit() for p in partes):
            print("! formato: fila col   (ej. 0 2)")
            continue
        try:
            res = juego.step(juego.siguiente, int(partes[0]), int(partes[1]))
        except JugadaIlegal as e:
            print(f"! jugada ilegal: {e}")
            continue
        if res.info["fusion"]:
            print(f"* fusion de {res.info['tam_grupo']} fichas -> valor {res.info['valor_resultante']}")
    print()
    print(juego.render(color=color))


def jugar(instancia, agente: Optional[Agente] = None, humano: bool = False,
          semilla: int = 0, limite_s: float = 10.0,
          salida: Optional[str] = None, verbose: bool = True,
          visual: bool = False) -> dict:
    """Inicia una partida de TileUp.

    instancia : ruta al archivo o un objeto Instancia.
    agente    : callable agente(juego, semilla, limite_s) -> (plan, esfuerzo). Se ignora si humano=True.
    humano    : False (por defecto) = juega el agente; True = juega usted por consola.
    salida    : ruta del archivo de solucion a escribir (se escribe aun en derrota).
    visual    : imprime el tablero inicial y cada estado del plan ejecutado.
    Devuelve un dict con las metricas finales y el plan ejecutado.
    """
    inst = instancia if isinstance(instancia, Instancia) else leer_instancia(instancia)
    juego = TileUp(inst)
    random.seed(semilla)
    t0 = time.perf_counter()
    esfuerzo = 0

    if humano:
        _jugar_humano(juego)
    else:
        if agente is None:
            raise ValueError("se requiere un agente cuando humano=False")
        plan, esfuerzo = agente(juego.clonar(), semilla, limite_s)
        color = _habilitar_ansi() if visual else False
        if visual:
            print(f"Estado inicial 0/{len(inst.fichas)} | vacias={juego.n * juego.n}")
            print(juego.render(color=color))
        # El motor ejecuta el plan: el agente nunca toca el estado oficial.
        for fila, col in plan:
            if juego.terminado:
                break
            try:
                res_step = juego.step(juego.siguiente, fila, col)
            except JugadaIlegal as e:
                if verbose:
                    print(f"[aviso] el agente propuso una jugada ilegal en la ficha "
                          f"{juego.siguiente}: {e}. Se detiene la partida.", file=sys.stderr)
                break
            if visual:
                fusion = "si" if res_step.info["fusion"] else "no"
                print(f"\nEstado {juego.colocadas}/{len(inst.fichas)} | "
                      f"ficha {res_step.info['ficha']} "
                      f"({res_step.info['color']}:{res_step.info['valor']}) en "
                      f"({fila}, {col}) | vacias={juego.n * juego.n - juego.ocupadas} | "
                      f"fusion={fusion}")
                print(juego.render(color=color))

    dt = time.perf_counter() - t0
    if salida:
        juego.guardar_solucion(salida)
    res = dict(juego.metricas(), tiempo_s=round(dt, 4), esfuerzo=esfuerzo, jugadas=list(juego.jugadas))
    if verbose:
        print(f"estado={res['estado']} colocadas={res['colocadas']}/{res['M']} "
              f"ocupadas={res['ocupadas']} mayor={res['mayor']} "
              f"tiempo={res['tiempo_s']}s esfuerzo={res['esfuerzo']}")
    return res
