
# Creación de adquisicion.py
Este archivo será no ejecutable. Contendrá unicamente una clase que organiza la descarga de datos serializada. Pienso incluir una función de descarga de datos klines y una función main que haga repetidas llamada para no sobrecargar el endpoint.

Para la descarga secuencias de dato en la api de binance. voy a crear una única clase que organice la descarga de datos. Estaba pensando en lo siguiente. 
- Crear una función __init__() inicializando el cliente de binance.
- Una función que descargue los datos desde la api, devolviendo unicamente los datos descargados. Proporcionando el simbolo, intervalo de vela, intervalo de descarga y límite de datos a descargar.
- Otra función que devuelva exactamente las fechas end y start para que no haya desincronización. Y el número de llamadas que hay que hacer.

- Una función run() que realice el proceso de descarga y devuelva el dataframe resultante.
- Una función que realice la conversión de datos lista, a dataframe con los formatos y nombres de columna adecuados.

> **Consideración:** Según las arquitectura SOLID. por la *D (Dependency Inversion Principle)*, es mejor que el __init__ recibiera un cliente ya creado. Esto se llama Inyección de Dependencias y facilita mucho las pruebas, ya que podrías pasarle un cliente "falso" (un mock) para testear la lógica de tu clase sin hacer llamadas reales a la API.

## Lógica de la clase:

### __init__()
La entrada son únicamente el cliente de binance y el objeto config. en esta función se descomponen todos los parámetros del config en variables autodefinidas. Para mayor claridad.

### _download_chunk
Recibe como entrada el periodo temporal en la que deseamos descargar los datos. Y dentro de la misma estas fechas se ajustan para que conincidan con el formato esperado por la api. Estos pares de datos se introducen así ya que cambian a lo largo de la ejecución.

<details>
<summary> Conversión de la fecha </summary>
```python
    start_ms = str(int(start_dt.timestamp() * 1000))
```

Se descompone en 4 pasos, ejecutados de adentro hacia afuera:

1.  **`start_dt.timestamp()`**
    *   **Qué hace**: Toma el objeto `datetime` de Python (ej. `datetime(2023, 1, 1)`) y lo convierte en un "timestamp de Unix".
    *   **Resultado**: Un número flotante que representa la cantidad de **segundos** transcurridos desde el 1 de enero de 1970. (ej. `1672531200.0`)

2.  **`... * 1000`**
    *   **Qué hace**: Multiplica el timestamp en segundos por 1000.
    *   **Por qué**: La API de Binance no trabaja con segundos, sino con **milisegundos**.
    *   **Resultado**: El timestamp en milisegundos, todavía como un número flotante. (ej. `1672531200000.0`)

3.  **`int(...)`**
    *   **Qué hace**: Convierte el número flotante a un número entero.
    *   **Por qué**: Elimina cualquier parte decimal que pudiera haber y asegura que el valor sea un número entero, que es lo que la API espera.
    *   **Resultado**: Un número entero. (ej. `1672531200000`)

4.  **`str(...)`**
    *   **Qué hace**: Convierte el número entero a una cadena de texto (string).
    *   **Por qué**: Aunque la librería a veces puede aceptar enteros, pasar el timestamp como un string es la forma más robusta y recomendada para los parámetros `startTime` y `endTime` de la función, evitando cualquier posible interpretación incorrecta.
    *   **Resultado Final**: Una cadena de texto que representa la fecha y hora exactas en milisegundos. (ej. `"1672531200000"`)

En resumen, la línea completa traduce un objeto `datetime` de Python, que es fácil de manipular, al formato de **string de timestamp en milisegundos** que la API de Binance entiende.
</details>

### _get_time_intervals:
Esta función recoge la fecha de inicio y fin que nosotros hemos configurado y crea una lista de tuplas con la fecha de inicio y fin. A partir de un registro donde asignamos a cada intervalo un lapso de tiempo equivalente al del objeto datetime de python. Esta magnitud, multiplicada por el límite de datos que podemos descarga en cada llamada. Es el incremento que hacemos en el tiempo en cada paso. Hata que se cumpla la condición de que la fecha de inicio actual es mas reciente que la de fin. 

