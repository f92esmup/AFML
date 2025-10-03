"""Configuración unificada del sistema de trading automatizado."""

import yaml
import os
import argparse
import logging
from typing import Any, Dict, Optional, Literal, List, Union, Tuple
from pydantic import BaseModel, ValidationError, Field
from datetime import datetime

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.train.config")


##########################################################################################################
# Clases de Configuración - Adquisición de Datos
##########################################################################################################

class IndicadoresConfig(BaseModel):
    """Configuración específica para los indicadores técnicos."""
    SMA_short: int = Field(..., gt=0, description="Periodo para la SMA de corto plazo.")
    SMA_long: int = Field(..., gt=0, description="Periodo para la SMA de largo plazo.")
    RSI_length: int = Field(..., gt=0, description="Periodo para el RSI.")
    MACD_fast: int = Field(..., gt=0, description="Periodo rápido para MACD.")
    MACD_slow: int = Field(..., gt=0, description="Periodo lento para MACD.")
    MACD_signal: int = Field(..., gt=0, description="Periodo de señal para MACD.")
    BB_length: int = Field(..., gt=0, description="Periodo para las Bandas de Bollinger.")
    BB_std: float = Field(..., gt=0, description="Número de desviaciones estándar para las Bandas de Bollinger.")


class PreprocesamientoConfig(BaseModel):
    """Configuración para el preprocesamiento de datos."""
    interpol_method: Literal[
        'linear', 'time', 'index', 'values', 'nearest', 'zero', 'slinear', 
        'quadratic', 'cubic', 'barycentric', 'krogh', 'polynomial', 'spline', 
        'piecewise_polynomial', 'from_derivatives', 'pchip', 'akima', 'cubicspline'
    ] = Field(..., description="Método de interpolación para rellenar valores NaN, e.g., 'linear', 'time'.")
    indicadores: IndicadoresConfig


class DataDownloaderConfig(BaseModel):
    """Configuración para la descarga de datos."""
    symbol: Optional[str] = Field(None, description="Símbolo del par de criptomonedas (ej. 'BTCUSDT').")
    interval: Optional[str] = Field(None, description="Intervalo de tiempo de las velas (ej. '1h', '4h', '1d').")
    start_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de inicio en formato 'YYYY-MM-DD'.")
    end_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de fin en formato 'YYYY-MM-DD'.")
    limit: int = Field(..., gt=0, le=1500, description="Límite máximo de datos por llamada a la API (máx 1500).")


##########################################################################################################
# Clases de Configuración - Entrenamiento
##########################################################################################################

class PortafolioConfig(BaseModel):
    """Configuración del portafolio de inversión."""
    capital_inicial: float = Field(..., gt=0, description="Capital inicial del portafolio.")
    apalancamiento: float = Field(..., gt=0, description="Nivel de apalancamiento permitido.")
    comision: float = Field(..., ge=0, le=0.1, description="Comisión por operación (fracción del 1).")
    slippage: float = Field(..., ge=0, le=0.1, description="Slippage por operación (fracción del 1).")


class EntornoConfig(BaseModel):
    """Configuración del entorno de entrenamiento."""
    window_size: int = Field(..., gt=0, description="Número de velas en la ventana de observación.")
    max_drawdown_permitido: float = Field(..., gt=0, lt=1, description="Máximo drawdown permitido antes de terminar el episodio.")
    factor_aversion_riesgo: float = Field(..., gt=1, description="Factor de aversión al riesgo para la recompensa.")
    umbral_mantener_posicion: float = Field(..., gt=0, lt=1, description="Umbral para mantener la posición actual.")
    penalizacion_no_operar: float = Field(..., ge=0, description="Penalización aplicada cuando el agente no realiza ninguna operación (recompensa == 0).")
    episodios: int = Field(0, ge=0, description="Número total de episodios para entrenar el agente.")


class NetArchConfig(BaseModel):
    """Configuración de la arquitectura de red."""
    pi: List[int] = Field(..., description="Capas de la red de política.")
    qf: List[int] = Field(..., description="Capas de las redes Q.")


class PolicyKwargsConfig(BaseModel):
    """Configuración de los argumentos de la política."""
    net_arch: NetArchConfig
    log_std_init: float = Field(..., description="Valor inicial de log(σ) para la política Gaussiana.")
    n_critics: int = Field(..., description="Número de críticos Q independientes.")


