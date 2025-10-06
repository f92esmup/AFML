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
    symbol: str = Field(..., description="Símbolo del par de criptomonedas (ej. 'BTCUSDT').")
    interval: str = Field(..., description="Intervalo de tiempo de las velas (ej. '1h', '4h', '1d').")
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de inicio en formato 'YYYY-MM-DD'.")
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Fecha de fin en formato 'YYYY-MM-DD'.")
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
    
    # Normalización
    normalizar_portfolio: bool = Field(True, description="Activar normalización de portfolio observation (equity y PnL).")
    normalizar_recompensa: bool = Field(True, description="Usar retornos porcentuales en vez de absolutos para recompensas.")
    penalizacion_pct: float = Field(0.00001, ge=0, description="Penalización por no operar expresada como porcentaje del capital inicial.")
    
    # Nueva función de recompensa multifactorial
    factor_escala_recompensa: float = Field(100.0, gt=0, description="Factor de escala para normalizar recompensas a rango [-1, +1].")
    
    # Pesos de componentes
    peso_retorno_base: float = Field(1.0, ge=0, description="Peso del componente de retorno base.")
    peso_temporal: float = Field(0.3, ge=0, description="Peso del componente temporal (penalización/bonificación por tiempo).")
    peso_gestion: float = Field(0.2, ge=0, description="Peso del componente de gestión eficiente.")
    peso_drawdown: float = Field(0.15, ge=0, description="Peso del componente de penalización por drawdown.")
    peso_inaccion: float = Field(0.05, ge=0, description="Peso del componente de penalización por inacción.")
    
    # Penalización temporal por pérdidas
    umbral_perdida_pct: float = Field(0.005, ge=0, lt=1, description="Umbral de pérdida porcentual para activar penalización temporal.")
    factor_crecimiento_perdida: float = Field(0.05, ge=0, description="Factor de crecimiento de penalización por vela en pérdida.")
    
    # Bonificación por ganancias
    umbral_ganancia_pct: float = Field(0.005, ge=0, lt=1, description="Umbral de ganancia porcentual para activar bonificación.")
    factor_moderacion_ganancia: float = Field(0.3, ge=0, le=1, description="Factor de moderación de bonificación por ganancias.")
    factor_crecimiento_ganancia: float = Field(0.01, ge=0, description="Factor de crecimiento de bonificación por vela en ganancia.")
    
    # Gestión eficiente
    bonus_cierre_ganador: float = Field(0.02, ge=0, description="Bonificación base por cerrar posición ganadora.")
    penalizacion_cierre_perdedor: float = Field(-0.005, le=0, description="Penalización base por cerrar posición perdedora.")
    
    # Drawdown
    umbral_drawdown: float = Field(0.05, ge=0, lt=1, description="Umbral de drawdown antes de aplicar penalización.")
    factor_penalizacion_drawdown: float = Field(0.5, ge=0, description="Factor de penalización cuadrática por drawdown.")
    
    # Anti-inacción
    umbral_caida_equity: float = Field(0.002, ge=0, description="Umbral de caída de equity para penalizar inacción.")
    penalizacion_inaccion: float = Field(-0.005, le=0, description="Penalización por inacción cuando equity está cayendo.")


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

