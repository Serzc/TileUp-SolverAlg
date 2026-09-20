"""Motor de TileUp pensado para agentes solucionadores.

Interfaz principal (estilo "entorno"):
    juego = TileUp(instancia)
    res = juego.step(ficha, fila, col)   # -> StepResult(obs, recompensa, terminado, info)
    juego.deshacer()                     # revierte la ultima colocacion (util para DFS/backtracking)
    juego.acciones_legales()             # celdas vacias [(fila, col), ...]
    juego.clonar()                       # copia independiente (util para busqueda/evolutivo)
    juego.clave()                        # estado hashable (tablero + indice) para tablas de visitados

El tablero se guarda plano: celda i = fila * N + col. Color 0 = vacia.
Las reglas (colocacion, fusion no encadenada, victoria/derrota) viven solo aqui;
los agentes no pueden modificarlas, solo llamar step().
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from .instancia import Instancia

EN_CURSO = "en_curso"
VICTORIA = "victoria"
DERROTA = "derrota"


class JugadaIlegal(Exception):
    """Se intento una jugada que las reglas no permiten. El estado no cambia."""


class StepResult(NamedTuple):
    obs: dict          # snapshot del estado (ver TileUp.observacion)
    recompensa: int    # celdas liberadas por la jugada: |G| - 1 (0 si no hubo fusion)
    terminado: bool    # True si la partida termino (victoria o derrota)
    info: dict         # detalles: fusion, celda, valor resultante, estado, ...


class TileUp:
    def __init__(self, instancia: Instancia):
        self.inst = instancia
        self.n = instancia.n
        self.k = instancia.k
        self.fichas = instancia.fichas
        n2 = self.n * self.n
        # vecinos ortogonales precalculados
        self._vec: List[Tuple[int, ...]] = []
        for i in range(n2):
            f, c = divmod(i, self.n)
            v = []
            if f > 0: v.append(i - self.n)
            if f < self.n - 1: v.append(i + self.n)
            if c > 0: v.append(i - 1)
            if c < self.n - 1: v.append(i + 1)
            self._vec.append(tuple(v))
        self.reiniciar()

    # ------------------------------------------------------------------ estado
    def reiniciar(self) -> dict:
        n2 = self.n * self.n
        self.color = [0] * n2
        self.valor = [0] * n2
        self.siguiente = 0            # indice de la proxima ficha pendiente
        self.ocupadas = 0
        self.jugadas: List[Tuple[int, int, int]] = []   # (ficha, fila, col)
        self._historial: List[tuple] = []               # para deshacer()
        self.estado = self._calcular_estado()
        return self.observacion()

    def _calcular_estado(self) -> str:
        if self.siguiente >= len(self.fichas):
            return VICTORIA
        if self.ocupadas >= self.n * self.n:
            return DERROTA
        return EN_CURSO

    @property
    def terminado(self) -> bool:
        return self.estado != EN_CURSO

    @property
    def colocadas(self) -> int:
        return self.siguiente

    @property
    def pendientes(self) -> int:
        return len(self.fichas) - self.siguiente

    @property
    def mayor(self) -> int:
        return max(self.valor) if self.valor else 0

    def ficha_actual(self) -> Optional[Tuple[int, int]]:
        return self.fichas[self.siguiente] if self.siguiente < len(self.fichas) else None

    def celda(self, fila: int, col: int) -> Optional[Tuple[int, int]]:
        i = fila * self.n + col
        return (self.color[i], self.valor[i]) if self.color[i] else None

    def tablero(self) -> List[List[Optional[Tuple[int, int]]]]:
        """Matriz N x N con None o (color, valor)."""
        return [[self.celda(f, c) for c in range(self.n)] for f in range(self.n)]

    def acciones_legales(self) -> List[Tuple[int, int]]:
        if self.terminado:
            return []
        return [divmod(i, self.n) for i, c in enumerate(self.color) if c == 0]

    def clave(self) -> tuple:
        """Estado hashable. El valor no influye en jugadas futuras, pero se incluye
        para no confundir estados distintos; use clave_colores() si solo importa la forma."""
        return (self.siguiente, tuple(self.color), tuple(self.valor))

    def clave_colores(self) -> tuple:
        """Estado hashable ignorando valores (dos estados con igual clave_colores
        tienen exactamente el mismo futuro en fichas colocadas y celdas ocupadas)."""
        return (self.siguiente, tuple(self.color))

    def metricas(self) -> Dict[str, object]:
        return {"colocadas": self.colocadas, "ocupadas": self.ocupadas,
                "mayor": self.mayor, "estado": self.estado, "M": len(self.fichas)}

    def observacion(self) -> dict:
        return {
            "n": self.n, "k": self.k,
            "color": tuple(self.color), "valor": tuple(self.valor),
            "siguiente": self.siguiente, "ficha_actual": self.ficha_actual(),
            "ocupadas": self.ocupadas, "vacias": self.n * self.n - self.ocupadas,
            "estado": self.estado,
        }

    # ------------------------------------------------------------------ reglas
    def es_legal(self, ficha: int, fila: int, col: int) -> bool:
        try:
            self._validar(ficha, fila, col)
            return True
        except JugadaIlegal:
            return False

    def _validar(self, ficha: int, fila: int, col: int) -> int:
        if self.terminado:
            raise JugadaIlegal(f"la partida ya termino ({self.estado})")
        if ficha != self.siguiente:
            raise JugadaIlegal(f"la ficha a colocar es la {self.siguiente}, no la {ficha}")
        if not (0 <= fila < self.n and 0 <= col < self.n):
            raise JugadaIlegal(f"celda ({fila},{col}) fuera del tablero {self.n}x{self.n}")
        i = fila * self.n + col
        if self.color[i]:
            raise JugadaIlegal(f"celda ({fila},{col}) ocupada")
        return i

    def _componente(self, p: int, c: int) -> List[int]:
        """Componente conexa ortogonal de color c que contiene a p (p ya pintada)."""
        comp, pila, vistos = [], [p], {p}
        color, vec = self.color, self._vec
        while pila:
            i = pila.pop()
            comp.append(i)
            for j in vec[i]:
                if j not in vistos and color[j] == c:
                    vistos.add(j)
                    pila.append(j)
        return comp

    def step(self, ficha: int, fila: int, col: int) -> StepResult:
        """Coloca la ficha `ficha` (debe ser la siguiente pendiente) en (fila, col).

        Lanza JugadaIlegal si la jugada no es valida (el estado no se modifica).
        Devuelve StepResult(obs, recompensa, terminado, info) donde
          recompensa = celdas liberadas (|G| - 1), por lo que la suma de recompensas
                       es colocadas - ocupadas_final;
          info = {"ficha", "fila", "col", "color", "valor", "fusion" (bool),
                  "tam_grupo", "celdas_fusionadas", "valor_resultante",
                  "estado", "colocadas", "ocupadas", "mayor"}.
        """
        p = self._validar(ficha, fila, col)
        c, v = self.fichas[ficha]
        self.color[p], self.valor[p] = c, v
        comp = self._componente(p, c)

        eliminadas = []                      # (celda, valor) retiradas, para deshacer
        if len(comp) >= 2:
            total = 0
            for i in comp:
                total += self.valor[i]
                if i != p:
                    eliminadas.append((i, self.valor[i]))
                    self.color[i] = 0
                    self.valor[i] = 0
            self.valor[p] = total
        self.ocupadas += 1 - len(eliminadas)
        self.siguiente += 1
        self.jugadas.append((ficha, fila, col))
        self._historial.append((p, c, eliminadas))
        self.estado = self._calcular_estado()

        info = {
            "ficha": ficha, "fila": fila, "col": col, "color": c, "valor": v,
            "fusion": bool(eliminadas), "tam_grupo": len(comp),
            "celdas_fusionadas": [divmod(i, self.n) for i, _ in eliminadas],
            "valor_resultante": self.valor[p],
            "estado": self.estado, "colocadas": self.colocadas,
            "ocupadas": self.ocupadas, "mayor": self.mayor,
        }
        return StepResult(self.observacion(), len(eliminadas), self.terminado, info)

    def deshacer(self) -> None:
        """Revierte la ultima colocacion en O(|G|)."""
        if not self._historial:
            raise JugadaIlegal("no hay jugadas que deshacer")
        p, c, eliminadas = self._historial.pop()
        self.jugadas.pop()
        for i, val in eliminadas:
            self.color[i] = c
            self.valor[i] = val
        self.color[p] = 0
        self.valor[p] = 0
        self.ocupadas -= 1 - len(eliminadas)
        self.siguiente -= 1
        self.estado = self._calcular_estado()

    def simular(self, fila: int, col: int) -> Tuple[int, int]:
        """Evalua la siguiente ficha en (fila, col) sin alterar el estado.
        Devuelve (celdas_liberadas, valor_resultante)."""
        res = self.step(self.siguiente, fila, col)
        self.deshacer()
        return res.recompensa, res.info["valor_resultante"]

    def jugar_secuencia(self, celdas) -> StepResult:
        """Aplica una lista de (fila, col) desde el estado actual hasta terminar o
        agotar la lista. Util para evaluar individuos de un evolutivo."""
        res = None
        for fila, col in celdas:
            if self.terminado:
                break
            res = self.step(self.siguiente, fila, col)
        return res

    def clonar(self) -> "TileUp":
        otro = TileUp.__new__(TileUp)
        otro.inst, otro.n, otro.k, otro.fichas = self.inst, self.n, self.k, self.fichas
        otro._vec = self._vec
        otro.color, otro.valor = self.color[:], self.valor[:]
        otro.siguiente, otro.ocupadas, otro.estado = self.siguiente, self.ocupadas, self.estado
        otro.jugadas = self.jugadas[:]
        otro._historial = [(p, c, e[:]) for p, c, e in self._historial]
        return otro

    # ------------------------------------------------------------------ salida
    def solucion_texto(self) -> str:
        lineas = [f"{f} {r} {c}" for f, r, c in self.jugadas]
        lineas.append(f"# colocadas={self.colocadas} ocupadas={self.ocupadas} mayor={self.mayor}")
        return "\n".join(lineas) + "\n"

    def guardar_solucion(self, ruta: str) -> None:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.solucion_texto())

    def render(self, color: bool = True) -> str:
        ancho = max(3, len(str(self.mayor)) + 2)
        pal = ["", "31", "32", "34", "33", "35", "36", "91", "92", "94", "93"]
        cab = "    " + "".join(f"{c:^{ancho + 1}}" for c in range(self.n))
        sep = "   +" + ("-" * ancho + "+") * self.n
        out = [cab, sep]
        for f in range(self.n):
            fila = []
            for c in range(self.n):
                i = f * self.n + c
                if self.color[i]:
                    txt = f"{self.color[i]}:{self.valor[i]}".center(ancho)
                    if color:
                        cod = pal[(self.color[i] - 1) % (len(pal) - 1) + 1]
                        txt = f"\033[{cod}m{txt}\033[0m"
                else:
                    txt = ".".center(ancho)
                fila.append(txt)
            out.append(f"{f:>2} |" + "|".join(fila) + "|")
            out.append(sep)
        return "\n".join(out)

    def __str__(self) -> str:
        return self.render(color=False)
