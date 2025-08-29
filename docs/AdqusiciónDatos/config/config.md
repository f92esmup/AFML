# Creación de config.py

Este archivo almacena la configuracion usando pydantic. Es un objeto que validara todos los parámetros de configuración que se incluyan tanto por cli como por el archivo de configuración config.yaml 

## Estructura.

En pydantic la estructura para el objeto que almacena la ingformación es un conjunto de clases. Tenemos la clase central "Config", el punto de entrada. Después tenemos clases secundarias como "DataDownloaderConfig" y "OutputConfig" que se crean para replicar la estructura del archivo config.yaml. Y así verificar cada tipo de parámetro.

## Lógica

### Clase config

En este caso definimo las claves principales / puntos de entrada de config.yaml fuera de cualquier tipo de estructura. Justo debajo del comando class. A cada valor, le asignamos las clases complementarias que simplemente dirá al código que dicho parámetro tiene la estructura de valores dado por la clase x.

En Config hemos difinido un constructor alternativo a init usando "@classmethod" y proporcionando cls como argumento.

**load_config:** recibe como entrada los argumentos de la cli y la dirección del archivo config.yaml. Seguidamente se abre el archivo de configuración y se extraen los datos.

Ahora lo que hacemos es crear nuevas variables dentro del diccionario donde hemos guardado el config.yaml. Para así tener los valores bien estructurados y que se puedan añadir usando la cli.

Cuando ya hemos añadido los argumentos faltantes. Devolvemos el objeto con cls(**yaml_config) 

**data_id** Es una función estática, es decir, no usa las variables de clase self. es simplemente un constructor de un nombre para identificación unívoca de los datos, data_id.

**_add_cli_args** Esta función incluye los argumentos de la cli en el diccionario donce hemos extraido el config.yaml. 

Tenemos un caso curioso en esta función. COmo nuestro constructor es distinto de "__init_()",  debemos asginarle al resto de funciones a las que queramos acceder el decorador @classmethod, y añadir como argumento cls en lugar de self. Tiene la misma función que self. 

### Resto de clases.

El resto de clases siguen la misma estructrura, heredan el BASEMODEL de pydantic y definen los distintos parámetros que tiene el config.yaml.

<details>
<summary> Como se usa Field() para estructurar parámetros </summary>
 
Claro. Aquí tienes un resumen sobre cómo se usa `Field` de Pydantic y sus posibilidades, basándonos en tu propio código.

`Field` es una función de Pydantic que te permite añadir información extra y reglas de validación a los campos de un modelo. Lo usas cuando una simple anotación de tipo como `symbol: str` no es suficiente.

En tu archivo config.py, ya estás usando `Field` para tres propósitos principales:

### 1. Definir Valores por Defecto y Campos Requeridos

-   **Campo Requerido (`...`):** Para indicar que un campo es obligatorio, usas `...` (el objeto Ellipsis de Python) como primer argumento de `Field`. Pydantic sabrá que debe dar un error de validación si no se proporciona un valor para este campo.
    ````python
    # filepath: /home/pedro/AFML/src/AdqusicionDatos/config/config.py
    // ...existing code...
    symbol: str = Field(..., description="Símbolo del par de trading, e.g., 'BTCUSDT'.")
    // ...existing code...
    ````

-   **Valor por Defecto (`default`):** Para que un campo sea opcional y tenga un valor predeterminado si no se proporciona, usas el argumento `default`.
    ````python
    # filepath: /home/pedro/AFML/src/AdqusicionDatos/config/config.py
    // ...existing code...
    limit: int = Field(default=1500, gt=0, le=1500, description="...")
    // ...existing code...
    ````

### 2. Añadir Metadatos y Documentación

Puedes hacer que tu configuración sea autodocumentada usando argumentos como `description` y `title`. Esto es muy útil para generar documentación automática o para que otros desarrolladores (o tú mismo en el futuro) entiendan el propósito de cada campo.

-   **Descripción (`description`):** Añade un texto explicativo sobre el campo.
    ````python
    # filepath: /home/pedro/AFML/src/AdqusicionDatos/config/config.py
    // ...existing code...
    interval: str = Field(description="Intervalo de tiempo para las velas, e.g., '1m', '5m', '1h'.")
    // ...existing code...
    ````

### 3. Aplicar Reglas de Validación

Esta es una de las características más potentes. `Field` te permite definir restricciones directamente en el modelo.

-   **Validación Numérica (`gt`, `lt`, `ge`, `le`):** Puedes forzar a que un número sea mayor que (`gt`), menor que (`lt`), mayor o igual que (`ge`), o menor o igual que (`le`) un valor.
    ````python
    # filepath: /home/pedro/AFML/src/AdqusicionDatos/config/config.py
    // ...existing code...
    # gt=0 (mayor que 0), le=1500 (menor o igual que 1500)
    limit: int = Field(default=1500, gt=0, le=1500, description="...")
    // ...existing code...
    ````

