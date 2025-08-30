# Logger.py

> **Resumen** Va a centralizar el sistema de logging en este script, y se le llamara para hacer los registros. Podría guardar el log en un archivo .log, pero de momento no.

## ¿Cómo funciona el logger?

Hola. Claro, te explico cómo funciona y cómo puedes implementarlo.

La idea de centralizar la configuración del logger en un solo script (como `utils/logger.py`) es una excelente práctica. Evita tener que repetir la configuración en cada fichero de tu proyecto.

El flujo general es el siguiente:

1.  **Crear un módulo de configuración:** Creas un fichero, por ejemplo `utils/logger.py`, que contiene una función para configurar y devolver un logger.
2.  **Configurar una sola vez:** En el punto de entrada principal de tu aplicación (normalmente `main.py` o similar), llamas a esta función de configuración una única vez.
3.  **Obtener el logger en otros módulos:** En cualquier otro script donde necesites registrar eventos, simplemente importas el módulo `logging` de Python y pides el logger por su nombre. No necesitas reconfigurarlo, ya que Python gestiona las instancias de logger de forma global.

Aquí tienes un ejemplo práctico de cómo podrías estructurarlo.

### 1. Crea tu script de configuración del Logger

Este script se encargará de definir el formato, el nivel y el destino de tus logs (consola, fichero, etc.).

````python
import logging
import sys

def setup_logger(log_level=logging.INFO):
    """
    Configura y devuelve un logger.
    Los logs se mostrarán en la consola.
    """
    # El nombre 'AFML_Logger' es un nombre raíz para tu aplicación.
    logger = logging.getLogger("AFML_Logger")
    logger.setLevel(log_level)

    # Evita añadir múltiples handlers si la función se llama más de una vez.
    if not logger.handlers:
        # Crea un handler para la salida estándar (consola).
        handler = logging.StreamHandler(sys.stdout)
        
        # Crea un formato para los mensajes de log.
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Asigna el formato al handler.
        handler.setFormatter(formatter)
        
        # Añade el handler al logger.
        logger.addHandler(handler)

    return logger
````

### 2. Inicializa el Logger en tu script principal

En el punto de entrada de tu aplicación, importa y ejecuta la función `setup_logger`.

````python
from utils.logger import setup_logger
import logging

# 1. Configura el logger UNA SOLA VEZ al inicio de tu aplicación.
# Todos los loggers que obtengas después heredarán esta configuración.
setup_logger()

# 2. Obtén una instancia del logger para este módulo específico.
# Es una buena práctica usar __name__ para que sepas de qué fichero viene el log.
log = logging.getLogger(f"AFML_Logger.{__name__}")

def run_analysis():
    log.info("Iniciando el análisis de datos.")
    # ... tu código de análisis aquí ...
    log.debug("Cargando datos del fichero X...")
    log.warning("Se encontró un valor faltante en la columna Y.")
    # ... más código ...
    log.info("Análisis completado con éxito.")

if __name__ == "__main__":
    run_analysis()
````

### 3. Usa el Logger en otros módulos

Ahora, en cualquier otro script, no necesitas volver a configurar nada. Simplemente pide el logger.

````python
import logging

# Simplemente obtén el logger. Usará la configuración ya establecida en main.py
# Usar 'AFML_Logger' como prefijo crea una jerarquía de loggers.
log = logging.getLogger(f"AFML_Logger.{__name__}")

def load_data_from_source(source: str):
    """
    Carga datos desde una fuente.
    """
    log.info(f"Intentando cargar datos desde: {source}")
    try:
        # ... Lógica para cargar los datos ...
        log.debug("Conexión a la fuente de datos establecida.")
        data = "datos de ejemplo" # Simulación
        log.info("Datos cargados correctamente.")
        return data
    except Exception as e:
        log.error(f"Fallo al cargar datos desde {source}: {e}", exc_info=True)
        # exc_info=True añade el traceback del error al log, muy útil para depurar.
        return None
````

### Resumen de tus preguntas:

*   **¿Cómo se configura?** Creando una función (`setup_logger`) que establece el nivel, formato y handlers.
*   **¿Tengo que llamarlo en cada script?** No. Configuras una vez en tu script principal. En los demás, solo pides la instancia del logger con `logging.getLogger()`.
*   **¿Dónde lo inicializo?** En el punto de entrada de tu aplicación (ej: `main.py`) antes de que se ejecute la lógica principal.

## ¿Em que ubicación se situan los 'hijos' del logger?
Pues justo debajo de los imports.