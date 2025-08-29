# Preprocesamiento.py

> **Resumen:** En este script vamos a recibie el dataframe resultante de adquisición.py. El cual ya ha sido somretido a la ELIMINACIÓN DE DUPLICADOS.  Haremos un proceso de limpieza, calculo de indicares y del scaler. Obteniendo como resultado el script ya limpio y listo para guardar. IMPORTANTE: no normalizamos los valores. solo calculamos el scaler ya que la normalización se debe hacer en el entorno, ya que por ejemplo durante una evaluación hay que normalizar datos con un scaler distinto.

Primero voy a estructurar las funciones de las clsases en las siguientes:
- UNa función principal orquestadora run.

- Una función que realiza el primer paso de la limpieza, comprobar que la serie de tiempo no tiene ningun valor faltante, y en caso de tenerlo hacer una interpolación.
- Calculamos los indicadores y los incluimos en el dataframe. Este sería otra función.

- Por último eliminamos los valores iniciales incompletos provenientes de la ventana de datos de los indicadores.

# Lógica de preprocesmiento

**run()**

**_continuidad**
Esta función se asegura de que no haya saltos temporales entre los datos. SU proceso es el siguiente:

1. Primero comprobamos que el formato del índice sea una instacia de datetime d epandas.

2.  Creamos el ínidice esperado a traves de la fecha de inicio y fin y del intervalo de tiempor usado.

3. Registramos las diferencias entre el índice esperado y el real. Para detectar los huecos.

4. DOnde hemos guardado los valores diferentes, comrpobamos si el objeto no tiene ningun elemento con .empty. QUe devuelve TRue si es el caso.

<details>
<summary> ¿Cómo verificamos que el formato del índice es el esperado? </summary>

Para asegurar que las operaciones de series temporales funcionen correctamente, es crucial que el índice del DataFrame sea del tipo `DatetimeIndex`. Esto se verifica con una simple comprobación al inicio de la función `_continuidad`.

El código utilizado es:
````python
if not isinstance(self.df.index, pd.DatetimeIndex):
    raise TypeError("El índice del DataFrame debe ser de tipo DatetimeIndex.")
````

**Desglose de la línea:**

*   **`isinstance(self.df.index, pd.DatetimeIndex)`**: Esta función de Python comprueba si el índice del DataFrame (`self.df.index`) es una instancia de la clase `pd.DatetimeIndex`. Devuelve `True` si lo es, y `False` en caso contrario.
*   **`if not ...`**: La condición se activa si el resultado de `isinstance` es `False`, es decir, si el índice **no** es del tipo esperado.
*   **`raise TypeError(...)`**: Si la condición se cumple, el programa se detiene inmediatamente y lanza un error (`TypeError`), informando al usuario que el formato del índice es incorrecto.

Esta es una práctica de **programación defensiva** que garantiza que la función no intente realizar operaciones de fecha/hora sobre un índice que no las soporta, evitando así errores más complejos y difíciles de depurar más adelante.

</details>

<details>
<summary> ¿Cómo se crea el indice esperado?</summary>

La función `pd.date_range` de pandas es una herramienta muy potente para crear secuencias de fechas y horas.

La línea `full_index = pd.date_range(start=self.df.index.min(), end=self.df.index.max(), freq=self.interval)` hace lo siguiente:

1.  **`pd.date_range(...)`**: Le dice a pandas que quieres generar un índice de fechas (`DatetimeIndex`).

2.  **`start=self.df.index.min()`**: Define el punto de inicio de la secuencia. Toma la fecha y hora más antigua (`.min()`) que existe en el índice de tu DataFrame actual.

3.  **`end=self.df.index.max()`**: Define el punto final de la secuencia. Toma la fecha y hora más reciente (`.max()`) de tu índice.

4.  **`freq=self.interval`**: Este es el parámetro más importante aquí. Define la frecuencia o el "paso" entre cada fecha en la secuencia. El valor de `self.interval` (que viene de tu configuración, por ejemplo, `'1h'`, `'5m'`, `'1d'`) se usa para generar los puntos intermedios.

### En resumen:

Esta línea crea un **índice de tiempo ideal y sin huecos**. Comienza en el mismo punto que tus datos, termina en el mismo punto, y tiene una entrada para cada intervalo de tiempo (`self.interval`) entre el inicio y el fin.

**Ejemplo práctico:**

*   Si `self.df.index.min()` es `2025-08-29 10:00:00`.
*   Si `self.df.index.max()` es `2025-08-29 12:00:00`.
*   Y `self.interval` es `'30min'`.

