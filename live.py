"""Orquestador del modo LIVE / TESTNET"""

import logging

from src.AdqusicionDatos.utils.logger import setup_logger

from src.produccion import ProductionConfig, parse_args

# Configurar logger
setup_logger()
log: logging.Logger = logging.getLogger(f"AFML.{__name__}")


def main() -> None:
    """Función para ejecutar el proceso principal"""
    print("inciando modo LIVE / TESTNET")
    args = parse_args()

    print(args.train_id)

    config: ProductionConfig = ProductionConfig.load_config(args)

    print(config.intervalo)


if __name__ == "__main__":
    main()
