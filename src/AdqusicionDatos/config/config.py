"""Este script se encarga de la configuración del sistema de adquisición de datos."""

import yaml
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError, Field
from datetime import datetime
import argparse
##########################################################################################################
# Clases que descomponen los parámetros de configuración.
##########################################################################################################

class DataDownloaderConfig(BaseModel):
    """
    Configuración UNIFICADA para la descarga de datos.
    Los valores pueden venir del archivo YAML y ser sobrescritos por argparse.
    """
    # --- Argumentos que pueden venir de argparse o YAML ---
    symbol: str = Field(..., description="Símbolo del par de trading, e.g., 'BTCUSDT'.")
    interval: str = Field(..., description="Intervalo de tiempo para las velas, e.g., '1m', '5m', '1h'.")
    start_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de inicio en formato 'YYYY-MM-DD'.") # type: ignore
    end_date: Optional[str] = Field(..., default=None, regex=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de fin en formato 'YYYY-MM-DD'. Si no se proporciona, se usa la fecha actual.") # type: ignore
    
    # --- Argumentos que probablemente solo vengan del YAML ---
    limit: int = Field(..., gt=0, le=1500, description="Límite de velas por llamada, máximo 1500.")

class OutputConfig(BaseModel):
    """Configuración para los archivos de salida."""
    data_id: str = Field(..., description="Prefijo de la carpeta de salida, identificado con el data_id.")
    data_filename: str = Field(..., description="Nombre del archivo de datos.")
    metadata_filename: str = Field(..., description="Nombre del archivo de metadatos.")
    scaler_filename: str = Field(..., description="Nombre del archivo del scaler.")
    
##########################################################################################################
# Clase de Configuración Principal
##########################################################################################################

class Config(BaseModel):
    data_downloader: DataDownloaderConfig
    output: OutputConfig

    @classmethod
    def load_config(cls, args: argparse.Namespace, file_path: str) -> "Config":
        """
        Carga la configuración desde un YAML, la fusiona con los argumentos de línea de comando
        y valida todo el conjunto. Los argumentos de línea de comando tienen prioridad.
        """
        try:
            with open(file_path, "r") as file:
                yaml_config = yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ValueError(f"Error al cargar el archivo de configuración: {e}")

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
        yaml_config['data_downloader']['interval'] = args.interval
        yaml_config['data_downloader']['start_date'] = args.start_date
        yaml_config['data_downloader']['end_date'] = args.end_date or datetime.now().strftime('%Y-%m-%d')
        
        yaml_config['output']['data_id'] = cls._data_id(args.symbol)
        
        return yaml_config
    
    @staticmethod
    def _data_id(symbol: str) -> str:
        """Devuelve el data_id para nombrar la carpeta de salida.
        El data_id es una combinación del símbolo y la fecha de creación.
        """
        date= datetime.now().strftime('%Y-%m-%d')
        return f"{symbol}_{date}"
        