class SACModelConfig(BaseModel):
    """Configuración del modelo SAC."""
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


class DatasetConfig(BaseModel):
    """Información extraída del dataset (dataset metadata)."""
    train: str
    eval: Optional[str] = None
    symbol: Optional[str] = None
    intervalo: Optional[Union[str, int]] = None
    symbol_eval: Optional[str] = None
    intervalo_eval: Optional[Union[str, int]] = None


##########################################################################################################
# Clases de Configuración - Output
##########################################################################################################

class OutputDataAcquisitionConfig(BaseModel):
    """Configuración de salida para adquisición de datos."""
    root: str = Field(..., description="Prefijo de la carpeta de salida, identificado con el data_id.")
    data_filename: str = Field(..., description="Nombre del archivo de datos.")
    metadata_filename: str = Field(..., description="Nombre del archivo de metadatos.")
    scaler_filename: str = Field(..., description="Nombre del archivo del scaler.")


class OutputTrainingConfig(BaseModel):
    """Configuración de salida para entrenamiento."""
    base_dir: str = Field(..., description="Directorio base para guardar todos los outputs del entrenamiento.")
    model_path: str = Field(..., description="Ruta para guardar el modelo entrenado.")
    tensorboard_log: str = Field(..., description="Ruta para los logs de TensorBoard.")


##########################################################################################################
# Clase de Configuración Unificada
##########################################################################################################

