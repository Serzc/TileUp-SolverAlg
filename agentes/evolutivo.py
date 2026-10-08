"""Agente evolutivo: evoluciona los pesos de una politica voraz parametrizada.

Individuo  : vector de 9 pesos reales, uno por caracteristica de una celda.
Decodificar: jugar la instancia completa eligiendo, en cada paso, la celda vacia
             con mayor producto punto <pesos, rasgos(celda)>.
Aptitud    : (fichas colocadas, -celdas ocupadas), el orden del concurso.
Paro       : presupuesto fijo de evaluaciones (determinista) y el reloj como red
             de seguridad para no exceder el limite de tiempo.

Todo el azar sale de random.Random(semilla) y los empates de puntuacion se
resuelven por indice de celda, asi que la corrida es reproducible.
La justificacion de cada decision esta en agentes/decisiones.md.
"""
import random
import time

# --------------------------------------------------------------- parametros
PARAMETROS = {
    "poblacion": 24,
    "torneo": 3,
    "elitismo": 2,
    "p_cruce": 0.9,
    "p_mut_gen": 0.5,
    "sigma_ini": 0.60,
    "sigma_fin": 0.05,
    "ventana": 8,            # fichas futuras que mira el rasgo "color proximo"
    "margen_tiempo": 0.90,   # fraccion del limite que se permite usar
    "rendimiento": 0.45e6,  # rasgos/segundo de la maquina (calibracion, ver decisiones.md)
    "evals_min": 24,
}

NOMBRES_RASGOS = (
    "liberadas",     # celdas que libera la fusion, |G| - 1
    "fusion",        # 1 si hay fusion
    "libres_p",      # vecinos vacios que le quedan a la ficha resultante
    "distintos",     # vecinos ocupados de otro color
    "borde",         # la celda toca un borde
    "esquina",       # la celda es una esquina
    "dist_centro",   # distancia Manhattan normalizada al centro
    "encierro",      # vecinos ocupados que quedan sin salida
    "prox_libres",   # (el color reaparece pronto) x (libres_p)
)
N_RASGOS = len(NOMBRES_RASGOS)


# ------------------------------------------------------- rasgos de una celda
def _ventanas(fichas, k, w):
    """prox[i][color] = fraccion de las w fichas posteriores a i que son de ese color."""
    prox = []
    for i in range(len(fichas) + 1):
        cuenta = [0.0] * (k + 1)
        trozo = fichas[i + 1: i + 1 + w]
        for c, _ in trozo:
            cuenta[c] += 1.0
        if trozo:
            cuenta = [x / len(trozo) for x in cuenta]
        prox.append(cuenta)
    return prox


def _rasgos(j, i, color, prox_color, centro, escala):
    """Rasgos de colocar una ficha de color `color` en la celda plana i.

    No modifica el tablero: reconstruye la componente que se formaria explorando
    los vecinos del mismo color. Solo incluye rasgos que dependen de la celda,
    porque un rasgo constante dentro del paso no cambiaria el argmax.
    """
    vec = j.vecinos
    col = j.color
    grupo = set()
    for v in vec[i]:
        if col[v] == color and v not in grupo:
            pila = [v]
            grupo.add(v)
            while pila:
                x = pila.pop()
                for y in vec[x]:
                    if y not in grupo and col[y] == color:
                        grupo.add(y)
                        pila.append(y)
    liberadas = len(grupo)

    libres_p = distintos = encierro = 0
    for v in vec[i]:
        if col[v] == 0 or v in grupo:
            libres_p += 1
        else:
            distintos += 1
            salidas = 0
            for z in vec[v]:
                if z != i and (col[z] == 0 or z in grupo):
                    salidas += 1
            if salidas == 0:
                encierro += 1

    f, c = divmod(i, j.n)
    grados = len(vec[i])
    return (
        liberadas * 0.25,
        1.0 if liberadas else 0.0,
        libres_p * 0.25,
        distintos * 0.25,
        1.0 if grados < 4 else 0.0,
        1.0 if grados == 2 else 0.0,
        (abs(f - centro) + abs(c - centro)) * escala,
        encierro * 0.25,
        prox_color * libres_p * 0.25,
    )


