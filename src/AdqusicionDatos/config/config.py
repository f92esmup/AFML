"""Este script se encarga de la configuración del sistema de adquisición de datos."""

import yaml
from typing import Any, Dict
from pydantic import BaseModel, ValidationError

class Config(BaseModel):
    # Definimos los parámetros de configuración que esperamos recibir
    

    @classmethod
    def load_config(cls, arg: Dict[str, Any], file_path: str) -> "Config":
        """
        Con @classmethod definirmos esta función como un constructor alternativo a __init__
        La entrada es la ruta del archivo de configuración.
        La salida es una instancia de la clase Config. El operador ** descompone el diccionario en pares clave-valor.
        El orden no importa, lo que importa son que los nombres de config.yaml y de pydantic coincidan exactamente.
        """

        # Cargamos la configuración del config.yaml
        try:
            with open(file_path, "r") as file:
                config_data = yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ValueError(f"Error loading config: {e}")
        
        # Ahora incluimos los datos que se han introducido con argparse.
        config_data['argparse'] = arg

        return cls(**config_data)

##########################################################################################################
# A partir de aquí voy a incluir las clases que descomponen todos los parámetros de configuración.
##########################################################################################################