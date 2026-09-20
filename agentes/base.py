"""Agentes de linea base (no son los agentes de la tarea): sirven para probar el motor."""
import random


def aleatorio(juego, semilla, limite_s):
    """Coloca cada ficha en una celda vacia al azar."""
    rng = random.Random(semilla)
    plan = []
    while not juego.terminado:
        f, c = rng.choice(juego.acciones_legales())
        juego.step(juego.siguiente, f, c)
        plan.append((f, c))
    return plan, len(plan)


def voraz(juego, semilla, limite_s):
    """Elige la celda que libera mas celdas; desempata al azar con la semilla."""
    rng = random.Random(semilla)
    plan, evals = [], 0
    while not juego.terminado:
        mejor, opciones = -1, []
        for f, c in juego.acciones_legales():
            liberadas, _ = juego.simular(f, c)
            evals += 1
            if liberadas > mejor:
                mejor, opciones = liberadas, [(f, c)]
            elif liberadas == mejor:
                opciones.append((f, c))
        f, c = rng.choice(opciones)
        juego.step(juego.siguiente, f, c)
        plan.append((f, c))
    return plan, evals