# ----------------------------------------------------------- decodificacion
def _jugar(juego, pesos, prox, centro, escala, fin=None):
    """Juega la instancia con esos pesos. Devuelve (aptitud, plan, rasgos_evaluados)."""
    j = juego.clonar()
    j.reiniciar()
    w0, w1, w2, w3, w4, w5, w6, w7, w8 = pesos
    plan = []
    cuenta = 0
    n2 = j.n * j.n
    while not j.terminado:
        color = j.ficha_actual()[0]
        pc = prox[j.siguiente][color]
        mejor, mejor_p = None, None
        for celda in range(n2):
            if j.color[celda]:
                continue
            r = _rasgos(j, celda, color, pc, centro, escala)
            p = (w0 * r[0] + w1 * r[1] + w2 * r[2] + w3 * r[3] + w4 * r[4]
                 + w5 * r[5] + w6 * r[6] + w7 * r[7] + w8 * r[8])
            if mejor_p is None or p > mejor_p:    # > estricto: desempata por indice
                mejor, mejor_p = celda, p
            cuenta += 1
        f, c = divmod(mejor, j.n)
        j.step(j.siguiente, f, c)
        plan.append((f, c))
        if fin is not None and time.perf_counter() > fin:
            break                                 # red de seguridad: plan parcial
    return (j.colocadas, -j.ocupadas), plan, cuenta


# -------------------------------------------------------------- el evolutivo
def _torneo(rng, puntajes, k):
    mejor = rng.randrange(len(puntajes))
    for _ in range(k - 1):
        otro = rng.randrange(len(puntajes))
        if puntajes[otro] > puntajes[mejor]:
            mejor = otro
    return mejor


def _cruce(rng, a, b):
    """Cruce aritmetico: el hijo es una combinacion convexa de los dos padres."""
    alfa = rng.random()
    return [alfa * x + (1.0 - alfa) * y for x, y in zip(a, b)]


def _mutar(rng, w, sigma, p_gen):
    return [x + rng.gauss(0.0, sigma) if rng.random() < p_gen else x for x in w]


def evolutivo(juego, semilla, limite_s, par=None, traza=None):
    p = dict(PARAMETROS, **(par or {}))
    rng = random.Random(semilla)
    fin = time.perf_counter() + limite_s * p["margen_tiempo"]

    n2 = juego.n * juego.n
    centro = (juego.n - 1) / 2.0
    escala = 1.0 / max(1, juego.n - 1)
    prox = _ventanas(juego.fichas, juego.k, p["ventana"])

    # Presupuesto determinista: depende de (N, M, limite), no de la velocidad real.
    costo = max(1, len(juego.fichas) * n2)
    presupuesto = max(p["evals_min"], int(limite_s * p["rendimiento"] / costo))

    # Poblacion inicial: un individuo imita al voraz, el resto es aleatorio.
    pob = [[0.0] * N_RASGOS]
    pob[0][0] = 1.0
    while len(pob) < p["poblacion"]:
        pob.append([rng.uniform(-1.0, 1.0) for _ in range(N_RASGOS)])

    evals = 0
    puntajes, planes = [], []
    for w in pob:
        apt, plan, _ = _jugar(juego, w, prox, centro, escala, fin)
        puntajes.append(apt)
        planes.append(plan)
        evals += 1

    i = max(range(len(pob)), key=lambda x: puntajes[x])
    mejor = (puntajes[i], pob[i][:], planes[i])
    gen = 0

    while evals < presupuesto and time.perf_counter() < fin:
        gen += 1
        avance = min(1.0, evals / presupuesto)
        sigma = p["sigma_ini"] + (p["sigma_fin"] - p["sigma_ini"]) * avance

        orden = sorted(range(len(pob)), key=lambda x: puntajes[x], reverse=True)
        nueva = [pob[x][:] for x in orden[:p["elitismo"]]]
        n_apt = [puntajes[x] for x in orden[:p["elitismo"]]]
        n_plan = [planes[x] for x in orden[:p["elitismo"]]]

        while len(nueva) < p["poblacion"]:
            a = pob[_torneo(rng, puntajes, p["torneo"])]
            if rng.random() < p["p_cruce"]:
                b = pob[_torneo(rng, puntajes, p["torneo"])]
                hijo = _cruce(rng, a, b)
            else:
                hijo = a[:]
            hijo = _mutar(rng, hijo, sigma, p["p_mut_gen"])
            apt, plan, _ = _jugar(juego, hijo, prox, centro, escala, fin)
            evals += 1
            nueva.append(hijo)
            n_apt.append(apt)
            n_plan.append(plan)
            if apt > mejor[0]:
                mejor = (apt, hijo[:], plan)
            if evals >= presupuesto or time.perf_counter() >= fin:
                break

        pob, puntajes, planes = nueva, n_apt, n_plan
        if traza is not None:
            traza.append({"gen": gen, "evals": evals, "mejor": mejor[0]})

    if traza is not None:
        traza.append({"gen": "fin", "evals": evals, "mejor": mejor[0],
                      "pesos": dict(zip(NOMBRES_RASGOS, [round(x, 3) for x in mejor[1]]))})
    return mejor[2], evals
