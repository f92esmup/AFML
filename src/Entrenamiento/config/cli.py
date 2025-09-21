""" Función para parsear los argumentos de la línea de comandos. """
import argparse
import logging
from typing import TYPE_CHECKING

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.cli")

def parse_args() -> argparse.Namespace:
    """ Parsea los argumentos de la línea de comandos para el entrenamiento del agente. """
    log.debug("Inicializando parser de argumentos de línea de comandos...")
    
    try:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Entrena un agente de aprendizaje por refuerzo usando SAC",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # Argumentos obligatorios
        parser.add_argument(
            "--data-id",
            type=str,
            required=True,
            help="ID del dataset a usar para el entrenamiento (ej: BTCUSDT_20250904_133047)"
        )

        parser.add_argument(
            "--data-eval-id",
            type=str,
            required=True,
            help="ID del dataset a usar para el entrenamiento (ej: BTCUSDT_20250904_133047)"
        )

        parser.add_argument(
            "--episodios",
            type=int,
            default=1,
            required=False,
            help="Número total de episodios para entrenar el agente"
        )
        
        parser.add_argument(
            "--config",
            type=str,
            default="src/Entrenamiento/config/config.yaml",
            required=False,
            help="Ruta al archivo de configuración YAML"
        )
        
        args: argparse.Namespace = parser.parse_args()
        
        # Validar argumentos básicos
        if not args.data_id or not args.data_id.strip():
            raise ValueError("El argumento --data-id no puede estar vacío")
        
        if args.episodios <= 0:
            raise ValueError(f"El número de episodios debe ser mayor que 0, recibido: {args.episodios}")
        
        log.debug(f"Argumentos parseados exitosamente: data_id={args.data_id}, episodios={args.episodios}")
        return args
        
    except ValueError as e:
        log.error(f"Error de validación en argumentos: {e}")
        raise
    except Exception as e:
        log.error(f"Error inesperado al parsear argumentos: {e}")
        log.error("Detalles del error:", exc_info=True)
        raise