class UnifiedConfig(BaseModel):
    """Configuración unificada del sistema de trading."""
    data_downloader: DataDownloaderConfig
    preprocesamiento: PreprocesamientoConfig
    portafolio: PortafolioConfig
    entorno: EntornoConfig
    SACmodel: SACModelConfig
    policy_kwargs: PolicyKwargsConfig
    output: Optional[Union[OutputDataAcquisitionConfig, OutputTrainingConfig, Dict[str, Any]]] = None
    Output: Optional[OutputTrainingConfig] = None  # Para mantener compatibilidad con código de entrenamiento
    Datasets: Optional[DatasetConfig] = None

    @classmethod
    def load_for_data_acquisition(cls, args: argparse.Namespace) -> "UnifiedConfig":
        """
        Carga la configuración para adquisición de datos.
        Utilizado por create_dataset.py
        """
        log.info("Cargando configuración para adquisición de datos...")
        
        try:
            # Cargar archivo YAML
            with open(args.config, "r", encoding="utf-8") as file:
                yaml_config = yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ValueError(f"Error al cargar el archivo de configuración: {e}")

        # Añadir argumentos CLI específicos de data acquisition
        try:
            yaml_config = cls._add_cli_args_data_acquisition(args, yaml_config)
        except KeyError as e:
            raise ValueError(f"Error: Falta un campo requerido en la configuración: {e}")

        try:
            config = cls(**yaml_config)
            log.info("Configuración de adquisición de datos cargada exitosamente")
            return config
        except ValidationError as e:
            log.error("Error: La configuración no es válida. Revisa los siguientes campos:")
            log.error(str(e))
            raise

    @classmethod
    def load_for_training(cls, args: argparse.Namespace) -> "UnifiedConfig":
        """
        Carga la configuración para entrenamiento.
        Utilizado por train.py
        """
        log.info("Cargando configuración del sistema de entrenamiento...")

        try:
            # Validar argumentos de entrada
            if args is None:
                raise ValueError("Los argumentos no pueden ser None")
            if not hasattr(args, "config") or not args.config:
                raise ValueError("Falta la ruta del archivo de configuración")

            log.debug(f"Cargando archivo de configuración: {args.config}")

            # Cargar archivo YAML
            try:
                with open(args.config, "r", encoding="utf-8") as file:
                    yaml_config = yaml.safe_load(file)

                if yaml_config is None:
                    raise ValueError("El archivo de configuración está vacío")

                log.debug("Archivo YAML cargado exitosamente")

            except FileNotFoundError as e:
                log.error(f"Archivo de configuración no encontrado: {args.config}")
                raise ValueError(f"Error al cargar el archivo de configuración: {e}")
            except yaml.YAMLError as e:
                log.error(f"Error de formato YAML: {e}")
                raise ValueError(f"Error al parsear el archivo YAML: {e}")

            # Añadir argumentos CLI
            try:
                log.debug("Integrando argumentos de línea de comandos...")
                yaml_config = cls._add_cli_args_training(args, yaml_config)
                log.debug("Argumentos CLI integrados exitosamente")
            except KeyError as e:
                log.error(f"Campo requerido faltante en configuración: {e}")
                raise ValueError(f"Error: Falta un campo requerido en la configuración: {e}")

            # Crear las rutas Output
            try:
                log.debug("Configurando rutas de salida...")
                yaml_config = cls._add_output_paths(yaml_config, args.data_id)
                
                # Intentar añadir metadata del dataset
                try:
                    yaml_config = cls._add_dataset_info(
                        yaml_config, args.data_id, getattr(args, "data_eval_id", None)
                    )
                    log.debug("Metadata del dataset integrada en la configuración")
                except Exception as e:
                    log.warning(f"No se pudo integrar metadata del dataset: {e}")
                
                log.debug("Rutas de salida configuradas exitosamente")
            except ValueError as e:
                log.error(f"Error al configurar rutas: {e}")
                raise

            # Crear y validar la configuración
            try:
                log.debug("Validando configuración final...")
                config_instance = cls(**yaml_config)
                log.info("Configuración cargada y validada exitosamente")
                return config_instance

            except ValidationError as e:
                log.error("Error de validación en la configuración:")
                for error in e.errors():
                    log.error(f"  - {error['loc']}: {error['msg']}")
                raise ValueError(f"La configuración no es válida: {e}")

        except Exception as e:
            log.error(f"Error crítico al cargar configuración: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    @classmethod
    def _add_cli_args_data_acquisition(
        cls, args: argparse.Namespace, yaml_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Añade los argumentos de argparse al diccionario de configuración YAML (data acquisition)."""
        
        # Sobrescribir con los argumentos de argparse
        yaml_config['data_downloader']['symbol'] = args.symbol
        yaml_config['data_downloader']['interval'] = args.interval
        yaml_config['data_downloader']['start_date'] = args.start_date
        yaml_config['data_downloader']['end_date'] = args.end_date or datetime.now().strftime('%Y-%m-%d')
        
        # Crear el data_id y configurar output
        data_id = cls._data_id(args.symbol)
        yaml_config['output'] = {
            'root': data_id,
            'data_filename': yaml_config.get('output', {}).get('data_filename', 'data.csv'),
            'metadata_filename': yaml_config.get('output', {}).get('metadata_filename', 'metadata.yaml'),
            'scaler_filename': yaml_config.get('output', {}).get('scaler_filename', 'scaler.pkl'),
        }
        
        return yaml_config

    @classmethod
    def _add_cli_args_training(
        cls, args: argparse.Namespace, yaml_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Añade los argumentos de argparse al diccionario de configuración YAML (training)."""
        log.debug("Procesando argumentos de línea de comandos...")

        try:
            # Validar que los argumentos requeridos estén presentes
            if not hasattr(args, "episodios"):
                raise KeyError("Falta el argumento 'episodios'")

            if args.episodios <= 0:
                raise ValueError(f"El número de episodios debe ser positivo: {args.episodios}")

            # Validar estructura de configuración
            if "entorno" not in yaml_config:
                raise KeyError("Falta la sección 'entorno' en la configuración")

            # Sobrescribir con los argumentos de argparse
            yaml_config["entorno"]["episodios"] = args.episodios

            log.debug(f"Episodios configurados: {args.episodios}")
            return yaml_config

        except Exception as e:
            log.error(f"Error al procesar argumentos CLI: {e}")
            raise

    @staticmethod
    def _data_id(symbol: str) -> str:
        """Devuelve el data_id para nombrar la carpeta de salida.
        El data_id es una combinación del símbolo y la fecha de creación.
        """
        date = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"datasets/{symbol}_{date}"

    @staticmethod
    def _train_id(yaml_config: Dict[str, Any], data_id: str) -> str:
        """Devuelve el train_id para nombrar la carpeta de salida del entrenamiento."""
        log.debug("Generando ID de entrenamiento...")

        try:
            # Validar parámetros de entrada
            if not data_id or not data_id.strip():
                raise ValueError("El data_id no puede estar vacío")

            timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Extraer parámetros clave con verificación
            required_keys: List[str] = ["SACmodel", "entorno"]
            for key in required_keys:
                if key not in yaml_config:
                    raise KeyError(f"Falta la sección '{key}' en la configuración")

            sac_config: Dict[str, Any] = yaml_config["SACmodel"]
            entorno_config: Dict[str, Any] = yaml_config["entorno"]

            # Validar y extraer parámetros específicos
            required_sac_keys: List[str] = ["learning_rate", "batch_size"]
            for key in required_sac_keys:
                if key not in sac_config:
                    raise KeyError(f"Falta '{key}' en la configuración SACmodel")

            if "window_size" not in entorno_config:
                raise KeyError("Falta 'window_size' en la configuración del entorno")

            lr: float = sac_config["learning_rate"]
            batch_size: int = sac_config["batch_size"]
            window_size: int = entorno_config["window_size"]

            train_id: str = (
                f"train_{data_id}_lr{lr}_bs{batch_size}_ws{window_size}_{timestamp}"
            )

            log.debug(f"Train ID generado: {train_id}")
            return train_id

        except KeyError as e:
            log.error(f"Configuración incompleta: {e}")
            raise ValueError(f"Error: Falta configuración requerida para crear train_id: {e}")
        except Exception as e:
            log.error(f"Error al generar train_id: {e}")
            raise ValueError(f"Error al generar train_id: {e}")

    @staticmethod
    def _add_output_paths(yaml_config: Dict[str, Any], data_id: str) -> Dict[str, Any]:
        """Añade rutas de salida compactas al diccionario de configuración YAML."""
        log.debug("Configurando rutas de salida...")

        try:
            # Validar parámetros de entrada
            if not data_id or not data_id.strip():
                raise ValueError("El data_id no puede estar vacío")

            train_id: str = UnifiedConfig._train_id(yaml_config, data_id)
            base_dir: str = f"entrenamientos/{train_id}"

            # Inicializar sección Output si no existe
            if "Output" not in yaml_config:
                yaml_config["Output"] = {}

            # Configurar rutas de salida
            output_config: Dict[str, str] = {
                "base_dir": base_dir,
                "model_path": f"{base_dir}/modelos/modelo",
                "tensorboard_log": f"{base_dir}/tensorboard/",
            }

            yaml_config["Output"].update(output_config)

            log.debug(f"Directorio base configurado: {base_dir}")
            return yaml_config

        except Exception as e:
            log.error(f"Error al configurar rutas de salida: {e}")
            raise ValueError(f"Error al configurar rutas de salida: {e}")

    @staticmethod
    def _add_dataset_info(
        yaml_config: Dict[str, Any], data_id: str, data_eval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lee datasets/{data_id}/metadata.yaml para extraer symbol e interval y los añade al yaml_config."""
        log.debug("Integrando información del dataset en la configuración...")

        if not data_id or not data_id.strip():
            raise ValueError("El data_id no puede estar vacío")

        # valores por defecto
        datasets_section: Dict[str, Any] = {
            "train": data_id,
            "eval": data_eval_id,
            "symbol": None,
            "intervalo": None
        }

        # Helper para leer metadata
        def _read_meta(path: str) -> Dict[str, Any]:
            try:
                if not os.path.exists(path):
                    log.debug(f"Metadata no encontrada: {path}")
                    return {}
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                log.error(f"Error leyendo metadata {path}: {e}")
                return {}

        # Leer metadata del dataset train
        train_meta = _read_meta(f"datasets/{data_id}/metadata.yaml")
        dd = train_meta.get("data_downloader", {})
        if dd:
            datasets_section["symbol"] = dd.get("symbol") or dd.get("symbol".lower())
            datasets_section["intervalo"] = dd.get("interval") or dd.get("intervalo") or dd.get("interval".lower())

        # Leer metadata del dataset eval si aplica
        if data_eval_id:
            eval_meta = _read_meta(f"datasets/{data_eval_id}/metadata.yaml")
            edd = eval_meta.get("data_downloader", {})
            if edd:
                datasets_section["symbol_eval"] = edd.get("symbol") or edd.get("symbol".lower())
                datasets_section["intervalo_eval"] = edd.get("interval") or edd.get("intervalo") or edd.get("interval".lower())

        # Añadir al yaml_config
        yaml_config["Datasets"] = datasets_section
        return yaml_config