La función `pd.date_range` generará el siguiente índice:
```
DatetimeIndex(['2025-08-29 10:00:00', '2025-08-29 10:30:00',
               '2025-08-29 11:00:00', '2025-08-29 11:30:00',
               '2025-08-29 12:00:00'],
              dtype='datetime64[ns]', freq='30min')
```
Este `full_index` se usa después para comprobar si a tu DataFrame original le falta alguna de estas marcas de tiempo.
</details>

<details>
<summary> ¿Cómo comparo los índices?</summary>

Esta línea de código utiliza el método `.difference()` de los índices de pandas para encontrar los huecos en tu serie temporal.

Funciona de manera muy similar a una operación de **diferencia de conjuntos** en matemáticas.

Vamos a desglosarlo:

*   **`full_index`**: Es tu índice ideal, completo y sin huecos que creaste en la línea anterior. Contiene todas las marcas de tiempo que *deberían* existir.
*   **`self.df.index`**: Es el índice real de tus datos, que podría tener saltos o huecos.
*   **`.difference(...)`**: Este método compara los dos índices y devuelve un nuevo índice que contiene todos los elementos que están en `full_index` pero **no** están en `self.df.index`.

### En resumen:

La variable `missing_timestamps` contendrá un índice con **exactamente las fechas y horas que le faltan a tu DataFrame**.

**Ejemplo práctico:**

*   Si `full_index` es `['10:00', '10:05', '10:10', '10:15']`.
*   Y `self.df.index` es `['10:00', '10:10', '10:15']` (le falta la marca de las `10:05`).

El resultado de `full_index.difference(self.df.index)` será un nuevo índice que contiene únicamente `['10:05']`.

El código luego usa esta variable en la línea `if not missing_timestamps.empty:` para comprobar si se encontró algún hueco y si es necesario tomar medidas (como reindexar el DataFrame).
</details>

<details>
<summary> ¿Si hay huecos como se añaden dichos valores? </summary>
La línea `self.df = self.df.reindex(full_index)` es el paso clave que **corrige los huecos** en tu serie temporal.

Su función es "conformar" o "ajustar" tu DataFrame (`self.df`) a un nuevo índice (`full_index`).

Así es como funciona:

1.  **Toma el `full_index`**: Este es el índice ideal, completo y sin saltos que creaste previamente.
2.  **Crea un nuevo DataFrame**: El método `.reindex()` no modifica el DataFrame original, sino que crea uno nuevo.
3.  **Mapea los datos**:
    *   Para cada fecha/hora en `full_index` que **ya existía** en el `self.df` original, copia la fila de datos correspondiente.
    *   Para cada fecha/hora en `full_index` que **no existía** en el `self.df` original (es decir, los huecos que detectaste), crea una nueva fila y la rellena con valores `NaN` (Not a Number).
4.  **Asigna el resultado**: Finalmente, `self.df = ...` reemplaza el DataFrame antiguo por este nuevo DataFrame completo y con los huecos marcados como `NaN`.

5. Solo justo despues de ejecutarse el reindex, llamamos a _interpolate. De esta forma solo se le llama cuando realmente hay datos faltantes.

### En resumen:

Esta línea transforma un DataFrame con un índice discontinuo en un DataFrame con un **índice perfectamente continuo**, donde los datos faltantes están explícitamente representados como `NaN`.

**Ejemplo práctico:**

Si tu `self.df` original es:

| | open | close |
| :--- | :--- | :--- |
| **10:00** | 100 | 101 |
| **10:10** | 102 | 103 |

Y tu `full_index` es `['10:00', '10:05', '10:10']`.

El resultado de `self.df.reindex(full_index)` será:

| | open | close |
| :--- | :--- | :--- |
| **10:00** | 100.0 | 101.0 |
| **10:05** | NaN | NaN |
| **10:10** | 102.0 | 103.0 |

Esto deja el DataFrame perfectamente preparado para el siguiente paso, que es `_interpolacion()`, el cual se encargará de rellenar esos `NaN`.
</details>

**_interpolación**
Después de ejecutar _continuidad. Ya estamos seguros de que todos los índces están presentes. Y podemos calcular el valor aproximado donde están los NANs. Aunque no hayan datos faltante, es conveniente que se llame siempre a la función por si los datos originales tenian valores NANs.

<details>
<summary> ¿Cómo interpolo los valores del dataframe? </summary>

La interpolación es el proceso de estimar y rellenar valores faltantes (`NaN`) en una secuencia de datos. En pandas, esto se hace de forma muy sencilla con el método `.interpolate()`.

La línea de código clave es:
````python
self.df.interpolate(method='linear', inplace=True)
````

