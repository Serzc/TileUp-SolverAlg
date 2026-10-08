# TileUp-SolverAlg

Motor del juego TileUp, dos agentes solucionadores y un verificador independiente.
Tarea Corta 1 de IC-6200. Python 3.8 o superior. Solo biblioteca estándar, no hay nada que instalar.

## Uso rápido

```bash
python main.py instancias/ejemplo.txt --agente voraz --semilla 1 --limite 10 --salida sol.txt
python main.py instancias/n3_k5_m30_s1.txt --agente busqueda --limite 10 --visual
python main.py instancias/ejemplo.txt --agente evolutivo --semilla 1 --limite 10 --salida sol.txt
python main.py instancias/ejemplo.txt --humano          # jugar uno mismo
python verificador.py instancias/ejemplo.txt sol.txt [--pasos] [--json]
python generador.py 5 15 100 --semilla 4 -o instancias/mia.txt
python generador.py --lote                              # regenera instancias/
python -m unittest discover -s tests -v                 # pruebas
python experimentos/barrido_evolutivo.py --limite 10 --semillas 5
python experimentos/comparacion.py --limite 10 --semillas 3   # comparación experimental
```

Agentes disponibles: `busqueda`, `evolutivo`, y `voraz` y `aleatorio` como líneas base.
Si no se indica `--salida`, la solución se escribe en `<instancia>.sol`.

En modo humano: `fila col` coloca la ficha, `u` deshace y `q` sale.
La solución parcial se guarda igual.

## Estructura

| Ruta | Qué contiene |
|---|---|
| `tileup/` | El motor del juego. Las reglas viven solo aquí. |
| `agentes/` | Los agentes. `decisiones.md` documenta cada decisión de diseño. |
| `verificador.py` | Árbitro independiente de soluciones. |
| `generador.py` | Genera instancias a partir de N, K, M y una semilla. |
| `instancias/` | Instancias de prueba y el ejemplo del enunciado. |
| `experimentos/` | Comparación entre agentes y barrido de parámetros del evolutivo. |
| `tests/` | Pruebas unitarias y de integración. |

## API del motor (`tileup/motor.py`)

```python
from tileup import TileUp, leer_instancia, JugadaIlegal
j = TileUp(leer_instancia("instancias/n4_k8_m60_s1.txt"))
obs, recompensa, terminado, info = j.step(j.siguiente, fila, col)
```

| Método | Qué hace |
|---|---|
| `step(ficha, fila, col)` | Coloca una ficha. Ver abajo. |
| `deshacer()` | Revierte la última jugada. Sirve para backtracking. |
| `acciones_legales()` | Lista las celdas vacías. |
| `simular(fila, col)` | Prueba una jugada sin aplicarla. Devuelve `(liberadas, valor)`. |
| `jugar_secuencia(celdas)` | Aplica un plan completo de una vez. |
| `clonar()` | Copia independiente del juego. |
| `reiniciar()` | Vuelve al tablero vacío. |
| `clave()`, `clave_colores()` | Estado hashable, para tablas de visitados. |
| `solucion_texto()`, `guardar_solucion(ruta)` | Escriben la solución. |
| `render()` | Dibuja el tablero. |

Consulta del estado: `estado`, `terminado`, `colocadas`, `ocupadas`, `mayor`, `ficha_actual()`, `tablero()`.

`step` recibe el índice de la ficha, que debe ser `j.siguiente`. Devuelve cuatro cosas:

- `obs`: el estado actual.
- `recompensa`: las celdas que liberó la fusión, o sea `|G| - 1`.
- `terminado`: si la partida acabó, en victoria o en derrota.
- `info`: detalles de la jugada. Trae `fusion`, `tam_grupo`, `celdas_fusionadas`, `valor_resultante`, `estado`, `colocadas`, `ocupadas` y `mayor`.

Una jugada ilegal lanza `JugadaIlegal`. El estado no cambia.

## Contrato de un agente

```python
def mi_agente(juego: TileUp, semilla: int, limite_s: float) -> tuple[list[tuple[int, int]], int]:
    ...  # devuelve (plan de (fila, col), esfuerzo)
```

El esfuerzo son nodos expandidos o evaluaciones de aptitud, según el algoritmo.
Hay que registrar el agente en `AGENTES`, dentro de `agentes/__init__.py`.
El agente recibe una copia del juego, no el original.
`tileup.juego.jugar()` ejecuta el plan sobre el motor oficial, así que un agente no puede alterar las reglas.

`jugar(instancia, agente=None, humano=False, semilla=0, limite_s=10.0, salida=None)` es la función que inicia la partida.

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

## Agente evolutivo

Está en `agentes/evolutivo.py`. Evoluciona los pesos de una política voraz.

