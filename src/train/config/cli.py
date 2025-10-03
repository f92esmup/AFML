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
    """Parsea los argumentos de la línea de comandos para el entrenamiento unificado del agente."""
    log.debug("Inicializando parser de argumentos de línea de comandos...")

    try:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Entrena un agente de aprendizaje por refuerzo usando SAC con flujo unificado (descarga + entrenamiento + evaluación)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Argumentos obligatorios - Configuración del símbolo
        parser.add_argument(
            "--symbol",
            type=str,
            required=True,
            help="Símbolo del par de trading (ej: 'BTCUSDT')",
        )

        parser.add_argument(
            "--interval",
            type=str,
            required=True,
            help="Intervalo de tiempo para las velas (ej: '1m', '5m', '1h', '4h', '1d')",
        )

        # Argumentos obligatorios - Fechas de entrenamiento
        parser.add_argument(
            "--train-start-date",
            type=str,
            required=True,
            help="Fecha de inicio del periodo de entrenamiento en formato 'YYYY-MM-DD'",
        )

        parser.add_argument(
            "--train-end-date",
            type=str,
            required=True,
            help="Fecha de fin del periodo de entrenamiento en formato 'YYYY-MM-DD'",
        )

        # Argumentos obligatorios - Fechas de evaluación
        parser.add_argument(
            "--eval-start-date",
            type=str,
            required=True,
            help="Fecha de inicio del periodo de evaluación en formato 'YYYY-MM-DD'",
        )

        parser.add_argument(
            "--eval-end-date",
            type=str,
            required=True,
            help="Fecha de fin del periodo de evaluación en formato 'YYYY-MM-DD'",
        )

        # Argumentos opcionales
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
        if not args.symbol or not args.symbol.strip():
            raise ValueError("El argumento --symbol no puede estar vacío")

        if not args.interval or not args.interval.strip():
            raise ValueError("El argumento --interval no puede estar vacío")

        if args.episodios <= 0:
            raise ValueError(
                f"El número de episodios debe ser mayor que 0, recibido: {args.episodios}"
            )

        if args.episodios_eval <= 0:
            raise ValueError(
                f"El número de episodios de evaluación debe ser mayor que 0, recibido: {args.episodios_eval}"
            )

        # Validar formato de fechas
        import re
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        
        for date_arg, date_value in [
            ("train-start-date", args.train_start_date),
            ("train-end-date", args.train_end_date),
            ("eval-start-date", args.eval_start_date),
            ("eval-end-date", args.eval_end_date),
        ]:
            if not re.match(date_pattern, date_value):
                raise ValueError(
                    f"El argumento --{date_arg} debe estar en formato 'YYYY-MM-DD', recibido: {date_value}"
                )

        # Validar que las fechas de entrenamiento son coherentes
        from datetime import datetime
        train_start = datetime.strptime(args.train_start_date, '%Y-%m-%d')
        train_end = datetime.strptime(args.train_end_date, '%Y-%m-%d')
        eval_start = datetime.strptime(args.eval_start_date, '%Y-%m-%d')
        eval_end = datetime.strptime(args.eval_end_date, '%Y-%m-%d')

        if train_start >= train_end:
            raise ValueError(
                f"La fecha de fin de entrenamiento debe ser posterior a la de inicio: "
                f"{args.train_start_date} >= {args.train_end_date}"
            )

        if eval_start >= eval_end:
            raise ValueError(
                f"La fecha de fin de evaluación debe ser posterior a la de inicio: "
                f"{args.eval_start_date} >= {args.eval_end_date}"
            )

        # Validar que evaluación es posterior al entrenamiento (walk-forward)
        if train_end >= eval_start:
            raise ValueError(
                f"Las fechas de evaluación deben ser posteriores a las de entrenamiento para un walk-forward válido: "
                f"train_end={args.train_end_date} >= eval_start={args.eval_start_date}"
            )

        log.debug(
            f"Argumentos parseados exitosamente: symbol={args.symbol}, interval={args.interval}, "
            f"train={args.train_start_date} a {args.train_end_date}, "
            f"eval={args.eval_start_date} a {args.eval_end_date}, episodios={args.episodios}"
        )
        return args

    except ValueError as e:
        log.error(f"Error de validación en argumentos: {e}")
        raise
    except Exception as e:
        log.error(f"Error inesperado al parsear argumentos: {e}")
        log.error("Detalles del error:", exc_info=True)
        raise