**Desglose de la línea:**

*   **`self.df.interpolate(...)`**: Es el método que se llama sobre el DataFrame. Su función es buscar valores `NaN` en todas las columnas numéricas y rellenarlos.
*   **`method='linear'`**: Este es el argumento más importante. Especifica la estrategia a seguir para rellenar los huecos.
    *   **`'linear'`**: Trata los valores como si estuvieran espaciados uniformemente. Para rellenar un hueco, traza una línea recta entre el último valor conocido *antes* del hueco y el primer valor conocido *después* del hueco. Los `NaN`s se reemplazan por los puntos que caen sobre esa línea.
*   **`inplace=True`**: Este argumento le dice a pandas que modifique el DataFrame `self.df` directamente, en lugar de devolver una nueva copia.

### ¿Cuál es el mejor método de interpolación para este caso?

Para datos de series temporales financieras (como precios de OHLC), la elección del método es crucial.

*   **`method='linear'` (Lineal):** **Esta es una excelente elección y el estándar para tu caso de uso.** Asume que el precio cambia a un ritmo constante durante el hueco. Para huecos pequeños (pocas velas faltantes), esta es una suposición muy razonable y produce resultados realistas sin distorsionar los datos.

*   **`method='time'` (Ponderado por tiempo):** Esta es una alternativa ligeramente más sofisticada. Es similar a `'linear'`, pero tiene en cuenta el intervalo de tiempo real del índice. Si tus huecos fueran de duración irregular, `'time'` sería superior. Como tú ya has asegurado un índice perfectamente regular con `reindex`, el resultado de `'time'` será prácticamente idéntico al de `'linear'`. Sigue siendo una opción de primera categoría.

*   **`method='pad'` o `'ffill'` (Forward Fill):** Rellena los `NaN` con el último valor válido conocido. Esto puede crear "mesetas" artificiales en los datos de precios, donde el precio se mantiene plano. Generalmente, no es ideal para columnas como `open`, `high`, `low`, `close`, pero a veces se considera aceptable para el `volume`.

**Conclusión:** El método `'linear'` que estás utilizando es la opción más común, robusta y recomendada para rellenar huecos en datos de precios de velas (OHLC) en una serie temporal con frecuencia regular.

</details>


<details>
<summary>¿Qué ocurre si hay datos no válidos que no son NaN (ej. "N/A")?</summary>

Este es un punto crítico. El método `.interpolate()` de pandas está diseñado para funcionar **exclusivamente** con el valor numérico especial `np.nan` (Not a Number).

Si en tus columnas numéricas (como `open`, `close`, `volume`, etc.) tienes valores como la cadena de texto `"N/A"`, `"null"`, o incluso un espacio en blanco, ocurrirán dos problemas principales:

1.  **Tipo de Dato Incorrecto:** Pandas verá que la columna contiene texto y la marcará con un `dtype` de `object` en lugar de un tipo numérico como `float64`.
2.  **La Interpolación los Ignora:** Cuando llames a `.interpolate()`, esta simplemente omitirá las columnas de tipo `object`. No dará un error, pero tampoco rellenará los valores "N/A", dejando el problema sin resolver.

### La Solución: Estandarizar los Valores Faltantes

La solución es convertir todos estos marcadores de datos faltantes no estándar al formato que pandas entiende (`np.nan`) **antes** de comenzar el preprocesamiento.

La forma más robusta de hacerlo es usando el método `.replace()`.

**¿Dónde colocar este código?**

El mejor lugar para este paso de limpieza es justo al principio, en el método `__init__` de tu clase `preprocesamiento`, antes de cualquier otra operación.

````python
# En preprocesamiento.py

import numpy as np
import pandas as pd

class preprocesamiento:
    
    def __init__(self, df: pd.DataFrame, config):
        
        # Lista de posibles valores que representan datos faltantes
        missing_values = ["N/A", "n/a", "null", "--"]
        
        # Reemplazar todos esos valores por np.nan
        df.replace(missing_values, np.nan, inplace=True)

        # Forzar la conversión de columnas a tipo numérico, por si acaso
        # 'coerce' convierte los valores que no se pueden transformar en NaN
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        self.df = df
        self.interval = config.data_downloader.interval
    
    # ... resto de la clase ...
````

Al añadir este bloque al inicio, te aseguras de que cuando los métodos `_continuidad` e `_interpolacion` se ejecuten, el DataFrame ya esté en un formato numérico limpio y estandarizado, permitiendo que la interpolación funcione correctamente sobre todos los tipos de datos faltantes

