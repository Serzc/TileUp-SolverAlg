"""Punto de entrada unico.

  python main.py instancias/ejemplo.txt --agente voraz --semilla 1 --limite 10 --salida sol.txt
  python main.py instancias/ejemplo.txt --humano
"""
import argparse
import sys

from agentes import AGENTES
from tileup import InstanciaError
from tileup.juego import jugar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TileUp")
    ap.add_argument("instancia", help="ruta del archivo de instancia")
    ap.add_argument("--agente", choices=sorted(AGENTES), default="voraz")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--limite", type=float, default=10.0, help="limite de tiempo en segundos")
    ap.add_argument("--salida", default=None, help="archivo de solucion (por defecto <instancia>.sol)")
    ap.add_argument("--humano", action="store_true", help="jugar uno mismo por consola")
    a = ap.parse_args(argv)
    salida = a.salida or a.instancia.rsplit(".", 1)[0] + ".sol"
    try:
        jugar(a.instancia, agente=AGENTES[a.agente], humano=a.humano,
              semilla=a.semilla, limite_s=a.limite, salida=salida)
    except InstanciaError as e:
        print(f"error de instancia: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    print(f"solucion escrita en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
