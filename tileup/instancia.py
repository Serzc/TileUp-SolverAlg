"""Lectura de instancias TileUp (formato de la seccion 3 del enunciado)."""
from dataclasses import dataclass
from typing import List, Tuple

Ficha = Tuple[int, int]  # (color, valor)


class InstanciaError(Exception):
    """Archivo de instancia mal formado."""


@dataclass(frozen=True)
class Instancia:
    n: int                      # lado del tablero (N x N)
    k: int                      # cantidad de colores (1..K)
    fichas: Tuple[Ficha, ...]   # secuencia fija de M fichas
    nombre: str = ""

    @property
    def m(self) -> int:
        return len(self.fichas)


def _lineas_utiles(texto: str) -> List[Tuple[int, List[str]]]:
    """Devuelve (num_linea, tokens) ignorando vacias, lineas con # y comentarios finales."""
    out = []
    for i, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.split("#", 1)[0].strip()
        if linea:
            out.append((i, linea.split()))
    return out


def _enteros(num: int, tokens: List[str], esperado: int, que: str) -> List[int]:
    if len(tokens) != esperado:
        raise InstanciaError(f"linea {num}: se esperaban {esperado} enteros ({que}), hay {len(tokens)}")
    try:
        return [int(t) for t in tokens]
    except ValueError:
        raise InstanciaError(f"linea {num}: valor no entero en {que}: {' '.join(tokens)}") from None


def parsear_instancia(texto: str, nombre: str = "") -> Instancia:
    lineas = _lineas_utiles(texto)
    if len(lineas) < 2:
        raise InstanciaError("faltan las lineas de 'N K' y/o 'M'")
    n, k = _enteros(*lineas[0], 2, "N K")
    (m,) = _enteros(*lineas[1], 1, "M")
    if n <= 0 or k <= 0 or m < 0:
        raise InstanciaError(f"parametros invalidos: N={n} K={k} M={m} (N,K>0, M>=0)")
    cuerpo = lineas[2:]
    if len(cuerpo) != m:
        raise InstanciaError(f"M={m} pero el archivo trae {len(cuerpo)} fichas")
    fichas = []
    for num, tokens in cuerpo:
        c, v = _enteros(num, tokens, 2, "color valor")
        if not 1 <= c <= k:
            raise InstanciaError(f"linea {num}: color {c} fuera de rango 1..{k}")
        if v <= 0:
            raise InstanciaError(f"linea {num}: el valor debe ser positivo, es {v}")
        fichas.append((c, v))
    return Instancia(n, k, tuple(fichas), nombre)


def leer_instancia(ruta: str) -> Instancia:
    try:
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        raise InstanciaError(f"no se pudo leer '{ruta}': {e.strerror}") from None
    return parsear_instancia(texto, nombre=ruta)
