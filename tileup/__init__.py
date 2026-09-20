"""TileUp: motor del juego para agentes solucionadores."""
from .instancia import Instancia, InstanciaError, leer_instancia
from .motor import TileUp, JugadaIlegal, StepResult, EN_CURSO, VICTORIA, DERROTA

__all__ = [
    "Instancia", "InstanciaError", "leer_instancia",
    "TileUp", "JugadaIlegal", "StepResult", "EN_CURSO", "VICTORIA", "DERROTA",
]
