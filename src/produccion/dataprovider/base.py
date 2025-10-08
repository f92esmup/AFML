"""Clase base abstracta para proveedores de datos.

Define la interfaz común que deben implementar todos los proveedores de datos
(WebSocket, Polling, etc.) para garantizar compatibilidad con live.py.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig


class DataProviderBase(ABC):
    """
    Interfaz común para todos los proveedores de datos.
    
    Todos los proveedores deben implementar estos métodos para ser compatibles
    con el sistema de trading en producción.
    """
    
    def __init__(self, config: ProductionConfig, scaler: StandardScaler) -> None:
        """
        Inicializa el proveedor de datos.
        
        Args:
            config: Configuración de producción
            scaler: Scaler para normalización (usado en ObservacionBuilder)
        """
        self.config = config
        self.scaler = scaler
        
        # Parámetros de configuración comunes
        self.simbolo = config.simbolo
        self.intervalo = config.intervalo
        self.window_size = config.window_size
        
        # Parámetros de indicadores técnicos
        self.sma_short = config.sma_short
        self.sma_long = config.sma_long
        self.rsi_length = config.rsi_length
        self.macd_fast = config.macd_fast
        self.macd_slow = config.macd_slow
        self.macd_signal = config.macd_signal
        self.bbands_length = config.bbands_length
        self.bbands_std = config.bbands_std
        
        # Ventana total necesaria (window_size + buffer para indicadores)
        self.ventana_total = self.window_size + max(
            self.sma_long, 
            self.macd_slow, 
            self.bbands_length
        ) + 50  # Buffer adicional
        
        # DataFrame con ventana rodante
        self.df_ventana: Optional[pd.DataFrame] = None
        
        # Estado
        self.inicializado = False
    
    @abstractmethod
    async def inicializar(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        """
        Inicializa el proveedor de datos.
        
        Args:
            api_key: API key de Binance
            api_secret: API secret de Binance
            testnet: Si True, usa testnet; si False, usa producción real
        """
        pass
    
    @abstractmethod
    async def stream_velas(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream asíncrono de velas completas.
        
        Yields:
            Diccionario con información de la vela:
            {
                'timestamp': datetime,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': float,
                'is_closed': bool
            }
        """
        # Este es un método abstracto que debe implementarse como async generator
        # pylint: disable=unreachable
        yield  # type: ignore
        # pylint: enable=unreachable
    
    @abstractmethod
    def get_ventana_normalizada(self) -> pd.DataFrame:
        """
        Retorna la ventana actual con indicadores (sin normalizar).
        
        La normalización se hace posteriormente en ObservacionBuilder.
        
        Returns:
            DataFrame con ventana actual y todos los indicadores calculados
        """
        pass
    
    @abstractmethod
    async def cerrar(self) -> None:
        """
        Cierra las conexiones y limpia recursos.
        
        Debe liberar todas las conexiones de red, cerrar sockets,
        y limpiar cualquier recurso utilizado.
        """
        pass
    
    def _calcular_indicadores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos sobre el DataFrame.
        
        Implementación común para todos los proveedores.
        Utiliza la misma lógica que preprocesamiento.py del entrenamiento.
        
        Args:
            df: DataFrame con columnas OHLCV
            
        Returns:
            DataFrame con indicadores añadidos
        """
        import pandas_ta as ta
        import logging
        
        log = logging.getLogger(f"AFML.{self.__class__.__name__}")
        
        try:
            log.debug("Calculando indicadores técnicos...")
            
            df_copy = df.copy()
            
            # Validar que 'close' existe
            if 'close' not in df_copy.columns:
                raise ValueError("Columna 'close' no encontrada en el DataFrame")
            
            # SMA corto y largo
            df_copy.ta.sma(length=self.sma_short, append=True)
            df_copy.ta.sma(length=self.sma_long, append=True)
            
            # RSI
            df_copy.ta.rsi(length=self.rsi_length, append=True)
            
            # MACD
            df_copy.ta.macd(
                fast=self.macd_fast,
                slow=self.macd_slow,
                signal=self.macd_signal,
                append=True
            )
            
            # Bollinger Bands
            df_copy.ta.bbands(
                length=self.bbands_length,
                std=self.bbands_std,
                append=True
            )
            
            log.debug(f"Indicadores calculados para {len(df_copy)} filas")
            log.debug(f"Columnas finales: {list(df_copy.columns)}")
            
            return df_copy
            
        except Exception as e:
            log.error(f"Error al calcular indicadores: {e}")
            raise
