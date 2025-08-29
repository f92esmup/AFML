"""
AFML - Adquisición de Datos para el Trading Financiero Automatizado.

Este sub-módulo es responsable de la recopilación y procesamiento de datos
financieros relevantes para el sistema de trading.
"""
from src.AdqusicionDatos.pipeline import DataPipeline
from src.AdqusicionDatos.config import Config, parse_args
from src.AdqusicionDatos.utils.logger import setup_logger

__all__ = [
    "DataPipeline",
      "Config",
      "parse_args",
      "setup_logger"
    ]