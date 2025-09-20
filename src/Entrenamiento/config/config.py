""" Configuración del entorno de entrenamiento"""
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, List, Union, Tuple
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
    episodios: int = Field(..., gt=1, description="Número total de episodios para entrenar el agente.")

class NetArchConfig(BaseModel):
    """ Configuración de la arquitectura de red. """
    pi: List[int] = Field(..., description="Capas de la red de política.")
    qf: List[int] = Field(..., description="Capas de las redes Q.")

class PolicyKwargsConfig(BaseModel):
    """ Configuración de los argumentos de la política. """
    net_arch: NetArchConfig
    log_std_init: float = Field(..., description="Valor inicial de log(σ) para la política Gaussiana.")
    n_critics: int = Field(..., description="Número de críticos Q independientes.")

class VecNormalizeConfig(BaseModel):
    """ Configuración de VecNormalize. """
    norm_obs: bool = Field(..., description="Normalizar observaciones.")
    norm_reward: bool = Field(..., description="Normalizar recompensas.")
    clip_obs: float = Field(..., description="Límite para el clipping de observaciones.")
    gamma: float = Field(..., ge=0, le=1, description="Factor de descuento para normalización de recompensas.")

class SACModelConfig(BaseModel):
    """ Configuración del modelo SAC. """
    policy: str = Field(..., description="Tipo de política.")
    learning_rate: float = Field(..., gt=0, description="Tasa de aprendizaje.")
    buffer_size: int = Field(..., gt=0, description="Tamaño del replay buffer.")
    learning_starts: int = Field(..., gt=0, description="Pasos antes de empezar a entrenar.")
    batch_size: int = Field(..., gt=0, description="Tamaño del lote.")
    tau: float = Field(..., gt=0, le=1, description="Coeficiente de actualización suave.")
    gamma: float = Field(..., ge=0, le=1, description="Factor de descuento.")
    ent_coef: str = Field(..., description="Coeficiente de entropía.")
    train_freq: Tuple[int, str] = Field(..., description="Frecuencia de entrenamiento.")
    gradient_steps: int = Field(..., gt=0, description="Pasos de gradiente por actualización.")
    verbose: int = Field(..., ge=0, le=2, description="Nivel de verbosidad.")
    seed: int = Field(..., description="Semilla para reproducibilidad.")

class DataDownloaderConfig(BaseModel):
    """ Configuración del descargador de datos. """

class OutputConfig(BaseModel):
    """ Configuración de la salida de datos. """
    base_dir: str = Field(..., description="Directorio base para guardar todos los outputs del entrenamiento.")
    model_path: str = Field(..., description="Ruta para guardar el modelo entrenado.")
    vecnorm_path: str = Field(..., description="Ruta para guardar las estadísticas de VecNormalize.")
    tensorboard_log: str = Field(..., description="Ruta para los logs de TensorBoard.")

##########################################################################################################
# Clase de Configuración Principal
##########################################################################################################

class Config(BaseModel):
    portafolio: PortafolioConfig
    entorno: EntornoConfig
    SACmodel: SACModelConfig
    policy_kwargs: PolicyKwargsConfig
    Vecnormalize: VecNormalizeConfig
    Output: OutputConfig


    @classmethod
    def load_config(cls, args: argparse.Namespace) -> "Config":
        """Carga la configuración desde un YAML y la fusiona con los argumentos CLI."""
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

        # Crear las rutas Output:
        try:
            yaml_config = cls._add_output_paths(yaml_config, args.data_id)
        except ValueError as e:
            raise e  # Re-raise para mantener el mensaje específico
        except Exception as e:
            raise ValueError(f"Error inesperado al configurar rutas de salida: {e}")
        
        try:
            return cls(**yaml_config)
        except ValidationError as e:
            print("Error: La configuración no es válida. Revisa los siguientes campos:")
            print(e)
            raise
    
    @classmethod
    def _add_cli_args(cls, args: argparse.Namespace, yaml_config: Dict[str, Any]) -> Dict[str, Any]:
        """Añade los argumentos de argparse al diccionario de configuración YAML."""
        
        try:
            # Sobrescribir con los argumentos de argparse
            yaml_config['entorno']['episodios'] = args.episodios
            
            return yaml_config
        except Exception as e:
            raise ValueError(f"Error al procesar argumentos CLI: {e}")
    
    @staticmethod
    def _train_id(yaml_config: Dict[str, Any], data_id: str) -> str:
        """Devuelve el train_id para nombrar la carpeta de salida del entrenamiento."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Extraer parámetros clave con verificación
            lr = yaml_config['SACmodel']['learning_rate']
            batch_size = yaml_config['SACmodel']['batch_size']
            window_size = yaml_config['entorno']['window_size']  

            return f"train_{data_id}_lr{lr}_bs{batch_size}_ws{window_size}_{timestamp}"
        except KeyError as e:
            raise ValueError(f"Error: Falta configuración requerida para crear train_id: {e}")
        except Exception as e:
            raise ValueError(f"Error al generar train_id: {e}")
    
    @staticmethod
    def _add_output_paths(yaml_config: Dict[str, Any], data_id: str) -> Dict[str, Any]:
        """Añade rutas de salida compactas al diccionario de configuración YAML."""
        try:
            train_id = Config._train_id(yaml_config, data_id)

            base_dir = f"entrenamientos/{train_id}"
            yaml_config.setdefault('Output', {}).update({
                "base_dir": f"{base_dir}",
                'model_path': f"{base_dir}/modelos/modelo",
                'vecnorm_path': f"{base_dir}/modelos/vecnorm",
                'tensorboard_log': f"{base_dir}/tensorboard/"
            })

            return yaml_config
        except Exception as e:
            raise ValueError(f"Error al configurar rutas de salida: {e}")