class OutputConfig(BaseModel):
    """Configuración de salida unificada para entrenamiento."""
    base_dir: str = Field(..., description="Directorio base para guardar todos los outputs del entrenamiento.")
    model_path: str = Field(..., description="Ruta para guardar el modelo entrenado.")
    tensorboard_log: str = Field(..., description="Ruta para los logs de TensorBoard.")
    scaler_train_path: str = Field(..., description="Ruta para guardar el scaler de entrenamiento.")
    scaler_eval_path: Optional[str] = Field(None, description="Ruta para guardar el scaler de evaluación (opcional).")
    metadata_filename: str = Field(default="config_metadata.yaml", description="Nombre del archivo de metadatos.")


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
    Output: Optional[OutputConfig] = None  # Configuración de salida unificada

    @classmethod
    def load_for_unified_training(cls, args: argparse.Namespace) -> "UnifiedConfig":
        """
        Carga la configuración para el flujo unificado de entrenamiento.
        Integra descarga de datos + entrenamiento + evaluación en un solo paso.
        Utilizado por train.py (nuevo flujo).
        """
        log.info("Cargando configuración para flujo unificado de entrenamiento...")

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

            # Integrar argumentos CLI (symbol, interval, fechas, episodios)
            try:
                log.debug("Integrando argumentos de línea de comandos...")
                yaml_config = cls._add_cli_args_unified(args, yaml_config)
                log.debug("Argumentos CLI integrados exitosamente")
            except KeyError as e:
                log.error(f"Campo requerido faltante en configuración: {e}")
                raise ValueError(f"Error: Falta un campo requerido en la configuración: {e}")

            # Crear las rutas de Output basadas en train_id
            try:
                log.debug("Configurando rutas de salida...")
                yaml_config = cls._add_output_paths_unified(args, yaml_config)
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
    def _add_cli_args_unified(
        cls, args: argparse.Namespace, yaml_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Añade los argumentos de argparse al diccionario de configuración YAML (flujo unificado)."""
        log.debug("Procesando argumentos de línea de comandos para flujo unificado...")

        try:
            # Configurar data_downloader con parámetros de ENTRENAMIENTO
            # (los de evaluación se configurarán dinámicamente durante la ejecución)
            yaml_config['data_downloader']['symbol'] = args.symbol
            yaml_config['data_downloader']['interval'] = args.interval
            yaml_config['data_downloader']['start_date'] = args.train_start_date
            yaml_config['data_downloader']['end_date'] = args.train_end_date

            # Configurar número de episodios
            if "entorno" not in yaml_config:
                raise KeyError("Falta la sección 'entorno' en la configuración")

            yaml_config["entorno"]["episodios"] = args.episodios

            log.debug(
                f"Argumentos integrados: symbol={args.symbol}, interval={args.interval}, "
                f"train={args.train_start_date} a {args.train_end_date}, episodios={args.episodios}"
            )
            return yaml_config

        except Exception as e:
            log.error(f"Error al procesar argumentos CLI: {e}")
            raise

    @staticmethod
    def _generate_train_id(
        symbol: str,
        train_start: str,
        train_end: str,
        yaml_config: Dict[str, Any]
    ) -> str:
        """Genera el train_id para nombrar la carpeta de salida del entrenamiento.
        
        Formato: train_{symbol}_{train_start}_{train_end}_lr{lr}_bs{batch}_ws{window}_{timestamp}
        """
        log.debug("Generando ID de entrenamiento...")

        try:
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

            # Formatear fechas para el ID (sin guiones)
            train_start_fmt = train_start.replace('-', '')
            train_end_fmt = train_end.replace('-', '')

            train_id: str = (
                f"train_{symbol}_{train_start_fmt}_{train_end_fmt}_"
                f"lr{lr}_bs{batch_size}_ws{window_size}_{timestamp}"
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
    def _add_output_paths_unified(
        args: argparse.Namespace, yaml_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Añade rutas de salida al diccionario de configuración YAML para el flujo unificado."""
        log.debug("Configurando rutas de salida para flujo unificado...")

        try:
            # Generar train_id
            train_id: str = UnifiedConfig._generate_train_id(
                args.symbol,
                args.train_start_date,
                args.train_end_date,
                yaml_config
            )
            base_dir: str = f"entrenamientos/{train_id}"

            # Configurar rutas de salida
            output_config: Dict[str, str] = {
                "base_dir": base_dir,
                "model_path": f"{base_dir}/modelos/modelo",
                "tensorboard_log": f"{base_dir}/tensorboard/",
                "scaler_train_path": f"{base_dir}/scaler_train.pkl",
                "scaler_eval_path": f"{base_dir}/scaler_eval.pkl",
                "metadata_filename": "config_metadata.yaml",
            }

            yaml_config["Output"] = output_config

            log.debug(f"Directorio base configurado: {base_dir}")
            return yaml_config

        except Exception as e:
            log.error(f"Error al configurar rutas de salida: {e}")
            raise ValueError(f"Error al configurar rutas de salida: {e}")