-   **Validación de Cadenas de Texto (`regex`):** Puedes asegurar que una cadena de texto cumpla con un formato específico usando una expresión regular.
    ````python
    # filepath: /home/pedro/AFML/src/AdqusicionDatos/config/config.py
    // ...existing code...
    # Asegura que la fecha tenga el formato YYYY-MM-DD
    start_date: str = Field(regex=r'^\d{4}-\d{2}-\d{2}$', description="...") # type: ignore
    // ...existing code...
    ````

### Otras Posibilidades Comunes de `Field`:

-   `min_length` / `max_length`: Para restringir la longitud de cadenas o listas.
-   `alias`: Para permitir que un campo sea poblado desde un nombre diferente (ej. en un JSON que usa `user-id` para tu campo `user_id`).
-   `default_factory`: Para crear valores por defecto dinámicos, como una lista vacía (`default_factory=list`) o la fecha y hora actual (`default_factory=datetime.now`).
-   `exclude`: Para evitar que un campo se incluya al exportar el modelo (ej. a un diccionario o JSON).

En resumen, `Field` transforma tus modelos de Pydantic de simples contenedores de datos a potentes validadores y sistemas de configuración autodocumentados.
</details>
También se puede hacer validaciones complejas con métods especificos de validación que se debe importar de la librería. De momento no he necesitado usar ninguna.

# Preguntas

<details> 
<summary> ¿CÓmo se puede añadir valores al diccionario ya cargado de taml_config? </summary>

Una vez que has cargado el contenido de un archivo YAML en un diccionario de Python, puedes añadir o modificar sus valores de varias maneras. La forma más común es tratando el diccionario como un objeto al que se le asignan valores a través de sus claves.

### Asignación directa

Puedes añadir una nueva clave o actualizar una existente con una simple asignación.

````python
# Suponiendo que yaml_config es el diccionario cargado
yaml_config = {'output': {'path': '/data/raw'}}

# Añadir una nueva clave-valor en el nivel superior
yaml_config['nueva_clave'] = 'nuevo_valor'

# El diccionario ahora es:
# {'output': {'path': '/data/raw'}, 'nueva_clave': 'nuevo_valor'}
````
</details>


<details>
<summary>¿Por qué `_add_cli_args` es un `@classmethod` si no es un constructor?</summary>

Es una buena observación. Aunque `_add_cli_args` no es un constructor, se utiliza `@classmethod` para que el método reciba la propia clase como su primer argumento (convencionalmente llamado `cls`).

La razón principal es que `_add_cli_args` necesita llamar a otro método de la misma clase: `_data_id`.

````python
# Dentro de _add_cli_args
yaml_config['output']['data_id'] = cls._data_id(args.symbol)
````

Al usar `@classmethod`, la función obtiene una referencia a la clase (`cls`) y puede invocar `cls._data_id(...)` de forma limpia. La alternativa sería usar `@staticmethod`, pero entonces tendrías que referenciar la clase por su nombre explícitamente (`Config._data_id(...)`), lo cual es menos flexible si en el futuro se crean subclases.

</details>


<details>
<summary>¿Por qué se envuelve el return del constructor con `return cls(**yaml_config)`?</summary>

Esta línea es la clave para crear y validar el objeto de configuración de Pydantic a partir de los datos que has recopilado. Vamos a desglosarla:

*   `cls`: Como `load_config` es un `@classmethod`, `cls` es una referencia a la propia clase `Config`. Por lo tanto, llamar a `cls(...)` es lo mismo que llamar al constructor `Config(...)`.

*   `**yaml_config`: Este es el operador de "desempaquetado de diccionario" de Python. Toma el diccionario `yaml_config` y convierte cada par clave-valor en un argumento de palabra clave para la función o constructor al que se está llamando.

**¿Cómo funciona en conjunto?**

1.  El método `load_config` prepara un diccionario, `yaml_config`, que contiene toda la configuración fusionada del archivo YAML y los argumentos de la línea de comandos.
2.  Supongamos que `yaml_config` tiene este aspecto:
    ````python
    {
        'data_downloader': {'symbol': 'BTCUSDT', 'interval': '1h', ...},
        'output': {'data_id': 'BTCUSDT_2025-08-29', ...}
    }
    ````
3.  La llamada `cls(**yaml_config)` se convierte en:
    ````python
    Config(
        data_downloader={'symbol': 'BTCUSDT', 'interval': '1h', ...},
        output={'data_id': 'BTCUSDT_2025-08-29', ...}
    )
    ````
4.  Pydantic intercepta esta llamada. Utiliza los argumentos `data_downloader` y `output` para inicializar los campos correspondientes del modelo `Config`. A su vez, utiliza los diccionarios internos para crear y validar las instancias de `DataDownloaderConfig` y `OutputConfig`.

En resumen, `return cls(**yaml_config)` es una forma elegante y potente de pasar un diccionario de datos directamente al constructor de Pydantic para que este se encargue de crear, poblar y validar el objeto de configuración completo en un solo paso.

</details>