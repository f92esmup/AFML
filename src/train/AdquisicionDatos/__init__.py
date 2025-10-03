"""
AFML - Adquisición de Datos para el Trading Financiero Automatizado.

Este sub-módulo es responsable de la recopilación y procesamiento de datos
financieros relevantes para el sistema de trading.
"""
from src.train.AdquisicionDatos.pipeline import DataPipeline
from src.train.AdquisicionDatos.utils.logger import setup_logger

__all__ = [
    "DataPipeline",
    "setup_logger",
]