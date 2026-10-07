# TileUp-SolverAlg

Motor de TileUp, verificador independiente e instancias para la Tarea Corta 1 (IC-6200).
Solo usa la biblioteca estándar de Python (3.8+).

## Uso rápido

```bash
python main.py instancias/ejemplo.txt --agente voraz --semilla 1 --limite 10 --salida sol.txt
python main.py instancias/n3_k5_m30_s1.txt --agente busqueda --limite 10 --visual
python main.py instancias/ejemplo.txt --humano          # jugar uno mismo
python verificador.py instancias/ejemplo.txt sol.txt [--pasos] [--json]
python generador.py 5 15 100 --semilla 4 -o instancias/mia.txt
python generador.py --lote                               # regenera instancias/
python -m unittest discover -s tests -v                  # pruebas
```

Modo humano: `fila col` coloca la ficha, `u` deshace, `q` sale (la solución parcial se guarda igual).

## API del motor (`tileup/motor.py`)

```python
from tileup import TileUp, leer_instancia, JugadaIlegal
j = TileUp(leer_instancia("instancias/n4_k8_m60_s1.txt"))
obs, recompensa, terminado, info = j.step(j.siguiente, fila, col)
```

| Método | Descripción |
|---|---|
| `step(ficha, fila, col)` | Coloca la ficha (debe ser `j.siguiente`). Devuelve `StepResult(obs, recompensa, terminado, info)`. `recompensa` = celdas liberadas (`|G|-1`). `info` trae `fusion`, `tam_grupo`, `celdas_fusionadas`, `valor_resultante`, `estado`, `colocadas`, `ocupadas`, `mayor`. Jugada ilegal → `JugadaIlegal` y el estado no cambia. |
| `deshacer()` | Revierte la última jugada en O(\|G\|) (backtracking / DFS). |
| `acciones_legales()` | Celdas vacías `[(fila, col), ...]`. |
| `simular(fila, col)` | Prueba la siguiente ficha sin modificar el estado → `(liberadas, valor)`. |
| `jugar_secuencia(celdas)` | Aplica un plan completo (evaluar individuos de un evolutivo). |
| `clonar()`, `reiniciar()` | Copia independiente / volver al tablero vacío. |
| `clave()`, `clave_colores()` | Estado hashable para tablas de visitados. |
| `estado`, `terminado`, `colocadas`, `ocupadas`, `mayor`, `ficha_actual()`, `tablero()` | Consulta. |
| `solucion_texto()`, `guardar_solucion(ruta)`, `render()` | Salida. |

## Contrato de un agente

```python
def mi_agente(juego: TileUp, semilla: int, limite_s: float) -> tuple[list[tuple[int, int]], int]:
    ...  # devuelve (plan de (fila, col), esfuerzo: nodos expandidos / evaluaciones)
```

Regístrelo en `agentes/__init__.py` (`AGENTES`). El agente recibe una **copia** del juego;
`tileup.juego.jugar()` ejecuta el plan sobre el motor oficial, así que no puede alterar las reglas.
`aleatorio` y `voraz` son líneas base.

## Agente de búsqueda

El juego tiene un solo decisor y una secuencia de fichas fija, así que no hay un adversario que justifique
minimax. La tarea es planificar una secuencia de colocaciones que evite llenar el tablero antes de consumir
las fichas. Por eso `busqueda` usa DFS con backtracking: explora planes completos cuando puede, conserva el
mejor prefijo si se agota el tiempo y optimiza en el orden pedido: fichas colocadas primero y celdas vacías
después.

En `agentes/busqueda.py`, el agente prepara primero un plan de respaldo: si `M <= N*N`, coloca una ficha en
cada una de las primeras `M` celdas, lo que garantiza una solución completa; si `M > N*N`, usa el agente
voraz para obtener un prefijo inicial. Luego DFS prueba cada celda legal usando `step()` y `deshacer()`.
Antes de descender, `simular()` estima cuántas celdas libera cada jugada; se prueban primero las que fusionan
grupos mayores. Una semilla fija resuelve empates de forma reproducible. La tabla de transposiciones usa
`clave_colores()`: el índice de la próxima ficha y la disposición de colores determinan las jugadas futuras,
mientras que los valores fusionados no cambian la legalidad de las jugadas. El límite de tiempo se revisa
durante la expansión; `esfuerzo` reporta nodos expandidos.

Hay dos casos imposibles que se resuelven directamente: en un tablero `N=1` solo cabe una ficha, y si todas
las fichas tienen colores distintos no puede ocurrir ninguna fusión. Fuera de esos casos, cuando `M > N*N`,
la posibilidad de completar depende de la secuencia concreta, no solo de `N` y `K`; que la búsqueda termine
con un prefijo no demuestra que no exista una solución.

La opción `--visual` muestra el tablero inicial y el tablero resultante de cada jugada del plan que se ejecuta,
con su ficha, posición, fusiones y celdas vacías. Es la reproducción de la solución elegida, no una impresión
de todas las ramas exploradas por DFS.

`jugar(instancia, agente=None, humano=False, semilla=0, limite_s=10.0, salida=None)` es la función que inicia la partida.

## Verificador

`verificador.py` no importa nada de `tileup/` ni de `agentes/`: reimplementa lectura y reglas.
Rechaza fichas fuera de orden, celdas ocupadas o fuera del tablero, jugadas después de terminar
y un resumen `# colocadas=.. ocupadas=.. mayor=..` incoherente. Salida: 0 legal, 1 ilegal, 2 archivo mal formado.

## Instancias

`instancias/ejemplo.txt` (+ `ejemplo.sol`) es el ejemplo del enunciado. El resto son 8 configuraciones × 3 semillas
(`nN_kK_mM_sS.txt`). K se eligió alto respecto a N²: con pocos colores el juego es trivial, porque
colocar cada ficha junto a otra de su color deja siempre ≤ K celdas ocupadas.
