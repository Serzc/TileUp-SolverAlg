# Decisiones de diseño de los agentes

Un apartado por agente. Dentro, una sección por característica. Cada sección trae
la **decisión** final y **qué más se consideró**. Esto alimenta directo el informe.

---

## Agente evolutivo (`agentes/evolutivo.py`)

### Enfoque general

**Decisión.** El evolutivo no evoluciona la partida, evoluciona los **pesos de una política**.
Un individuo es un vector de pesos. Para evaluarlo se juega la instancia completa con esos pesos.
Se evoluciona en el momento, dentro del límite de tiempo, y se entrega el plan del mejor individuo.

**Qué más se consideró.** Representar el individuo como la lista de las M jugadas.
Se descartó como entregable principal: el espacio tiene M dimensiones y la localidad es mala.
Queda como variante para el informe. Entrenar pesos antes y jugar con pesos fijos también se
descartó: reportaría cero evaluaciones de aptitud, no usaría el límite de tiempo y se sobreajusta
a nuestras instancias.

### Representación del individuo

**Decisión.** Vector de 9 números reales, uno por rasgo de celda. Sin restricciones de rango.

**Qué más se consideró.** Pesos binarios o enteros: menos expresivos. Normalizar el vector a norma 1:
innecesario, porque la escala global no cambia el argmax. Codificación binaria estilo GA clásico:
se descartó por el ruido de la conversión.

### Rasgos de la celda

**Decisión.** Nueve rasgos, todos dependientes de la celda candidata: `liberadas`, `fusion`,
`libres_p`, `distintos`, `borde`, `esquina`, `dist_centro`, `encierro`, `prox_libres`.
Se calculan sin modificar el tablero, reconstruyendo la componente del mismo color desde los vecinos.
Están escalados a un rango parecido (los conteos de vecinos se dividen entre 4).

**Qué más se consideró.** Rasgos constantes dentro de un paso, como `ocupadas / N²` o la frecuencia
del color actual. Se descartaron: suman lo mismo a todas las celdas y no cambian el argmax.
El valor de la ficha tampoco entró: la fusión conserva la suma, así que el valor no afecta el resultado.
Usar `juego.simular()` para medir la fusión era más corto, pero hace `step` y `deshacer` por celda;
el cálculo directo evita esa ida y vuelta.

### Decodificador

**Decisión.** Política voraz de un paso. En cada ficha se puntúa cada celda vacía con el producto punto
y se toma la mejor. Los empates se resuelven por índice de celda, con una comparación `>` estricta.

**Qué más se consideró.** Mirar dos fichas por delante: multiplica el costo por el número de celdas vacías
y recorta mucho las generaciones posibles. Desempate aleatorio: rompería la reproducibilidad con la semilla.

### Función de aptitud

**Decisión.** La tupla `(fichas colocadas, −celdas ocupadas)`. Python la ordena lexicográficamente,
que es exactamente el orden del concurso.

**Qué más se consideró.** Un escalar del tipo `colocadas × (N²+1) + (N² − ocupadas)`: equivalente, pero
solo hace falta si se usa selección proporcional. Premiar el valor de la ficha mayor: se descartó,
no es criterio del concurso y no depende de las decisiones del agente.

### Población inicial

**Decisión.** Tamaño 24. El primer individuo es `liberadas = 1` y el resto en cero, o sea una imitación
del agente voraz. Los otros 23 son uniformes en [−1, 1].

**Qué más se consideró.** Población enteramente aleatoria: parte más abajo sin ganar diversidad útil.
Sembrar varios individuos cerca del voraz: concentra la población antes de explorar.
Medición: esa semilla voraz, por sí sola, coloca 29 de 100 fichas en `n5_k15_m100_s1`, mientras que
el evolutivo completo coloca las 100. La mejora viene de la evolución, no de la siembra.

### Selección

**Decisión.** Torneo de tamaño 3.

**Qué más se consideró.** Torneo de 2 y de 5: diferencia dentro del ruido en el barrido.
Selección proporcional a la aptitud: incómoda con aptitud en tuplas y sensible a la escala.
Se eligió torneo por ser invariante a la escala de la aptitud.

### Cruce

**Decisión.** Cruce aritmético con probabilidad 0.9: el hijo es una combinación convexa de los padres,
con un `alfa` sorteado por hijo.

