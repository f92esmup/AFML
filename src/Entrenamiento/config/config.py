""" Configuración del entorno de entrenamiento"""
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any
import argparse
import yaml
from datetime import datetime

##########################################################################################################
# Clases que descomponen los parámetros de configuración.
##########################################################################################################
class PortafolioConfig(BaseModel):
    """ Configuración del portafolio de inversión. """
    capital_inicial: float = Field(..., gt=0, description="Capital inicial del portafolio.")
    apalancamiento: float = Field(..., gt=0, description="Nivel de apalancamiento permitido.")
    comision: float = Field(..., ge=0, le=0.1, description="Comisión por operación (fracción del 1).")
    slippage: float = Field(..., ge=0, le=0.1, description="Slippage por operación (fracción del 1).")

class EntornoConfig(BaseModel):
    """ Configuración del entorno de entrenamiento. """
    window_size: int = Field(..., gt=0, description="Número de velas en la ventana de observación.")
    max_drawdown_permitido: float = Field(..., gt=0, lt=1, description="Máximo drawdown permitido antes de terminar el episodio.")
    factor_aversion_riesgo: float = Field(..., gt=1, description="Factor de aversión al riesgo para la recompensa.")
    umbral_mantener_posicion: float = Field(..., gt=0, lt=1, description="Umbral para mantener la posición actual.")
    directorio_salida: str = Field(..., description="Directorio donde se guardarán los resultados.")

class DataDownloaderConfig(BaseModel):
    """ Configuración del descargador de datos. """

class OutputConfig(BaseModel):
    """ Configuración de la salida de datos. """

##########################################################################################################
# Clase de Configuración Principal
##########################################################################################################

class Config(BaseModel):
    portafolio: PortafolioConfig
    entorno: EntornoConfig

    @classmethod
    def load_config(cls, args: argparse.Namespace) -> "Config":
        """
        Carga la configuración desde un YAML, la fusiona con los argumentos de línea de comando
        y valida todo el conjunto. Los argumentos de línea de comando tienen prioridad.
        """
        try:
            with open(args.config, "r") as file:
                yaml_config = yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ValueError(f"Error al cargar el archivo de configuración: {e}")

        # Añadir la configuración del metadata_id ¿Cómo lo hago?
        
        # Añadir los argumentos de argaparse al diccionario de configuración.
        try:
            yaml_config = cls._add_cli_args(args, yaml_config)
        except KeyError as e:
            raise ValueError(f"Error: Falta un campo requerido en la configuración o el cli: {e}")

        try:
            return cls(**yaml_config)
        except ValidationError as e:
            print("Error: La configuración no es válida. Revisa los siguientes campos:")
            print(e)
            raise
    
    @classmethod
    def _add_cli_args(cls, args: argparse.Namespace, yaml_config: Dict[str, Any]) -> Dict[str, Any]:
        """Añade los argumentos de argparse al diccionario de configuración YAML."""

        # Sobrescribir con los argumentos de argparse
        yaml_config['data_downloader']['symbol'] = args.symbol

        return yaml_config
    
    @staticmethod
    def _run_id(symbol: str) -> str:
        """Devuelve el data_id para nombrar la carpeta de salida.
        El data_id es una combinación del símbolo y la fecha de creación.
        """
        date= datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"datasets/{symbol}_{date}"
