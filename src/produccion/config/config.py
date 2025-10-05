"""Configuración de la aplicación de producción"""

from pydantic import BaseModel, Field
from typing import List, Optional
import argparse
import yaml
import logging
import joblib
from sklearn.preprocessing import StandardScaler
import os

# Cargamos el logging
log = logging.getLogger("AFML.config")


##########################################################################################################
# Clase de Configuración Principal
##########################################################################################################


class ProductionConfig(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    apalancamiento: float = Field(
        ..., ge=1, description="Nivel de apalancamiento del portafolio"
    )
    intervalo: str = Field(..., description="Intervalo de tiempo para los datos")
    simbolo: str = Field(..., description="Símbolo del activo a analizar")
    train_id: str = Field(..., description="Identificador del entrenamiento")
    model_path: str = Field(..., description="Ruta al modelo entrenado")
    scaler_path: str = Field(..., description="Ruta al scaler de entrenamiento")
    is_live: bool = Field(..., description="Modo de ejecución: True=Live, False=Testnet")
    
    # Parámetros del entorno (necesarios para observación y control de riesgo)
    window_size: int = Field(..., description="Tamaño de la ventana de observación")
    max_drawdown_permitido: float = Field(..., description="Drawdown máximo permitido")
    umbral_mantener_posicion: float = Field(..., description="Umbral para mantener posición")
    normalizar_portfolio: bool = Field(..., description="Si normalizar observación de portfolio")
    
    # Parámetros del portfolio (simulación - NO usar para valores reales)
    # IMPORTANTE: capital_inicial NO se carga aquí porque debe obtenerse de Binance API
    # Los valores de comisión y slippage son solo referenciales del entrenamiento
    comision: float = Field(..., description="Comisión por operación (referencial)")
    slippage: float = Field(..., description="Slippage estimado (referencial)")
    
    # Parámetros de indicadores (necesarios para DataProvider)
    sma_short: int = Field(..., description="Período de SMA corto")
    sma_long: int = Field(..., description="Período de SMA largo")
    rsi_length: int = Field(..., description="Período de RSI")
    macd_fast: int = Field(..., description="Período rápido de MACD")
    macd_slow: int = Field(..., description="Período lento de MACD")
    macd_signal: int = Field(..., description="Período de señal de MACD")
    bbands_length: int = Field(..., description="Período de Bollinger Bands")
    bbands_std: float = Field(..., description="Desviación estándar de Bollinger Bands")
    
    # Scaler cargado (no se serializa en YAML)
    scaler: Optional[StandardScaler] = Field(default=None, exclude=True)

    @classmethod
    def load_config(cls, args: argparse.Namespace) -> "ProductionConfig":
        """Carga la configuración desde los argumentos de línea de comandos"""

        config_path = f"entrenamientos/{args.train_id}/config_metadata.yaml"

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
        except FileNotFoundError:
            log.error(f"No se encontró el archivo de configuración: {config_path}")
            raise FileNotFoundError(
                f"No se encontró el archivo de configuración: {config_path}"
            )
        except yaml.YAMLError as e:
            log.error(f"Error al analizar el archivo YAML: {e}")
            raise ValueError(f"Error al analizar el archivo YAML: {e}")
        except Exception as e:
            log.error(f"Error inesperado al cargar la configuración: {e}")
            raise RuntimeError(f"Error inesperado al cargar la configuración: {e}")

        # Seleccionamos solo los parámetros relevantes para Producción.
        try:
            config_dict = {
                # Datos básicos
                "apalancamiento": yaml_data["portafolio"]["apalancamiento"],
                "intervalo": yaml_data["data_downloader"]["interval"],
                "simbolo": yaml_data["data_downloader"]["symbol"],
                "train_id": args.train_id,
                "model_path": yaml_data["Output"]["model_path"],
                "scaler_path": yaml_data["Output"]["scaler_train_path"],
                "is_live": args.live,
                
                # Entorno
                "window_size": yaml_data["entorno"]["window_size"],
                "max_drawdown_permitido": yaml_data["entorno"]["max_drawdown_permitido"],
                "umbral_mantener_posicion": yaml_data["entorno"]["umbral_mantener_posicion"],
                "normalizar_portfolio": yaml_data["entorno"]["normalizar_portfolio"],
                
                # Portfolio
                # NOTA: capital_inicial NO se carga porque debe obtenerse de Binance API
                # Solo se cargan valores referenciales de comisión y slippage
                "comision": yaml_data["portafolio"]["comision"],
                "slippage": yaml_data["portafolio"]["slippage"],
                
                # Indicadores
                "sma_short": yaml_data["preprocesamiento"]["indicadores"]["SMA_short"],
                "sma_long": yaml_data["preprocesamiento"]["indicadores"]["SMA_long"],
                "rsi_length": yaml_data["preprocesamiento"]["indicadores"]["RSI_length"],
                "macd_fast": yaml_data["preprocesamiento"]["indicadores"]["MACD_fast"],
                "macd_slow": yaml_data["preprocesamiento"]["indicadores"]["MACD_slow"],
                "macd_signal": yaml_data["preprocesamiento"]["indicadores"]["MACD_signal"],
                "bbands_length": yaml_data["preprocesamiento"]["indicadores"]["BB_length"],
                "bbands_std": yaml_data["preprocesamiento"]["indicadores"]["BB_std"],
            }
        except (KeyError, AttributeError) as e:
            log.error(f"Error al extraer parámetros de configuración: {e}")
            raise ValueError(f"Parámetro faltante en configuración: {e}")

        # Crear instancia de configuración
        config_instance = cls(**config_dict)
        
        # Cargar el scaler
        log.info(f"Cargando scaler desde: {config_instance.scaler_path}")
        try:
            if not os.path.exists(config_instance.scaler_path):
                raise FileNotFoundError(f"Scaler no encontrado: {config_instance.scaler_path}")
            
            config_instance.scaler = joblib.load(config_instance.scaler_path)
            log.info("✅ Scaler cargado exitosamente")
            
            # Validar que el scaler tenga los atributos necesarios
            if not hasattr(config_instance.scaler, 'mean_') or not hasattr(config_instance.scaler, 'scale_'):
                raise ValueError("El scaler cargado no es válido (falta mean_ o scale_)")
                
        except Exception as e:
            log.error(f"Error al cargar el scaler: {e}")
            raise

        log.info(f"✅ Configuración cargada exitosamente")
        log.info(f"   Símbolo: {config_instance.simbolo}")
        log.info(f"   Intervalo: {config_instance.intervalo}")
        log.info(f"   Modo: {'LIVE' if config_instance.is_live else 'TESTNET'}")
        log.info(f"   Window size: {config_instance.window_size}")
        
        return config_instance