**Qué más se consideró.** Cruce de un punto o uniforme: válidos, pero el aritmético aprovecha que el
genotipo es real y continuo. Dato honesto del barrido: desactivar el cruce (`p_cruce = 0`) dio 0.603
frente a 0.597 con 0.9. La diferencia está dentro del ruido, así que el cruce **no demostró aportar**.
Se mantiene porque la rúbrica pide operadores de variación, y se reporta tal cual.

### Mutación

**Decisión.** Gaussiana por gen, cada gen se muta con probabilidad 0.5, con `sigma` que decrece
linealmente de 0.60 a 0.05 según el avance del presupuesto.

**Qué más se consideró.** `sigma` fija: explora igual al inicio que al final. Mutar todos los genes
siempre (`p = 1.0`) o solo el 30%: ambos dentro del ruido en el barrido. El esquema decreciente se
mantuvo porque es estándar en codificación real y es fácil de justificar.

### Reemplazo

**Decisión.** Generacional con elitismo de 2: los dos mejores pasan intactos y el resto de la nueva
generación se produce por torneo, cruce y mutación.

**Qué más se consideró.** Elitismo de 1 y de 4: dentro del ruido. Reemplazo estacionario
(steady-state): más código y más parámetros para el mismo efecto en este problema.
El mejor plan encontrado se guarda aparte, así que nunca se pierde aunque la población empeore.

### Criterio de paro

**Decisión.** Doble criterio. El principal es un **presupuesto fijo de evaluaciones**, calculado como
`limite_s × rendimiento / (M × N²)`. El secundario es el reloj, al 90% del límite, como red de seguridad.

**Qué más se consideró.** Parar solo por reloj: haría que el resultado dependiera de la velocidad de la
máquina y rompería el determinismo. Parar por estancamiento: deja tiempo sin usar y agrega un parámetro
más. El presupuesto es una función de los datos de entrada, no de la velocidad real, así que la corrida
es reproducible; terminar antes del límite además favorece el tercer criterio de desempate del concurso,
que es el menor tiempo de cómputo.

**Calibración de `rendimiento`.** Vale 0.45e6 rasgos por segundo, medido en esta máquina. El
procedimiento fue correr el evolutivo con presupuesto infinito y límite de 6 segundos en cinco
instancias, calcular `evaluaciones/segundo × M × N²` y quedarse con el 75% del mínimo observado
(0.61e6, en la instancia más pequeña). Con ese valor, un límite de 10 segundos se consume en 5 a 8
segundos reales y el presupuesto siempre corta antes que el reloj. La medición hay que repetirla si se
corre en una máquina mucho más lenta: se baja el valor y listo, el algoritmo no cambia.

Importante para medir: los individuos buenos son unas tres veces más caros que los malos, porque dejan
el tablero despejado y entonces hay más celdas candidatas por paso. Calibrar con pesos malos sobreestima
la velocidad.

### Determinismo

**Decisión.** Un único `random.Random(semilla)` para población inicial, torneos, cruces y mutaciones.
Desempate de celdas por índice. Presupuesto derivado de los parámetros de entrada.

**Qué más se consideró.** Usar `random` global: se contamina con cualquier otro uso del proceso.
Hay un caso de borde declarado: si la máquina es tan lenta que el reloj corta antes de agotar el
presupuesto, el número de generaciones varía. La constante `rendimiento` está puesta a la mitad de lo
medido justamente para que eso no pase.

### Medida de esfuerzo

**Decisión.** Se devuelve el número de **evaluaciones de aptitud**, que es lo que pide el enunciado.
Cada evaluación es una partida completa.

**Qué más se consideró.** Contar rasgos evaluados o pasos del motor: más fino, pero no comparable con
los nodos expandidos del agente de búsqueda. `_jugar` ya devuelve el conteo de rasgos si se quiere para
el informe.

### Parámetros y procedimiento

**Decisión.** Los valores de `PARAMETROS` en el módulo. Se fijaron con `experimentos/barrido_evolutivo.py`,
que varía un parámetro a la vez desde la configuración base, sobre 4 instancias de calibración con K alto
y 3 semillas cada una, y escribe un CSV.

| Parámetro | Valor | Probados |
|---|---|---|
| `poblacion` | 24 | 12, 24, 48, 96 |
| `torneo` | 3 | 2, 3, 5 |
| `p_cruce` | 0.9 | 0.0, 0.6, 0.9 |
| `p_mut_gen` | 0.5 | 0.3, 0.5, 1.0 |
| `sigma_ini` | 0.60 | 0.3, 0.6, 1.2 |
| `sigma_fin` | 0.05 | 0.01, 0.05, 0.2 |
| `elitismo` | 2 | 1, 2, 4 |
| `ventana` | 8 | 0, 4, 8, 16 |