### _process_to_dataframe
Esta función recibe todos los klines descargados en forma de lista. Si no hay ningun dato descargado se devuelve un dataframe vacio. EN caso contrario:
Creamos el dataframe a partir de la lista de valores y le asignamos un nombre a las columnas del dataframe. Luego, convertimos la columna de tiempo *timestamps* que está originalmente en *ms* a un formato de fecha estandar entendible para los humanos. Y acontinuación establecemos esa columna como el índice del dataframe.

Hay que tener en cuenta que la api de binance nos proporciona las datos como strings, no como números. Por ellos convertimos todos los datos que usaremos en números. 
<details>
<summary> Para que sirve el error = coerce</summary>
            df[col] = pd.to_numeric(df[col], errors='coerce')
Si no se especifica esta función lanza un error si no es capaz de convertir un str a un número (lo puede convertir a int, str... Según el resto de datos de la columna)
Con errors = 'coerce' le estamos diciendo que cuando no se pueda convertir a un número le asigne el valor N/A que es el estandar de not a number en pandas.
 
</details>

Esta función resuelve otro problema. Cuando hacemos el troceados de los intervalos de tiempo, peude ocurrir que alguna de las velas aparezca duplicadas debido a una sincronización erronea entre los límites. Por ello nos aseguramos que no haya valores duplicados.


<details>
<summary> ¿Cómo eliminamos los duplicados?</summary>

La línea `df = df[~df.index.duplicated(keep='first')]` es una forma concisa y eficiente en Pandas para eliminar filas con un índice duplicado, conservando únicamente la primera aparición.

Se descompone en tres partes, que se leen de adentro hacia afuera:

1.  **`df.index.duplicated(keep='first')`**
    *   Esto examina el índice del DataFrame (que en nuestro caso son los timestamps).
    *   Devuelve una serie de valores booleanos (`True`/`False`). Será `False` para la primera vez que aparece un timestamp y `True` para todas las apariciones posteriores de ese mismo timestamp.
    *   **Ejemplo:** Si el índice es `[t1, t2, t2, t3]`, esto devolvería `[False, False, True, False]`.

2.  **`~` (El operador de negación)**
    *   Este es el operador "NOT". Invierte los valores booleanos del paso anterior. `True` se convierte en `False` y `False` se convierte en `True`.
    *   **Ejemplo:** La serie `[False, False, True, False]` se convierte en `[True, True, False, True]`.

3.  **`df[...]` (El filtrado)**
    *   Esto es una selección booleana. El DataFrame `df` se filtra para conservar únicamente las filas donde la serie booleana interna es `True`.
    *   **Ejemplo:** Usando la serie `[True, True, False, True]`, Pandas se quedará con la primera fila (t1), la segunda fila (la primera aparición de t2) y la cuarta fila (t3). Descartará la tercera fila (el duplicado de t2).

**En resumen: la línea completa le dice a Pandas "dame todas las filas cuyo índice NO sea un duplicado (considerando la primera aparición como no duplicada)".** Esto limpia eficazmente los datos, eliminando las velas que se solaparon entre las distintas llamadas a la API.
</details>


Por último, la función devuelve el dataframe solo con las columnas de interes OHLCV.

### run()
Esta función va a realizar la orquestación de las funciones anteriores: 
1. Obtenemos los intervalos y definimos la lista donde almacenamos los klines que vayamos descargando
2. Recorremos cada tupla de intervals para los cuales haremos la llamada a la api y añadiremos dichos datos en nuestra lista.

<details>
<summary>¿Por qué se usa `extend` en lugar de `append`?</summary>

Se usa `extend` en lugar de `append` para **combinar los elementos de dos listas en una sola lista plana**, en lugar de anidar una lista dentro de otra. La elección es crucial para que Pandas pueda procesar los datos correctamente.

*   `all_klines_data` es la lista grande que acumula todas las velas.
*   `chunk` es la lista de velas que devuelve una única llamada a la API.

#### Comportamiento de `append` (Incorrecto en este caso)

`append` añade su argumento como **un único elemento** al final de la lista.

```python
all_klines_data = [ [vela_1], [vela_2] ]
chunk = [ [vela_3], [vela_4] ]

all_klines_data.append(chunk)

# El resultado sería una lista anidada:
# [ [vela_1], [vela_2], [ [vela_3], [vela_4] ] ] 
#                  ^--- El chunk entero es el tercer elemento
```
Esta estructura anidada es incorrecta y `pd.DataFrame` no podría procesarla para crear la tabla que queremos.

