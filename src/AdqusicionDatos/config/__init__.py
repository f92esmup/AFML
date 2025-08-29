"""

AFML - Configuración para la Adquisición de Datos

Este sub-módulo se encarga de la gestión de la configuración necesaria
para la adquisición de datos en el sistema de trading.
"""
from .config import Config
from .cli import parse_args

__all__ = [
    "Config",
    "parse_args"
    ]