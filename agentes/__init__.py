"""Agentes. Cada agente: agente(juego, semilla, limite_s) -> (plan, esfuerzo).

Por ahora solo hay lineas base para probar el motor; aqui se agregan el agente
de busqueda y el evolutivo.
"""
from .base import aleatorio, voraz

AGENTES = {"aleatorio": aleatorio, "voraz": voraz}