#### Comportamiento de `extend` (Correcto)

`extend` itera sobre su argumento y añade **cada uno de sus elementos** individualmente a la lista.

```python
all_klines_data = [ [vela_1], [vela_2] ]
chunk = [ [vela_3], [vela_4] ]

all_klines_data.extend(chunk)

# El resultado es una única lista plana:
# [ [vela_1], [vela_2], [vela_3], [vela_4] ]
```
Esta es exactamente la estructura que necesitamos: una única lista donde cada elemento es una vela. `pd.DataFrame` puede interpretar esta lista plana para crear el DataFrame correctamente.

**En resumen:** `extend` "desempaqueta" la lista `chunk` y añade sus contenidos a `all_klines_data`, mientras que `append` metería la lista `chunk` entera como un solo paquete dentro de `all_klines_data`.

</details>

3. hacemos la conversión de la lista a dataframe (**DONDE ELIMINAMOS DATOS DUPLICADOS**)
4. Devolvemos el dataframe resultante.


# Preguntas
<details>
<summary> ¿Qué datos/indicadores voy a utilizar? </summary>

La librería `python-binance` permite descargar una amplia variedad de datos de la plataforma Binance. Se pueden dividir en:

*   **Datos de Mercado (Públicos):**
    *   **Datos históricos de velas (K-lines/Candlesticks):** Datos OHLCV (Open, High, Low, Close, Volume) en diferentes intervalos de tiempo. Son la base para la mayoría de análisis técnicos y modelos de Machine Learning.
    *   **Libro de órdenes (Order Book):** Órdenes de compra y venta activas.
    *   **Trades recientes:** Últimas operaciones ejecutadas.
    *   **Datos de Ticker:** Resumen de las últimas 24h.

*   **Datos de Cuenta (Privados, requieren API Key):**
    *   Balances, historial de órdenes y trades personales.

*   **Datos de Futuros:**
    *   Datos de mercado específicos de futuros como el *funding rate* y el *open interest*.

Inicialmente, nos centraremos en los **datos históricos de velas (K-lines)** para los pares de criptomonedas de interés. Ya que son los más comunes. 

A partir de los datos OHLCV, calcularemos **indicadores técnicos** que servirán como *features* para el modelo.

**¿Por qué usar indicadores?**
Los indicadores transforman los datos de precios para resaltar patrones específicos como la tendencia, el momentum o la volatilidad. Aportan valor al darle al modelo "pistas" que no son obvias en los datos brutos.

**¿Cuántos y cuáles usar?**
La clave es la diversidad, no la cantidad. Un exceso de indicadores puede generar ruido. Un conjunto inicial sólido incluye:
*   **MACD:** Para tendencia y momentum.
*   **RSI:** Para medir la velocidad del precio (sobrecompra/sobreventa).
*   **Bandas de Bollinger:** Para medir la volatilidad.
*   **Media Móvil Simple (SMA):** Para la tendencia a largo plazo (ej. 50 o 200 periodos).

**¿Se deben conservar los datos OHLCV?**
**Sí, es fundamental.** Los datos OHLCV son la fuente de verdad. Los indicadores son derivados de ellos. Debemos proporcionar al modelo **tanto los datos OHLCV como los indicadores** para que tenga la máxima información disponible para aprender.
</details>

<details>
<summary> ¿A que procesos se va a someter los datos?</summary>

El flujo de procesamiento de datos es un pipeline estándar para preparar series temporales para Machine Learning. El orden es importante para asegurar la calidad de los datos.

1.  **Adquisición de Datos**: Descargar los datos OHLCV brutos desde la API de Binance.

2.  **Verificación de Integridad**: Comprobar que no existen "huecos" (timestamps faltantes) en la serie de datos.

3.  **Ingeniería de Características (Feature Engineering)**: Calcular los indicadores técnicos (MACD, RSI, etc.) y añadirlos como nuevas columnas.

4.  **Limpieza de Nulos (NaN)**: Los indicadores basados en ventanas (ej. una media móvil de 50 periodos) crearán valores nulos en las primeras filas. Estas filas deben ser eliminadas ya que no pueden ser utilizadas por el modelo.

