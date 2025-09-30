"""Configuración de la aplicación de producción"""

from pydantic import BaseModel, Field
from typing import List
import argparse
import yaml
import logging

# Cargamos el logging
log = logging.getLogger("config_logger")

##########################################################################################################
# Clases que descomponen los parámetros de configuración.
##########################################################################################################


class MarketStats(BaseModel):
    """Estadísticas de normalización del mercado."""

    count: int
    mean: List[List[float]]
    var: List[List[float]]


class PortfolioStats(BaseModel):
    """Estadísticas de normalización del portafolio."""

    count: int
    mean: List[float]
    var: List[float]


class ObsNorm(BaseModel):
    """Parámetros de normalización de las observaciones."""

    _clip_obs: float
    market: MarketStats
    portfolio: PortfolioStats


##########################################################################################################
# Clase de Configuración Principal
##########################################################################################################


class ProductionConfig(BaseModel):
    apalancamiento: float = Field(
        ..., ge=1, description="Nivel de apalancamiento del portafolio"
    )
    intervalo: str = Field(..., description="Intervalo de tiempo para los datos")
    simbolo: str = Field(..., description="Símbolo del activo a analizar")
    train_id: str = Field(..., description="Identificador del entrenamiento")
    model_path: str = Field(..., description="Ruta al modelo entrenado")
    obs_norm: ObsNorm = Field(
        ..., description="Parámetros de normalización de observaciones"
    )

    @classmethod
    def load_config(cls, args: argparse.Namespace) -> "ProductionConfig":
        """Carga la configuración desde los argumentos de línea de comandos"""

        config_path = f"entrenamientos/{args.train_id}/config_metadata.yaml"

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró el archivo de configuración: {args.config.file}"
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Error al analizar el archivo YAML: {e}")
        except Exception as e:
            raise RuntimeError(f"Error inesperado al cargar la configuración: {e}")

        # Seleccionamos solo los parámetros relevantes para Producción.
        try:
            config = {
                "apalancamiento": yaml_data.get("portafolio").get("apalancamiento"),
                "intervalo": yaml_data.get("Datasets").get("intervalo"),
                "simbolo": yaml_data.get("Datasets").get("symbol"),
                "train_id": args.train_id,
                "model_path": yaml_data.get("Output").get("model_path"),
                "obs_norm": yaml_data.get("obs_norm"),
            }
        except AttributeError as e:
            log.error(f"Error al extraer parámetros de configuración: {e}")
            raise

        return cls(**config)
