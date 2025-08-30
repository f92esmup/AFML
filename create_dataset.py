""" Este script orquesta la creación del dataset completo."""
import logging
import sys # Añadido para capturar excepciones

from src.AdqusicionDatos import (
    DataPipeline,
    parse_args,
    setup_logger
    )
# Configurar logger.
setup_logger()
log = logging.getLogger(f"AFML.{__name__}")


def main():
    """Función principal para ejecutar el pipeline de datos."""
    log.info("--- Iniciando el script de creación de dataset ---")
    try:
        # Parsear argumentos de configuración
        log.info("1. Parseando argumentos de la línea de comandos.")
        args = parse_args()
        log.debug(f"Argumentos recibidos: {args}")

        # Inicializar el pipeline de datos
        log.info("2. Inicializando el DataPipeline.")
        pipeline = DataPipeline(args)

        # Ejecutar el pipeline
        log.info("3. Ejecutando el pipeline.")
        pipeline.run()
        
        log.info("--- Script de creación de dataset finalizado con éxito. ---")

    except Exception as e:
        log.error("!!! El script ha fallado de forma inesperada. !!!")
        log.error(f"Error: {e}", exc_info=True) # exc_info=True añade el traceback
        sys.exit(1) # Termina el script con un código de error


if __name__ == "__main__":
    main()