5.  **Normalización / Estandarización**: Escalar todas las características numéricas (OHLCV e indicadores) a un rango común. Esto es fundamental porque los modelos de ML son sensibles a la escala de los datos. Características con magnitudes muy diferentes (ej. precio en 50,000 vs. RSI en 70) pueden sesgar el aprendizaje.

    **¿Qué método usar?**
    *   **`MinMaxScaler` (Normalización a [0, 1])**: Es muy sensible a valores atípicos (*outliers*). Un solo pico extremo en los datos puede distorsionar la escala para el resto de los puntos.
    *   **`StandardScaler` (Estandarización)**: Transforma los datos para que tengan una media de 0 y desviación estándar de 1. Es mucho más robusto frente a outliers, lo que lo convierte en la **opción recomendada para datos financieros**.

    **Procedimiento Crítico para Evitar Fuga de Datos (Data Leakage):**
    1.  **Dividir los datos** en conjuntos de entrenamiento, validación y prueba.
    2.  **Ajustar el escalador (`fit`)** usando **únicamente** los datos de **entrenamiento**.
    3.  **Transformar (`transform`)** todos los conjuntos (entrenamiento, validación y prueba) con el escalador ya ajustado.

Este pipeline asegura que el modelo reciba datos limpios, enriquecidos y en un formato óptimo para el entrenamiento.

Ademśa, es útil mantener la columna de precios duplicada, sin hacerle la normalización. Ya que se usará para calcular stoploss y otras cosas en el entorno.

</details>


<details>
<summary> ¿Cuál es el estandar para crear un sistema de configuración que se verifique asi mismo y actúe como única fuente de verdad?</summary>

Para crear un sistema de configuración robusto, que se valide a sí mismo y funcione como una única fuente de verdad, el estándar en el ecosistema de Python es combinar un **fichero de configuración legible** (como YAML) con una **librería de validación de datos** como **Pydantic**.

Este enfoque separa la configuración del código y garantiza que los parámetros sean correctos antes de que la aplicación se ejecute.

### Componentes del Sistema

1.  **Fichero de Configuración (ej. `config.yml`)**:
    *   **Propósito**: Almacenar todos los parámetros de configuración de forma centralizada y en un formato legible para humanos. Esto incluye claves de API, rutas de ficheros, parámetros del modelo, listas de características, etc.
    *   **Ventajas**: Fácil de modificar sin tocar el código. Permite tener diferentes configuraciones para desarrollo, pruebas y producción.

2.  **Modelo de Datos de Configuración (ej. `config.py` con Pydantic)**:
    *   **Propósito**: Definir la estructura esperada de la configuración usando clases de Python y anotaciones de tipo. Pydantic utiliza este modelo para:
        1.  Leer y parsear el fichero `config.yml`.
        2.  **Validar** que todos los campos necesarios existan.
        3.  **Coaccionar** los datos a los tipos de Python correctos (ej. convertir `"100"` a `100`).
        4.  Aplicar reglas de validación personalizadas (ej. un valor debe ser positivo).
    *   **Ventajas**:
        *   **Fuente Única de Verdad**: El resto de la aplicación importa y utiliza el objeto de configuración validado por Pydantic, no el fichero YAML directamente.
        *   **Autovalidación**: La aplicación falla al inicio si la configuración es inválida, con un error claro que indica qué parámetro está mal. Esto previene errores inesperados en tiempo de ejecución.
        *   **Soporte del IDE**: Al ser un objeto de Python tipado, se obtiene autocompletado y verificación de tipos en el editor.

### Flujo de Trabajo

1.  **Definir la estructura** en `config.yml`.
2.  **Crear un modelo Pydantic** en `config.py` que refleje esa estructura.
3.  Al iniciar la aplicación, **cargar el fichero YAML y pasarlo al modelo Pydantic** para crear una instancia de configuración global.
4.  **Usar esta instancia** en todo el proyecto para acceder a los parámetros de forma segura.

Este patrón asegura que la configuración sea explícita, validada y centralizada, eliminando una fuente común de errores en proyectos complejos.
</details>

<details>
<summary> ¿Que es un MOCK?</summary>
Esta pregunta surge por que para realizar la clase de descarga de datos desde la api de binance, me recomiendas crear el cliente externamente e introducirlo en el __init__ como un argumento.

