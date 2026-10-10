# TileUp-SolverAlg

Motor del juego TileUp, dos agentes solucionadores y un verificador independiente.
Tarea Corta 1 de IC-6200. Python 3.8 o superior, solo biblioteca estándar. No hay nada que instalar.

## Uso rápido

```bash
python main.py <instancia> [flags]                 # resolver una instancia
python verificador.py <instancia> <solucion>       # validar una solución
python generador.py <N> <K> <M> [flags]            # crear una instancia
python -m unittest discover -s tests               # correr las pruebas
python experimentos/comparacion.py [flags]         # comparar los agentes
python experimentos/barrido_evolutivo.py [flags]   # ajustar el evolutivo
```

Ejemplo completo, de la instancia a la solución validada:

```bash
python main.py instancias/n5_k15_m100_s1.txt --agente evolutivo --semilla 1 --limite 10 --salida sol.txt
python verificador.py instancias/n5_k15_m100_s1.txt sol.txt
```

### Flags de `main.py`

| Flag | Por defecto | Qué hace |
|---|---|---|
| `--agente NOMBRE` | `voraz` | Agente a usar: `busqueda`, `evolutivo`, `voraz` o `aleatorio`. |
| `--semilla N` | `0` | Semilla del agente. Fija el resultado por completo. |
| `--limite S` | `10` | Límite de tiempo en segundos. |
| `--salida RUTA` | `<instancia>.sol` | Archivo de solución. Se escribe también en derrota. |
| `--humano` | apagado | Jugar uno mismo. `fila col` coloca, `u` deshace, `q` sale. |
| `--visual` | apagado | Mostrar el tablero tras cada jugada del plan. |

### Flags de los demás programas

| Programa | Flag | Qué hace |
|---|---|---|
| `verificador.py` | `--pasos` | Imprime la partida paso a paso. |
| | `--json` | Devuelve el veredicto y las métricas en JSON. |
| `generador.py` | `--semilla N` | Semilla de la secuencia. Por defecto 0. |
| | `--vmax V` | Valor máximo de una ficha. Por defecto 4. |
| | `-o RUTA` | Archivo de salida. Por defecto imprime en consola. |
| | `--lote` | Regenera el conjunto completo, ignorando N, K y M. |
| `barrido_evolutivo.py` | `--limite S`, `--semillas N` | Límite por corrida y semillas por configuración. |
| | `--solo P1 P2` | Barre solo esos parámetros. |
| | `-o RUTA` | CSV de salida. |