yO NO ME DEBO PREOCUPAR POR ESTO PARQUE YA HE USADO EL PD.TO_NUMERICO CON ERROR=COERCE EANTERIORMENTE. ENTONCES YA TENDRE LOS ERRONEOS EN NP.NAN

</details>

**_calculo_indicadores**

Este método se encarga de enriquecer el DataFrame añadiendo una variedad de indicadores técnicos que serán utilizados como características (features) para el modelo de machine learning.

<details>
<summary> ¿Por qué es tan útil y limpio usar pandas-ta?</summary>

La librería `pandas-ta` es extremadamente útil porque se integra a la perfección con los DataFrames de pandas, permitiendo calcular cientos de indicadores técnicos con una sintaxis muy limpia y declarativa.

La magia de `pandas-ta` reside en que, al importarla, añade un **accesor especial (`.ta`)** a tu DataFrame. Esto te permite llamar a los indicadores como si fueran métodos nativos del DataFrame.

**Principales Ventajas:**

1.  **Sintaxis Intuitiva:** El código es muy legible. En lugar de llamar a una función externa y pasarle columnas, simplemente haces `df.ta.nombre_indicador()`.

2.  **Auto-Añadido (`append=True`):** Esta es su característica más potente. Al usar el argumento `append=True`, `pandas-ta` calcula el indicador y **añade la nueva columna (o columnas) directamente a tu DataFrame**. Esto elimina la necesidad de gestionar la creación de nuevas Series y unirlas manualmente con `pd.concat` o `df.join`, evitando posibles errores de alineación de índices.

3.  **Nomenclatura Automática:** La librería nombra las nuevas columnas de forma estándar y descriptiva. Por ejemplo, `df.ta.rsi(length=14, append=True)` creará una columna llamada `RSI_14`.

4.  **Manejo de Indicadores Complejos:** Para indicadores que devuelven múltiples valores (como MACD o Bandas de Bollinger), `pandas-ta` añade todas las columnas necesarias de una sola vez, simplificando enormemente el código.

**Ejemplo de Implementación:**

Así es como se vería el método `_calculo_indicadores` usando este enfoque:

````python
def _calculo_indicadores(self) -> pd.DataFrame:
    """ 
    Metodo para calcular los indicadores técnicos usando la extensión .ta
    y añadirlos directamente al DataFrame.
    """
    print("Calculando indicadores técnicos...")

    # Cálculo de una Media Móvil Simple (SMA)
    self.df.ta.sma(length=50, append=True)

    # Cálculo del Índice de Fuerza Relativa (RSI)
    self.df.ta.rsi(length=14, append=True)

    # Cálculo de MACD (añade 3 columnas: MACD, Histograma y Señal)
    self.df.ta.macd(append=True)

    print("Indicadores calculados y añadidos al DataFrame.")
    return self.df
