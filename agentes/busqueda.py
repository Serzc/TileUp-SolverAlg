"""Busqueda de planes largos con transposiciones y limite de tiempo."""
import random
import time

from .base import voraz


def busqueda(juego, semilla, limite_s):
    """Busca maximizar fichas colocadas y, en empate, celdas vacias.

    Devuelve el mejor plan encontrado antes del limite, el esfuerzo cuenta nodos
    expandidos. Si M <= N*N, la busqueda parte de un plan completo garantizado.
    """
    inicio = time.perf_counter()
    limite = max(0.0, limite_s)
    rng = random.Random(semilla)
    n2 = juego.n * juego.n
    cantidad = len(juego.fichas)

    if cantidad > n2 and juego.n == 1:
        return [(0, 0)], 0
    if cantidad > n2 and len({color for color, _ in juego.fichas}) == cantidad:
        return [(i // juego.n, i % juego.n) for i in range(n2)], 0

    # Una colocacion por celda siempre permite colocar M fichas cuando M <= N^2.
    if cantidad <= n2:
        respaldo = [(i // juego.n, i % juego.n) for i in range(cantidad)]
    else:
        respaldo, _ = voraz(juego.clonar(), semilla, limite)

    mejor_plan = list(respaldo)
    mejor_vacias = n2
    copia = juego.clonar()
    for fila, col in mejor_plan:
        if copia.terminado:
            break
        copia.step(copia.siguiente, fila, col)
    mejor_plan = mejor_plan[:copia.colocadas]
    mejor_vacias = n2 - copia.ocupadas

    if not juego.fichas:
        return [], 0

    plan = []
    visitados = set()
    nodos = 0
    vencido = False
    fin = inicio + limite

    def explorar():
        nonlocal mejor_plan, mejor_vacias, nodos, vencido

        if time.perf_counter() >= fin:
            vencido = True
            return
        nodos += 1

        colocadas = len(plan)
        vacias = n2 - juego.ocupadas
        if colocadas > len(mejor_plan) or (
            colocadas == len(mejor_plan) and vacias > mejor_vacias
        ):
            mejor_plan = plan[:]
            mejor_vacias = vacias
            if colocadas == len(juego.fichas) and vacias == n2 - 1:
                vencido = True
                return

        if juego.terminado or vencido:
            return

        clave = juego.clave_colores()
        if clave in visitados:
            return
        visitados.add(clave)

        acciones = juego.acciones_legales()
        rng.shuffle(acciones)
        evaluadas = []
        for fila, col in acciones:
            if time.perf_counter() >= fin:
                vencido = True
                return
            recompensa, _ = juego.simular(fila, col)
            evaluadas.append((recompensa, fila, col))
        evaluadas.sort(key=lambda item: item[0], reverse=True)

        for _, fila, col in evaluadas:
            juego.step(juego.siguiente, fila, col)
            plan.append((fila, col))
            explorar()
            plan.pop()
            juego.deshacer()
            if vencido:
                return

    explorar()
    return mejor_plan, nodos