"""Módulo CLI unificado para adquisición de datos y entrenamiento."""

import argparse
import logging

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.config.cli")


def parse_args_data_acquisition() -> argparse.Namespace:
    """Parsea los argumentos de la línea de comandos para la adquisición de datos."""
    parser = argparse.ArgumentParser(
        description="Descarga de datos históricos de Binance Futures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="src/train/config/config.yaml",
        help="Ruta al archivo de configuración YAML.",
    )

    parser.add_argument(
        "--symbol",
        required=True,
        type=str,
        help="Símbolo del par de trading, e.g., 'BTCUSDT'.",
    )

    parser.add_argument(
        "--interval",
        required=True,
        type=str,
        help="Intervalo de tiempo para las velas, e.g., '1m', '5m', '1h'.",
    )

    parser.add_argument(
        "--start_date",
        required=True,
        type=str,
        help="Fecha de inicio en formato 'YYYY-MM-DD'.",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        default="",
        help="Fecha de fin en formato 'YYYY-MM-DD'. Si no se proporciona, se usa la fecha actual.",
    )

    return parser.parse_args()


def parse_args_training() -> argparse.Namespace:
    """Parsea los argumentos de la línea de comandos para el entrenamiento del agente."""
    log.debug("Inicializando parser de argumentos de línea de comandos...")

    try:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Entrena un agente de aprendizaje por refuerzo usando SAC",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Argumentos obligatorios
        parser.add_argument(
            "--data-id",
            type=str,
            required=True,
            help="ID del dataset a usar para el entrenamiento (ej: BTCUSDT_20250904_133047)",
        )

        parser.add_argument(
            "--data-eval-id",
            type=str,
            required=True,
            help="ID del dataset a usar para la evaluación (ej: BTCUSDT_20250904_133047)",
        )

        parser.add_argument(
            "--episodios",
            type=int,
            default=1,
            required=False,
            help="Número total de episodios para entrenar el agente",
        )

        parser.add_argument(
            "--episodios-eval",
            type=int,
            default=1,
            required=False,
            help="Número total de episodios para la evaluación",
        )

        parser.add_argument(
            "--config",
            type=str,
            default="src/train/config/config.yaml",
            required=False,
            help="Ruta al archivo de configuración YAML",
        )

        args: argparse.Namespace = parser.parse_args()

        # Validar argumentos básicos
        if not args.data_id or not args.data_id.strip():
            raise ValueError("El argumento --data-id no puede estar vacío")

        if args.episodios <= 0:
            raise ValueError(
                f"El número de episodios debe ser mayor que 0, recibido: {args.episodios}"
            )

        log.debug(
            f"Argumentos parseados exitosamente: data_id={args.data_id}, episodios={args.episodios}"
        )
        return args

    except ValueError as e:
        log.error(f"Error de validación en argumentos: {e}")
        raise
    except Exception as e:
        log.error(f"Error inesperado al parsear argumentos: {e}")
        log.error("Detalles del error:", exc_info=True)
        raise