`````
</details>

**_eliminar_faltantes**

Esta función elimina todas las filas del dataframe con valores no válidos.


<details>
<summary> ¿Cómo elimino los NAN de un dataframe?</summary>

Para eliminar filas que contienen valores `NaN` en un DataFrame de pandas, se utiliza el método `.dropna()`. Este es el paso final de la limpieza, diseñado para eliminar las filas que han quedado incompletas después del cálculo de indicadores.

El código para esto es muy simple:
````python
self.df.dropna(inplace=True)
````

**Desglose de la línea:**

*   **`self.df.dropna(...)`**: Este método escanea el DataFrame y elimina las filas (o columnas) que contienen al menos un valor `NaN`.
*   **`inplace=True`**: Modifica el DataFrame `self.df` directamente, eliminando las filas sin necesidad de reasignarlo (`self.df = self.df.dropna()`).

### ¿Por qué es necesario este paso al final?

El cálculo de indicadores técnicos (como Medias Móviles, RSI, etc.) casi siempre requiere una "ventana" de datos históricos.

*   Por ejemplo, para calcular la Media Móvil de 20 periodos (`SMA_20`) para la vela de hoy, necesitas los precios de cierre de las 19 velas anteriores más la de hoy.
*   Esto significa que para las primeras 19 velas de tu conjunto de datos, es imposible calcular la `SMA_20`. La librería `pandas-ta` llenará el valor de la columna `SMA_20` para esas primeras 19 filas con `NaN`.

Estas filas con datos incompletos no son útiles para entrenar un modelo de machine learning, por lo que deben ser eliminadas.

**Ejemplo práctico:**

Imagina que calculas una `SMA_3` (Media Móvil de 3 periodos) sobre tus datos:

**Antes de `.dropna()`:**

| | close | SMA_3 |
| :--- | :--- | :--- |
| **10:00** | 100 | NaN |
| **10:05** | 102 | NaN |
| **10:10** | 101 | 101.0 |
| **10:15** | 103 | 102.0 |

Las dos primeras filas tienen `NaN` en la columna `SMA_3` porque no hay suficientes datos históricos para el cálculo.

**Después de `df.dropna(inplace=True)`:**

| | close | SMA_3 |
| :--- | :--- | :--- |
| **10:10** | 101 | 101.0 |
| **10:15** | 103 | 102.0 |

El método `.dropna()` ha eliminado todas las filas que contenían algún `NaN`, dejando un DataFrame completamente limpio y listo para ser utilizado.

</details>

**_scaler**

En esta función calculamos el scaler de nuestross datos. y el objeto se devuelve como salida.

El método de scaler que voy a utilizar para normalizar los datos es el stdou

<details>
<summary> ¿Cómo se define un scaler, como se ajusta y usa para transformar?</summary>

El escalado de características es un paso fundamental en el preprocesamiento de datos para muchos algoritmos de Machine Learning. Su objetivo es normalizar el rango de las variables independientes o características de los datos para que todas tengan una escala similar.

Un "scaler" es un objeto, generalmente de la librería `scikit-learn`, que aprende los parámetros necesarios para esta transformación a partir de los datos de entrenamiento y luego los aplica a cualquier conjunto de datos.

El proceso se divide en tres pasos clave: **definir**, **ajustar (`fit`)** y **transformar (`transform`)**.

### 1. Definir el Scaler

Primero, se crea una instancia del tipo de scaler que se desea utilizar. El más común para normalizar precios en un rango de [0, 1] es `MinMaxScaler`.

````python
from sklearn.preprocessing import MinMaxScaler

# 1. Definir: Creamos una instancia del scaler
scaler = MinMaxScaler()
````

### 2. Ajustar el Scaler (`.fit()`)

El método `.fit()` es el paso de "aprendizaje". El scaler analiza los datos que le pasas para calcular los parámetros de transformación necesarios. Para `MinMaxScaler`, `.fit()` calcula el valor mínimo y máximo de cada columna en los datos.

**¡Crucial!** El método `.fit()` **solo debe ejecutarse sobre los datos de entrenamiento**. Hacerlo sobre el conjunto completo (entrenamiento + prueba) introduciría información del futuro en el proceso de entrenamiento (*data leakage*), lo que llevaría a una evaluación demasiado optimista del rendimiento del modelo.

````python
# Supongamos que 'training_data' es un DataFrame de pandas con tus características
# 2. Ajustar: El scaler "aprende" los mínimos y máximos de los datos de entrenamiento
scaler.fit(training_data)
````

### 3. Usar para Transformar (`.transform()`)

Una vez que el scaler ha sido "ajustado", se puede usar su método `.transform()` para aplicar la transformación de escalado a cualquier conjunto de datos (entrenamiento, validación o prueba). Este método utiliza los parámetros aprendidos en el paso `.fit()` para escalar los nuevos datos.

````python
# 3. Transformar: Aplicamos la transformación a los datos de entrenamiento
scaled_training_data = scaler.transform(training_data)

# Cuando lleguen nuevos datos (ej. datos de prueba), usamos el MISMO scaler ya ajustado
# scaled_test_data = scaler.transform(test_data)
````

### El atajo: `.fit_transform()`

`scikit-learn` proporciona un método de conveniencia, `.fit_transform()`, que realiza ambos pasos (`fit` y `transform`) en una sola llamada. Es muy útil y eficiente, y se usa típicamente **solo sobre el conjunto de datos de entrenamiento**.

````python
# Ajustar y transformar en un solo paso sobre los datos de entrenamiento
scaled_training_data = scaler.fit_transform(training_data)
````

### Guardar y Cargar el Scaler

El objeto `scaler` ajustado es una pieza clave de tu modelo. Debes guardarlo para poder transformar nuevos datos en el futuro (por ejemplo, en producción) exactamente de la misma manera que transformaste los datos de entrenamiento. La librería `joblib` es la forma recomendada de hacerlo.

**Guardar el scaler:**
````python
import joblib

# Después de ajustar el scaler con scaler.fit(training_data)
joblib.dump(scaler, 'ruta/donde/guardar/scaler.joblib')
````

**Cargar el scaler:**
````python
import joblib

# En otro script o cuando necesites hacer predicciones
loaded_scaler = joblib.load('ruta/donde/guardar/scaler.joblib')

# Ahora puedes usar loaded_scaler para transformar nuevos datos
# nuevos_datos_escalados = loaded_scaler.transform(nuevos_datos)
````

</details>