**Lectura honesta del barrido.** Todas las variantes quedaron entre 0.573 y 0.603 de fichas colocadas,
con desviación cercana a 0.08 sobre 12 corridas. El error estándar es de unos 0.023, así que ninguna
diferencia observada es distinguible del ruido. La conclusión que se reporta es que **el algoritmo es
robusto a estos parámetros en este régimen**, no que la base sea óptima. Población 12 fue la peor
(0.573), que es el único indicio de tendencia.

**Qué más se consideró.** Rejilla completa en vez de un parámetro a la vez: 972 combinaciones, no cabe
en el tiempo de una tarea corta. Barrido con límite de 2 segundos: suficiente para comparar, pero las
cifras finales del informe conviene correrlas con el límite real.

**Pendiente.** El CSV incluido se corrió en otra máquina. Vuelve a correrlo en la tuya con
`--limite 10 --semillas 5` antes de citar números en el informe.

### Rendimiento observado

Con límite de 5 segundos, frente al voraz con 3 semillas, en las instancias del repositorio
(medido en otra máquina; en esta, con límite 10, los resultados son iguales o mejores y la corrida
tarda entre 5 y 8 segundos):

| Instancia | voraz (colocadas/ocupadas) | evolutivo |
|---|---|---|
| n3_k6_m30_s1 | 15/9, 15/9, 21/9 | 30/6 en las tres semillas |
| n4_k10_m60_s2 | 58/16, 49/16, 43/16 | 60/10 |
| n5_k15_m100_s1 | 79/25, 87/25, 74/25 | 100/15 |
| n6_k20_m150_s1 | 124/36, 147/36, 85/36 | 150/20 |
| n7_k30_m200_s1 | 165/49, 126/49, 148/49 | 200/30 o 200/31 |

El evolutivo gana todas las instancias del repositorio y deja el tablero en aproximadamente K celdas
ocupadas, que es cerca del mínimo posible. Con K = N² (instancias generadas aparte, mucho más duras)
ya no las resuelve y coloca entre el 50% y el 70% de las fichas: ahí es donde conviene comparar contra
el agente de búsqueda.

### Limitaciones conocidas

- La política mira un solo paso. Si una instancia exige sacrificar una fusión ahora para lograr dos
  después, esta representación no lo puede expresar con ningún peso.
- El rasgo `encierro` es una aproximación: cuenta salidas sin simular la fusión completa.
- `_rasgos` lee `juego.vecinos` y `juego.color` directamente, por velocidad. Es acoplamiento con el motor,
  aunque solo de lectura.
- Las instancias del repositorio quedaron fáciles para esta política. Para el informe conviene agregar
  instancias con K cercano a N².

---

## Agentes de línea base (`agentes/base.py`)

### Propósito

**Decisión.** `aleatorio` y `voraz` existen para probar el motor y dar un punto de comparación.
No son entregables de la tarea.

**Qué más se consideró.** No incluirlos. Se mantuvieron porque el `voraz` es el piso contra el cual se
mide cualquier agente real, y porque las pruebas de integración los usan.

### `aleatorio`

**Decisión.** Celda vacía al azar con un `random.Random(semilla)` propio.

### `voraz`

**Decisión.** Elige la celda que libera más celdas, con `juego.simular()`, y desempata al azar.

**Qué más se consideró.** Desempate determinista. Se dejó aleatorio a propósito, para que la dispersión
entre semillas sea visible en la comparación.

---

## Agente de búsqueda

Pendiente. Cuando se implemente, este archivo debe crecer con las mismas secciones: representación del
estado, operador de sucesión, costo, prueba de meta, heurística y su admisibilidad, criterio de paro,
medida de esfuerzo (nodos expandidos) y parámetros.

---

## Cambio al motor

**Decisión.** Se agregó `juego.vecinos`, alias público de la tabla de vecinos precalculada, para que los
agentes la lean sin tocar un atributo privado. `clonar()` lo propaga.

**Qué más se consideró.** Dejar que los agentes usen `_vec` directamente, o exponer un método
`vecinos(i)`. El alias no agrega llamadas de función en el camino caliente.
