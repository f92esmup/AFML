"""Argument parser for the command line interface."""

import argparse
import logging

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.cli")


def parse_args() -> argparse.Namespace:
    """Parsear los argumentos de la línea de comandos"""
    log.debug("Inicializando parser de argumentos de línea de comandos...")

    try:
        # Creamos el parser:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Producción de un agente de aprendizaje por refuerzo usando SAC",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Argumentos obligatorios
        parser.add_argument(
            "--train-id",
            type=str,
            required=True,
            help="ID del agente entrenado a usar para la producción (ej: SAC_BTCUSDT_20250904_133047)",
        )

        parser.add_argument(
            "--live",
            action="store_true",
            help="Modo LIVE (si no se especifica, se asume TESTNET)",
        )
    except ValueError as ve:
        log.error(
            f"Error de valor al parsear los argumentos de la línea de comandos: {ve}"
        )
        raise ve
    except Exception as e:
        log.error(f"Error al parsear los argumentos de la línea de comandos: {e}")
        raise e

    args: argparse.Namespace = parser.parse_args()

    return args
