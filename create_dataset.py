""" Este script orquesta la creación del dataset completo."""
import logging

from src.AdqusicionDatos import (
    DataPipeline,
    parse_args,
    setup_logger
    )
# Configurar logger.
setup_logger()
log = logging.getLogger(f"AFML{__name__}")


def main():
    """Función principal para ejecutar el pipeline de datos."""
    # Parsear argumentos de configuración
    args = parse_args()

    # Inicializar el pipeline de datos
    pipeline = DataPipeline(args)

    # Ejecutar el pipeline
    pipeline.run()
    
if __name__ == "__main__":
    main()