Un mock te da control total sobre las dependencias de tu código durante las pruebas. Te permite aislar el código que quieres probar y simular cualquier escenario (éxito, fallo, datos extraños) de forma rápida, fiable y predecible. Por eso la Inyección de Dependencias es un principio tan importante para escribir código que se pueda probar fácilmente.
</details>

<details>
<summary>¿Cómo se usa la api de binance para descarga datos historicos de klines de futuros ? </summary>
Claro, aquí tienes el contenido para completar esa sección en tu archivo de preguntas.

<details>
<summary>¿Cómo se usa la api de binance para descarga datos historicos de klines de futuros ? </summary>

Para descargar datos históricos de futuros (USD-M Futures) con la librería `python-binance`, el proceso es muy similar a la descarga de datos del mercado spot, pero se utiliza un método específico: `client.futures_historical_klines()`.

Este método se encarga de apuntar al endpoint correcto de la API de Binance para los datos de futuros perpetuos.

### Componentes Clave

1.  **Instanciación del Cliente**: Se crea una instancia de `binance.client.Client`. No se necesita API key para datos públicos.
2.  **Método de Descarga**: Se llama a `client.futures_historical_klines()`.
3.  **Parámetros**: Los parámetros son los mismos que para los datos spot:
    *   `symbol`: El símbolo del contrato de futuros (ej. `'BTCUSDT'`).
    *   `interval`: El intervalo de las velas (ej. `Client.KLINE_INTERVAL_1HOUR`).
    *   `start_str`: La fecha de inicio como un string. La librería lo convierte internamente.
    *   `end_str`: La fecha de fin (opcional).
    *   `limit`: El número máximo de velas a devolver. **Para futuros, el máximo es 1500**.

### Estrategia de Descarga Eficiente

Para descargar grandes cantidades de datos (varios meses o años), es crucial minimizar el número de llamadas a la API. La estrategia correcta es:
1.  Establecer siempre el `limit` al máximo posible (`1500`).
2.  Implementar un bucle que realice múltiples llamadas, ajustando las fechas de inicio y fin en cada iteración hasta cubrir todo el periodo deseado.
### Otros Tipos de Futuros

La librería también distingue futuros con margen en criptomonedas (COIN-M). Para ellos, se usaría el método `client.futures_coin_historical_klines()`.
</details>

Claro, aquí tienes la explicación para añadir a tu archivo.

<details>
<summary>¿Por qué tengo que establecer las columnas de los datos descargados?</summary>

Tienes que establecer las columnas manualmente porque la API de Binance, y por extensión la librería `python-binance`, devuelve los datos históricos de velas (klines) en un formato crudo y sin etiquetas: una **lista de listas**.

Cada lista interna contiene los valores de una vela (timestamp, open, high, low, close, etc.) en un orden específico, pero sin nombres que los identifiquen.

**Ejemplo de la respuesta de la API:**
```python
[
  [1609459200000, '40000.0', '40100.0', '39900.0', '40050.0', '100.5', ...],  # Vela 1
  [1609459260000, '40050.0', '40200.0', '40050.0', '40150.0', '120.7', ...],  # Vela 2
  ...
]
```

Cuando creas un DataFrame de Pandas a partir de esta estructura con `pd.DataFrame(klines)`, Pandas no tiene forma de saber qué significa cada valor. Por defecto, nombraría las columnas con números enteros: `0`, `1`, `2`, etc.

```
# Sin especificar columnas
         0          1          2          3          4      5 ...
0  1609459200000  '40000.0'  '40100.0'  '39900.0'  '40050.0'  100.5 ...
1  1609459260000  '40050.0'  '40200.0'  '40050.0'  '40150.0'  120.7 ...
```

Al proporcionar una lista de nombres en el parámetro `columns`, le estás diciendo a Pandas: "El primer elemento de cada lista es el 'timestamp', el segundo es 'open', el tercero es 'high', y así sucesivamente".

Esto transforma los datos crudos y ambiguos en un DataFrame estructurado, legible y fácil de usar, donde puedes acceder a los datos por su nombre (`df['close']`) en lugar de por su posición (`df[4]`). El orden de los nombres que proporcionas debe coincidir exactamente con el orden definido en la documentación de la API de Binance.

</details>