Los flags de `comparacion.py` están en [Comparación experimental](#comparación-experimental).

## Formatos

**Instancia.** Texto plano. Se ignoran las líneas vacías y lo que siga a `#`.
Primero `N K`, luego `M`, luego M líneas con `color valor` en el orden de colocación.

```
4 3     # tablero 4x4, 3 colores
6       # 6 fichas
1 2
2 1
1 3
3 1
1 1
2 4
```

**Solución.** Una línea por colocación con `índice fila columna`, todo desde cero.
La última línea empieza con `#` y resume el resultado.

```
0 0 0
1 1 1
2 0 1
3 2 2
4 0 2
5 1 2
# colocadas=6 ocupadas=3 mayor=6
```

Una instancia mal formada produce un mensaje de error legible y código de salida 2.

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

## API del motor

```python
from tileup import TileUp, leer_instancia, JugadaIlegal
j = TileUp(leer_instancia("instancias/n4_k8_m60_s1.txt"))
obs, recompensa, terminado, info = j.step(j.siguiente, fila, col)
```

| Método | Qué hace |
|---|---|
| `step(ficha, fila, col)` | Coloca una ficha. Devuelve estado, celdas liberadas, si terminó y detalles. |
| `deshacer()` | Revierte la última jugada. Sirve para backtracking. |
| `acciones_legales()` | Lista las celdas vacías. |
| `simular(fila, col)` | Prueba una jugada sin aplicarla. Devuelve `(liberadas, valor)`. |
| `jugar_secuencia(celdas)` | Aplica un plan completo de una vez. |
| `clonar()`, `reiniciar()` | Copia independiente, o volver al tablero vacío. |
| `clave()`, `clave_colores()` | Estado hashable, para tablas de visitados. |
| `solucion_texto()`, `guardar_solucion(ruta)`, `render()` | Salida. |

Consulta del estado: `estado`, `terminado`, `colocadas`, `ocupadas`, `mayor`, `ficha_actual()`, `tablero()`.

`step` exige que `ficha` sea `j.siguiente`. Una jugada ilegal lanza `JugadaIlegal` y el estado no cambia.

## Contrato de un agente

```python
def mi_agente(juego: TileUp, semilla: int, limite_s: float) -> tuple[list[tuple[int, int]], int]:
    ...  # devuelve (plan de (fila, col), esfuerzo)
```

El esfuerzo son nodos expandidos o evaluaciones de aptitud, según el algoritmo.
Hay que registrar el agente en `AGENTES`, dentro de `agentes/__init__.py`.
El agente recibe una copia del juego. `tileup.juego.jugar()` ejecuta el plan sobre el motor oficial,
así que un agente no puede alterar las reglas.

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

Está en `agentes/evolutivo.py`. No evoluciona la partida: evoluciona los **pesos de una política**.

La política es voraz de un paso. En cada ficha puntúa las celdas vacías y coloca en la mejor.
Los pesos deciden qué hace buena a una celda, y el evolutivo busca esos pesos.
Se evoluciona durante la corrida, sobre la instancia que se está resolviendo. No hay entrenamiento previo.

### Los pesos

Un individuo es un vector de **9 números reales**. Cada uno multiplica un rasgo de la celda candidata.
El puntaje de una celda es `Σ pesos[i] × rasgos[i]`, y se coloca en la de mayor puntaje.
Los empates se resuelven por índice de celda, no al azar, para que la corrida sea reproducible.

| Peso | Qué mide el rasgo |
|---|---|
| `liberadas` | Celdas que liberaría la fusión, o sea `\|G\| - 1`. |
| `fusion` | Vale 1 si hay fusión. |
| `libres_p` | Vecinos vacíos que le quedarían a la ficha resultante. |
| `distintos` | Vecinos ocupados por otro color. |
| `borde` | Vale 1 si la celda toca un borde. |
| `esquina` | Vale 1 si la celda es una esquina. |
| `dist_centro` | Distancia Manhattan al centro, normalizada. |
| `encierro` | Vecinos ocupados que quedarían sin salida. |
| `prox_libres` | `libres_p` por qué tan pronto reaparece ese color. |

El signo dice si el rasgo atrae o repele. La magnitud dice cuánto pesa frente a los demás.
La escala global no importa: multiplicar los 9 pesos por 10 no cambia ninguna decisión.
Todos los rasgos dependen de la celda, porque un rasgo igual para todas no cambiaría la elección.
El valor de la ficha no es un rasgo: la fusión conserva la suma, así que no depende del agente.

### Cómo se evalúa la aptitud

Evaluar un individuo es **jugar la instancia completa** con sus pesos, de la primera ficha a la última.
Eso es una evaluación de aptitud, y es la unidad de esfuerzo que reporta el agente.

La aptitud es la tupla `(fichas colocadas, −celdas ocupadas)`. Python compara tuplas en orden, así que
primero mandan las fichas colocadas y en empate decide tener menos celdas ocupadas.
Es el orden del concurso en sus dos primeros criterios.

### Operadores y valores fijos

| Componente | Valor | Por qué |
|---|---|---|
| Población | 24 | Lo mejor del barrido, por poco. Con 12 fue claramente peor. |
| Población inicial | 1 imita al voraz, 23 uniformes en [−1, 1] | Da un piso de arranque sin perder diversidad. |
| Selección | Torneo de 3 | Presión media. 2 y 5 dieron lo mismo dentro del ruido. |
| Cruce | Aritmético, `p = 0.9` | `alfa × padre1 + (1 − alfa) × padre2`. El barrido no mostró que aporte. |
| Mutación | Gaussiana, `p = 0.5` por gen | Cambia medio vector por hijo. 0.3 y 1.0 dieron lo mismo. |
| `sigma` | 0.60 → 0.05 | Baja en línea recta con el presupuesto. Explora al inicio, afina al final. |
| Reemplazo | Generacional, elitismo 2 | Los dos mejores pasan intactos. 1 y 4 dieron lo mismo. |
| `ventana` | 8 fichas futuras | Alimenta `prox_libres`. Con 0 baja un poco; de 4 a 16 da igual. |
| Paro | Presupuesto de evaluaciones | Ver abajo. El reloj corta en el 90% del límite. |

El mejor plan encontrado se guarda aparte, así que nunca se pierde aunque la población empeore.

### Cuántas generaciones corre

El paro no es un número fijo de generaciones, sino un presupuesto de evaluaciones:

```
presupuesto = límite_en_segundos × rendimiento / (M × N²)
```

Depende de la instancia y del límite, no de la velocidad real de la máquina. Por eso la corrida es
reproducible. `rendimiento` vale 0.45e6 y está calibrado en la máquina del grupo.

Cada generación cuesta 22 evaluaciones, no 24: los 2 élites no se reevalúan.
Con límite de 10 segundos:

| Instancia | Presupuesto | Generaciones |
|---|---|---|
| N=3, M=30 | 16 666 | unas 756 |
| N=4, M=60 | 4 687 | unas 211 |
| N=5, M=100 | 1 800 | unas 80 |
| N=6, M=150 | 833 | unas 36 |
| N=7, M=200 | 459 | unas 19 |

En las corridas de la comparación el reloj nunca hizo falta: el máximo fue 8.52 s de 10.

### Reproducibilidad y procedimiento

- Todo el azar sale de un solo `random.Random(semilla)`: población inicial, torneos, cruces y mutaciones.
- El desempate entre celdas es por índice y el presupuesto depende de los datos de entrada, no del reloj.
- Los parámetros se fijaron con `experimentos/barrido_evolutivo.py`, que varía uno a la vez desde la base
  sobre 4 instancias de calibración con K alto y 3 semillas.
- Lectura honesta del barrido: todas las variantes quedaron entre 0.573 y 0.603 de fichas colocadas, con un
  error estándar cercano a 0.023, así que ninguna diferencia se distingue del ruido. Lo que se reporta es
  que el algoritmo es robusto a estos parámetros, no que la base sea óptima.


## Comparación experimental

`experimentos/comparacion.py` corre los dos agentes sobre el mismo conjunto de instancias.
Cada corrida guarda su solución y la valida con el verificador independiente.

```bash
python experimentos/comparacion.py --limite 10 --semillas 3
```

Por defecto usa una instancia por configuración de N, K y M, con 3 semillas por agente: 72 corridas.

| Flag | Qué hace |
|---|---|
| `--patron GLOB` | Limita el conjunto de instancias. |
| `--agentes A B` | Elige qué agentes comparar. |
| `--limite S`, `--semillas N` | Límite por corrida y semillas por agente. |
| `--reanudar` | Continúa una corrida interrumpida. El CSV se escribe fila por fila. |
| `--solo-resumen` | Rehace la tabla desde el CSV, sin correr nada. |
| `--csv`, `--md`, `--soluciones` | Rutas de salida. |

Produce `experimentos/comparacion.csv` con una fila por corrida,
`experimentos/comparacion_resumen.md` con la tabla por instancia y agente, y las soluciones en
`experimentos/soluciones/`. Las métricas son las que pide el enunciado: fichas colocadas, celdas ocupadas,
ficha mayor, tiempo y esfuerzo. El esfuerzo no es comparable entre agentes en términos absolutos.

### Resultados

Límite de 10 s, 3 semillas, 12 configuraciones. Tabla completa en
[`experimentos/comparacion_resumen.md`](experimentos/comparacion_resumen.md).

| Agente | Instancias completadas | Corridas legales | Tiempo medio | Esfuerzo medio |
|---|---|---|---|---|
| busqueda | 6/12 | 36/36 | 10.0 s | 627 850 nodos |
| evolutivo | 8/12 | 36/36 | 4.8 s | 5 965 evaluaciones |

El evolutivo gana 9 de las 12 configuraciones y empata 3. La búsqueda gana `n3_k9_m30` por una ficha.
Las 72 soluciones son legales según el verificador.

Dos observaciones:

- La búsqueda consume siempre el límite completo y en 6 corridas lo excedió, con un máximo de 10.92 s.
  El enunciado deja fuera del concurso al agente que se pasa, así que hay que recortar su margen de reloj.
- Con K cercano a N² ningún agente completa la secuencia. Ambos quedan entre el 35% y el 40% de las fichas.

## Verificador

`verificador.py` no importa nada de `tileup/` ni de `agentes/`: reimplementa la lectura y las reglas por
su cuenta, para arbitrar de forma independiente.

Rechaza una solución si encuentra fichas fuera de orden, celdas ocupadas o fuera del tablero, jugadas
después de que la partida terminó, o un resumen que no coincide con la reproducción.
Códigos de salida: 0 legal, 1 ilegal, 2 archivo mal formado.

## Instancias

`instancias/ejemplo.txt` y `ejemplo.sol` son el ejemplo del enunciado.
El resto son 12 configuraciones con 3 semillas cada una, nombradas `nN_kK_mM_sS.txt`.

K se eligió alto respecto a N², porque con pocos colores el juego es trivial: colocar cada ficha junto a
otra de su color deja siempre K celdas ocupadas o menos. Las últimas cuatro configuraciones usan K = N²
y son las duras, donde ningún agente completa la secuencia.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las unitarias prueban el motor por separado: fusión de dos fichas, fusión de tres o más, colocación sin
fusión, detección de derrota y archivos mal formados. Las de integración resuelven una instancia completa
y validan la solución con el verificador.
