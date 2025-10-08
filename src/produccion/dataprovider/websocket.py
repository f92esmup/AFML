"""Proveedor de datos mediante WebSocket para alta frecuencia.

Ideal para intervalos cortos (< 15 minutos) donde se requiere
recepción de datos en tiempo real con mínima latencia.
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig
from .base import DataProviderBase
from .timesync import BinanceTimeSync

log = logging.getLogger("AFML.DataProviderWebSocket")


class DataProviderWebSocket(DataProviderBase):
    """
    Proveedor de datos mediante WebSocket de Binance.
    
    Recibe velas en tiempo real a través de WebSocket, ideal para
    trading de alta frecuencia (intervalos < 15 minutos).
    """
    
    def __init__(self, config: ProductionConfig, scaler: StandardScaler) -> None:
        """
        Inicializa el proveedor de datos por WebSocket.
        
        Args:
            config: Configuración de producción
            scaler: Scaler para normalización
        """
        super().__init__(config, scaler)
        
        # Cliente asíncrono de Binance
        self.client: Optional[AsyncClient] = None
        self.socket_manager: Optional[BinanceSocketManager] = None
        
        # Sincronización de tiempo
        self.time_sync: Optional[BinanceTimeSync] = None
        
        # Control de estado específico de WebSocket
        self.websocket_conectado = False
        self.velas_recibidas = 0
        
        log.info("✅ DataProviderWebSocket inicializado")
        log.info(f"   Símbolo: {self.simbolo}")
        log.info(f"   Intervalo: {self.intervalo}")
        log.info(f"   Método: WebSocket (tiempo real)")
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
            
            # Inicializar sincronización de tiempo
            self.time_sync = BinanceTimeSync(self.client, sync_interval_hours=1)
            await self.time_sync.sync()
            
            # Descargar historial inicial
            await self._descargar_historial_inicial()
            
            self.inicializado = True
            log.info("✅ DataProviderWebSocket inicializado completamente")
            
        except Exception as e:
            log.error(f"Error al inicializar DataProviderWebSocket: {e}")
            raise
    
    async def _descargar_historial_inicial(self) -> None:
        """Descarga el historial necesario para llenar la ventana inicial."""
        try:
            log.info(f"Descargando historial inicial ({self.ventana_total} velas)...")
            
            # Descargar klines desde Binance
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
    
    async def stream_velas(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream asíncrono de velas completas desde WebSocket.
        
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
            raise RuntimeError("DataProviderWebSocket no inicializado. Llama a inicializar() primero.")
        
        try:
            # Crear socket manager
            self.socket_manager = BinanceSocketManager(self.client)
            
            # Conectar a kline stream
            stream_name = f"{self.simbolo.lower()}@kline_{self.intervalo}"
            log.info(f"Conectando a WebSocket: {stream_name}")
            
            async with self.socket_manager.kline_socket(symbol=self.simbolo, interval=self.intervalo) as stream:
                self.websocket_conectado = True
                log.info("✅ WebSocket conectado y esperando velas...")
                
                while True:
                    try:
                        msg = await stream.recv()
                        
                        # Manejar errores del WebSocket
                        if msg['e'] == 'error':
                            log.error(f"❌ Error en WebSocket: {msg}")
                            continue
                        
                        # Extraer información de la vela
                        kline = msg['k']
                        
                        # Solo procesar velas COMPLETADAS
                        if kline['x']:  # 'x' = is_closed
                            self.velas_recibidas += 1
                            
                            vela_data = {
                                'timestamp': datetime.fromtimestamp(kline['T'] / 1000),
                                'open': float(kline['o']),
                                'high': float(kline['h']),
                                'low': float(kline['l']),
                                'close': float(kline['c']),
                                'volume': float(kline['v']),
                                'is_closed': True
                            }
                            
                            log.info(f"📊 Nueva vela completa: {vela_data['timestamp']} - Close: {vela_data['close']:.2f}")
                            
                            # Resincronizar tiempo periódicamente
                            if self.time_sync and self.time_sync.should_resync():
                                await self.time_sync.sync()
                            
                            # Actualizar ventana rodante
                            self._actualizar_ventana(vela_data)
                            
                            # Yield la vela para el bucle principal
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
            log.info(f"WebSocket desconectado (velas recibidas: {self.velas_recibidas})")
    
    def _actualizar_ventana(self, vela_data: Dict[str, Any]) -> None:
        """
        Actualiza la ventana rodante con una nueva vela.
        
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
            log.info("Cerrando DataProviderWebSocket...")
            
            if self.socket_manager:
                # El socket se cierra automáticamente con el context manager
                self.socket_manager = None
            
            if self.client:
                await self.client.close_connection()
                log.info("✅ Cliente de Binance cerrado")
            
            self.websocket_conectado = False
            self.inicializado = False
            
            log.info(f"✅ DataProviderWebSocket cerrado (total velas recibidas: {self.velas_recibidas})")
            
        except Exception as e:
            log.error(f"Error al cerrar DataProviderWebSocket: {e}")
