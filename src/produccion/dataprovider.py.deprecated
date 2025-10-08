"""Proveedor de datos en tiempo real desde Binance Futures.

Gestiona WebSocket asíncrono, descarga historial inicial, mantiene ventana rodante
y calcula indicadores técnicos en cada nueva vela.
"""

import asyncio
import logging
import pandas as pd
import pandas_ta as ta  # Importar para extender DataFrame con .ta
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, AsyncGenerator
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig

log = logging.getLogger("AFML.DataProvider")


class DataProvider:
    """Proveedor de datos de mercado en tiempo real con cálculo de indicadores."""
    
    def __init__(self, config: ProductionConfig, scaler: StandardScaler) -> None:
        """
        Inicializa el proveedor de datos.
        
        Args:
            config: Configuración de producción
            scaler: Scaler para normalización (se usa en ObservacionBuilder, aquí solo para validar)
        """
        self.config = config
        self.scaler = scaler
        
        # Parámetros de configuración
        self.simbolo = config.simbolo
        self.intervalo = config.intervalo
        self.window_size = config.window_size
        
        # Parámetros de indicadores
        self.sma_short = config.sma_short
        self.sma_long = config.sma_long
        self.rsi_length = config.rsi_length
        self.macd_fast = config.macd_fast
        self.macd_slow = config.macd_slow
        self.macd_signal = config.macd_signal
        self.bbands_length = config.bbands_length
        self.bbands_std = config.bbands_std
        
        # Tamaño de ventana necesario: window_size + datos para indicadores
        # El indicador más largo es SMA_long (200)
        self.ventana_total = self.window_size + max(
            self.sma_long, 
            self.macd_slow, 
            self.bbands_length
        ) + 50  # Buffer adicional
        
        # DataFrame que mantiene la ventana rodante
        self.df_ventana: Optional[pd.DataFrame] = None
        
        # Cliente asíncrono de Binance
        self.client: Optional[AsyncClient] = None
        self.socket_manager: Optional[BinanceSocketManager] = None
        
        # Control de estado
        self.inicializado = False
        self.websocket_conectado = False
        
        log.info("✅ DataProvider inicializado")
        log.info(f"   Símbolo: {self.simbolo}")
        log.info(f"   Intervalo: {self.intervalo}")
        log.info(f"   Window size: {self.window_size}")
        log.info(f"   Ventana total requerida: {self.ventana_total}")
    
    async def inicializar(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        """
        Inicializa el cliente de Binance y descarga el historial inicial.
        
        Args:
            api_key: API key de Binance
            api_secret: API secret de Binance
            testnet: Si True, usa testnet; si False, usa producción real
        """
        try:
            log.info("Inicializando cliente de Binance...")
            
            # Crear cliente asíncrono
            if testnet:
                self.client = await AsyncClient.create(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=True
                )
                log.info("✅ Conectado a Binance TESTNET")
            else:
                self.client = await AsyncClient.create(
                    api_key=api_key,
                    api_secret=api_secret
                )
                log.warning("⚠️  Conectado a Binance PRODUCCIÓN REAL")
            
            # Descargar historial inicial
            await self.descargar_historial_inicial()
            
            self.inicializado = True
            log.info("✅ DataProvider inicializado completamente")
            
        except Exception as e:
            log.error(f"Error al inicializar DataProvider: {e}")
            raise
    
    async def descargar_historial_inicial(self) -> None:
        """
        Descarga el historial necesario para llenar la ventana inicial.
        """
        try:
            log.info(f"Descargando historial inicial ({self.ventana_total} velas)...")
            
            # Calcular fecha de inicio
            # Necesitamos suficiente historial para la ventana + indicadores
            klines = await self.client.futures_klines(
                symbol=self.simbolo,
                interval=self.intervalo,
                limit=self.ventana_total
            )
            
            if not klines:
                raise ValueError("No se pudo descargar historial inicial")
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Seleccionar y convertir columnas relevantes
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Establecer timestamp como índice
            df.set_index('timestamp', inplace=True)
            
            log.info(f"✅ Descargadas {len(df)} velas históricas")
            log.info(f"   Rango: {df.index.min()} a {df.index.max()}")
            
            # Calcular indicadores
            self.df_ventana = self._calcular_indicadores(df)
            
            log.info(f"✅ Ventana inicial preparada con {len(self.df_ventana)} filas")
            log.debug(f"Columnas: {list(self.df_ventana.columns)}")
            
        except Exception as e:
            log.error(f"Error al descargar historial inicial: {e}")
            raise
    
    def _calcular_indicadores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos sobre el DataFrame.
        Utiliza la misma lógica que preprocesamiento.py
        
        Args:
            df: DataFrame con columnas OHLCV
            
        Returns:
            DataFrame con indicadores añadidos
        """
        try:
            log.debug("Calculando indicadores técnicos...")
            
            df_copy = df.copy()
            
            # Asegurar que 'close' esté disponible para pandas_ta
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
            
            # NO eliminamos filas con NaN aquí - se mantienen en ventana_total
            # El ObservacionBuilder tomará las últimas window_size filas
            # y validará que no tengan NaN (activando protocolo emergencia si las hay)
            
            log.debug(f"Indicadores calculados para {len(df_copy)} filas")
            log.debug(f"Columnas finales: {list(df_copy.columns)}")
            
            return df_copy
            
        except Exception as e:
            log.error(f"Error al calcular indicadores: {e}")
            raise
    
    async def stream_velas(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream asíncrono de velas completas desde WebSocket.
        Yielde cada vez que se completa una vela nueva.
        
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
        if not self.inicializado:
            raise RuntimeError("DataProvider no inicializado. Llama a inicializar() primero.")
        
        try:
            # Crear socket manager
            self.socket_manager = BinanceSocketManager(self.client)
            
            # Conectar a kline stream
            stream_name = f"{self.simbolo.lower()}@kline_{self.intervalo}"
            log.info(f"Conectando a WebSocket: {stream_name}")
            
            async with self.socket_manager.kline_socket(symbol=self.simbolo, interval=self.intervalo) as stream:
                self.websocket_conectado = True
                log.info("✅ WebSocket conectado")
                
                while True:
                    try:
                        msg = await stream.recv()
                        
                        if msg['e'] == 'error':
                            log.error(f"Error en WebSocket: {msg}")
                            continue
                        
                        # Extraer información de la vela
                        kline = msg['k']
                        
                        # Solo procesar velas COMPLETADAS
                        if kline['x']:  # 'x' = is_closed
                            vela_data = {
                                'timestamp': datetime.fromtimestamp(kline['T'] / 1000),
                                'open': float(kline['o']),
                                'high': float(kline['h']),
                                'low': float(kline['l']),
                                'close': float(kline['c']),
                                'volume': float(kline['v']),
                                'is_closed': True
                            }
                            
                            log.info(f"📊 Nueva vela completa: {vela_data['timestamp']} - Close: {vela_data['close']}")
                            
                            # Actualizar ventana rodante
                            self._actualizar_ventana(vela_data)
                            
                            # Yielder la vela para el bucle principal
                            yield vela_data
                            
                    except asyncio.CancelledError:
                        log.info("Stream de velas cancelado")
                        break
                    except Exception as e:
                        log.error(f"Error al procesar mensaje del WebSocket: {e}")
                        # Continuar recibiendo mensajes
                        continue
                        
        except Exception as e:
            log.error(f"Error en stream de velas: {e}")
            self.websocket_conectado = False
            raise
        finally:
            self.websocket_conectado = False
            log.info("WebSocket desconectado")
    
    def _actualizar_ventana(self, vela_data: Dict[str, Any]) -> None:
        """
        Actualiza la ventana rodante con una nueva vela.
        Agrega la nueva vela al final y elimina la más antigua.
        
        Args:
            vela_data: Diccionario con datos de la vela
        """
        try:
            # Crear nueva fila
            nueva_fila = pd.DataFrame([{
                'timestamp': vela_data['timestamp'],
                'open': vela_data['open'],
                'high': vela_data['high'],
                'low': vela_data['low'],
                'close': vela_data['close'],
                'volume': vela_data['volume'],
            }])
            nueva_fila.set_index('timestamp', inplace=True)
            
            # Agregar a la ventana existente
            self.df_ventana = pd.concat([self.df_ventana, nueva_fila])
            
            # Recalcular TODOS los indicadores (para mantener precisión)
            # En una versión optimizada, podrías calcular incrementalmente
            self.df_ventana = self._calcular_indicadores(self.df_ventana)
            
            # Mantener solo las últimas N filas necesarias
            if len(self.df_ventana) > self.ventana_total:
                self.df_ventana = self.df_ventana.tail(self.ventana_total)
            
            log.debug(f"Ventana actualizada: {len(self.df_ventana)} filas")
            
        except Exception as e:
            log.error(f"Error al actualizar ventana: {e}")
            log.error("Detalles del error:", exc_info=True)
            # No lanzar excepción para no interrumpir el stream
    
    def get_ventana_normalizada(self) -> pd.DataFrame:
        """
        Retorna la ventana actual con indicadores (sin normalizar).
        La normalización se hace en ObservacionBuilder.
        
        Returns:
            DataFrame con ventana actual y todos los indicadores
        """
        if self.df_ventana is None:
            raise RuntimeError("Ventana no inicializada")
        
        # Resetear índice para tener timestamp como columna
        df_copy = self.df_ventana.reset_index().copy()
        
        return df_copy
    
    async def cerrar(self) -> None:
        """Cierra las conexiones y limpia recursos."""
        try:
            log.info("Cerrando DataProvider...")
            
            if self.socket_manager:
                # El socket se cierra automáticamente con el context manager
                self.socket_manager = None
            
            if self.client:
                await self.client.close_connection()
                log.info("✅ Cliente de Binance cerrado")
            
            self.websocket_conectado = False
            self.inicializado = False
            
        except Exception as e:
            log.error(f"Error al cerrar DataProvider: {e}")