- Un individuo es un vector de 9 pesos reales, uno por cada rasgo de una celda.
- Para evaluarlo se juega la instancia completa con esos pesos.
- En cada paso puntúa las celdas vacías y coloca en la de mayor puntaje.
- La aptitud es `(fichas colocadas, −celdas ocupadas)`, el orden del concurso.
- El paro es un presupuesto fijo de evaluaciones. El reloj queda como red de seguridad.
- El esfuerzo reportado son las evaluaciones de aptitud.
- Los empates se resuelven por índice de celda. Todo el azar sale de la semilla.

Cada decisión de diseño, con lo que se descartó, está en [`agentes/decisiones.md`](agentes/decisiones.md).

## Comparación experimental

El script `experimentos/comparacion.py` corre los dos agentes sobre el mismo conjunto de instancias.
Cada corrida guarda su solución y la valida con el verificador independiente.

```bash
python experimentos/comparacion.py --limite 10 --semillas 3
```

Por defecto usa una instancia por cada configuración de N, K y M, con 3 semillas por agente.
Son 12 configuraciones, o sea 72 corridas.

Opciones útiles:

- `--patron "instancias/n5*.txt"` limita el conjunto de instancias.
- `--agentes evolutivo voraz` elige qué agentes comparar.
- `--limite` y `--semillas` fijan el límite de tiempo y la cantidad de semillas.
- `--reanudar` continúa una corrida interrumpida. El CSV se escribe fila por fila.
- `--solo-resumen` rehace la tabla desde el CSV, sin volver a correr nada.

Produce tres salidas:

| Archivo | Contenido |
|---|---|
| `experimentos/comparacion.csv` | Una fila por corrida, con todas las métricas. |
| `experimentos/comparacion_resumen.md` | Tabla por instancia y agente, con media y desviación. |
| `experimentos/soluciones/*.sol` | La solución de cada corrida, para re-verificarla. |

Las métricas por corrida son las que pide el enunciado: fichas colocadas, celdas ocupadas, valor de la
ficha mayor, tiempo y esfuerzo. El esfuerzo son nodos expandidos en la búsqueda y evaluaciones de aptitud
en el evolutivo, así que entre agentes no es comparable en términos absolutos.

### Resultados de la última corrida

Límite de 10 segundos, 3 semillas, 12 configuraciones. La tabla completa está en
[`experimentos/comparacion_resumen.md`](experimentos/comparacion_resumen.md).

| Agente | Instancias completadas | Corridas legales | Tiempo medio | Esfuerzo medio |
|---|---|---|---|---|
| busqueda | 6/12 | 36/36 | 10.0 s | 627 850 nodos |
| evolutivo | 8/12 | 36/36 | 4.8 s | 5 965 evaluaciones |

El evolutivo gana en 9 de las 12 configuraciones y empata en 3.
La búsqueda gana en una, `n3_k9_m30`, por una ficha.
Las 72 soluciones producidas son legales según el verificador.

Dos lecturas que conviene mirar antes del informe:

- La búsqueda consume siempre el límite completo y en 6 corridas lo excedió, con un máximo de 10.92 s.
  El enunciado deja fuera del concurso al agente que se pasa del límite, así que hay que recortar el
  margen de su revisión de reloj.
- Con K cercano a N² ningún agente completa la secuencia. Ahí ambos quedan entre el 35% y el 40% de las
  fichas, y el evolutivo gana por poco. Esas son las instancias `n3_k9`, `n4_k16`, `n5_k25` y `n6_k36`.

## Verificador

`verificador.py` no importa nada de `tileup/` ni de `agentes/`.
Reimplementa la lectura y las reglas por su cuenta, para arbitrar de forma independiente.

Rechaza una solución si encuentra:

- fichas fuera de orden,
- celdas ocupadas o fuera del tablero,
- jugadas después de que la partida terminó,
- un resumen `# colocadas=.. ocupadas=.. mayor=..` que no coincide con la reproducción.

Códigos de salida: 0 si la solución es legal, 1 si es ilegal, 2 si el archivo está mal formado.

## Instancias

`instancias/ejemplo.txt` y `ejemplo.sol` son el ejemplo del enunciado.
El resto son 12 configuraciones con 3 semillas cada una, nombradas `nN_kK_mM_sS.txt`.

K se eligió alto respecto a N². Con pocos colores el juego es trivial.
La razón es que colocar cada ficha junto a otra de su color deja siempre K celdas ocupadas o menos.

Las últimas cuatro configuraciones usan K = N². Son las duras: casi no hay margen para fusionar
y ningún agente completa la secuencia.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las unitarias prueban el motor por separado: fusión de dos fichas, fusión de tres o más,
colocación sin fusión, detección de derrota y archivos mal formados.
Las de integración resuelven una instancia completa y validan la solución con el verificador.
