# Pipeline.py

>**Resumen** En este script definimos el flujo de trabajo para obtener los datos de la api de binance y guardarlos en un archivo .csv 

# Lógica de la clase

En esta clase vamos a tener las siguientes funciones:

* El constructor: que va a instanciar todos los objetos necesarios para realizar todo el flujo.

* Una función principal donde se ejecuta en orden cada paso.

* Una función que se encargue de guardar los elementos en sus respectivos directorios. No se crea en una clase independiente por que sería un ejemplo de sobreingeniería.


**_guardar_datos** 

En esta función voy a hacer el guardado de las tres datos importantes, el .csv, el scaler.pkl y el metadata.yaml. 

primero vamos a comprobar si existe las carpetas donde se van a guardar los objetos y si no existen se crean.

Luego guardamos los datos, el siguiente es el scaler y por último la configuración.s

<details>
<summary> ¿Cómo se puede guardar en un .yaml el objeto Config que he creado con pydantic? </summary>

Para guardar un objeto de configuración Pydantic en un archivo `.yaml`, necesitas dos pasos principales:

1.  Convertir el objeto Pydantic a un diccionario de Python.
2.  Usar una librería como `PyYAML` para escribir ese diccionario en un archivo con formato YAML.

Pydantic facilita el primer paso con su método `.model_dump()`.

### Pasos a seguir

**1. Instalar `PyYAML`**

Si aún no lo has hecho, instala la librería necesaria desde tu terminal:
````bash
pip install pyyaml
````

**2. Implementar el guardado en el código**

Puedes añadir un método a tu clase `Config` o crear una función de utilidad para realizar el guardado.

Aquí tienes un ejemplo de cómo hacerlo:

````python
import yaml
from pydantic import BaseModel

# Suponiendo que tu clase Config se ve así:
class IndicadoresConfig(BaseModel):
    SMA_short: int = 20
    SMA_long: int = 50

class PreprocesamientoConfig(BaseModel):
    indicadores: IndicadoresConfig = IndicadoresConfig()
    scaler_path: str = "models/scaler.joblib"

class Config(BaseModel):
    preprocesamiento: PreprocesamientoConfig = PreprocesamientoConfig()
    
    def save_to_yaml(self, file_path: str):
        """
        Guarda la configuración actual en un archivo YAML.
        """
        # 1. Convertir el objeto Pydantic a un diccionario
        config_dict = self.model_dump()

        # 2. Escribir el diccionario en un archivo YAML
        with open(file_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        print(f"Configuración guardada en: {file_path}")

# --- Ejemplo de uso ---
# Crear una instancia de tu configuración
config_actual = Config()

# Llamar al método para guardarla
config_actual.save_to_yaml("metadata.yaml")
````

**Desglose del código:**

*   **`self.model_dump()`**: Este es el método clave de Pydantic. Convierte la instancia de la clase `Config` (incluyendo todos sus modelos anidados) en un diccionario estándar de Python.
*   **`import yaml`**: Importa la librería `PyYAML`.
*   **`with open(file_path, 'w') as f:`**: Abre el archivo de destino en modo escritura (`'w'`). El `with` se asegura de que el archivo se cierre correctamente.
*   **`yaml.dump(config_dict, f, ...)`**: Esta función toma el diccionario y lo escribe en el archivo `f` con formato YAML.
    *   `default_flow_style=False`: Asegura que el YAML se escriba en el formato de bloque (más legible), en lugar de todo en una línea.
    *   `sort_keys=False`: Mantiene el orden original de las claves del diccionario, lo cual es preferible para archivos de configuración.

</details>


<details>
<summary> ¿Cómo guardo un objeto scaler? </summary>

Para guardar objetos de `scikit-learn` como un `StandardScaler` o `MinMaxScaler`, la forma recomendada es usar la librería `joblib`. Es más eficiente que el `pickle` estándar de Python para objetos que contienen grandes arrays de NumPy, como es el caso de los scalers ajustados.

### Pasos a seguir

**1. Instalar `joblib`**

Si aún no lo has hecho, instala la librería desde tu terminal:
````bash
pip install joblib
````

**2. Implementar el guardado**

La función `joblib.dump()` toma dos argumentos principales: el objeto que quieres guardar y la ruta del archivo donde lo quieres guardar. La extensión de archivo común para estos objetos es `.joblib` o `.pkl`.

````python
import joblib
from sklearn.preprocessing import StandardScaler
import pandas as pd

# Suponiendo que ya tienes un scaler ajustado
# scaler = StandardScaler()
# scaler.fit(tus_datos)

# Ruta donde se guardará el objeto
scaler_path = "models/scaler.joblib"

# Guardar el objeto scaler en el archivo
joblib.dump(scaler, scaler_path)

print(f"Scaler guardado en: {scaler_path}")
````

### Ejemplo en tu función `_guardar_datos`

Así es como se integraría en tu método `_guardar_datos` dentro de la clase `DataPipeline`:

````python
import joblib
import os
# ... otras importaciones

class DataPipeline:
    # ... __init__ y otros métodos

    def _guardar_datos(self, data: pd.DataFrame, scaler: StandardScaler) -> None:
        """ metodo para guardar los datos, el scaler y la metadata """
        # Rutas de los archivos
        root_dir = self.config.output.root
        data_path = os.path.join(root_dir, self.config.output.data_filename)
        scaler_path = os.path.join(root_dir, self.config.output.scaler_filename)
        metadata_path = os.path.join(root_dir, self.config.output.metadata_filename)

        # Creamos las carpetas si no existen
        os.makedirs(root_dir, exist_ok=True)

        # Guardamos el DataFrame en CSV
        print(f"Guardando datos en: {data_path}")
        data.to_csv(data_path, index=True)

        # Guardamos el scaler usando joblib
        print(f"Guardando scaler en: {scaler_path}")
        joblib.dump(scaler, scaler_path)

        # Guardamos la configuración (metadata)
        print(f"Guardando metadata en: {metadata_path}")
        self.config.save_to_yaml(metadata_path)
````

</details>

