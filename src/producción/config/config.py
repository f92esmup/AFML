"""Configuración de la aplicación de producción"""

from pydantic import BaseModel, Field
import argparse
import yaml
import logging

# Cargamos el logging
log = logging.getLogger("config_logger")

##########################################################################################################
# Clases que descomponen los parámetros de configuración.
##########################################################################################################


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

    @classmethod
    def load_config(cls, args: argparse.Namespace) -> "ProductionConfig":
        """Carga la configuración desde los argumentos de línea de comandos"""

        try:
            with open(args.config.file, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró el archivo de configuración: {arg.config.file}"
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
                # OBS NORM FALTA POR AÑADIR
            }
        except AttributeError as e:
            log.error(f"Error al extraer parámetros de configuración: {e}")
            raise

        return cls(**config)
