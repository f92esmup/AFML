"""
AFML - Adquisición de Datos para el Trading Financiero Automatizado.

Este sub-módulo es responsable de la recopilación y procesamiento de datos
financieros relevantes para el sistema de trading.

Nota: DataPipeline ha sido deprecado. La funcionalidad de descarga y preprocesamiento
está ahora integrada directamente en train.py mediante los componentes individuales
DataDownloader y Preprocesamiento.
"""
from src.train.AdquisicionDatos.adquisicion import DataDownloader
from src.train.AdquisicionDatos.preprocesamiento import Preprocesamiento
from src.train.AdquisicionDatos.utils.logger import setup_logger

__all__ = [
    "DataDownloader",
    "Preprocesamiento",
    "setup_logger",
]
