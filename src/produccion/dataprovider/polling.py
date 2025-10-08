"""Proveedor de datos mediante polling para baja frecuencia.

Ideal para intervalos largos (>= 15 minutos) donde se requiere
mayor robustez y no es crítica la latencia de milisegundos.
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, AsyncGenerator
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig
from .base import DataProviderBase
from .timesync import BinanceTimeSync

log = logging.getLogger("AFML.DataProviderPolling")


class DataProviderPolling(DataProviderBase):
    """
    Proveedor de datos mediante polling (REST API).
    
    Descarga velas periódicamente mediante REST API, ideal para
    trading de baja frecuencia (intervalos >= 15 minutos).
    
    Ventajas sobre WebSocket:
    - Más robusto (no se cae la conexión)
    - Más predecible (ejecución programada)
    - Menos recursos de red
    - Perfecto para timeframes largos
    """
    
    # Mapeo de intervalos a segundos
    INTERVAL_TO_SECONDS: Dict[str, int] = {
        '1m': 60,
        '3m': 180,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '2h': 7200,
        '4h': 14400,
        '6h': 21600,
        '8h': 28800,
        '12h': 43200,
        '1d': 86400,
        '3d': 259200,
        '1w': 604800,
    }
    
    def __init__(self, config: ProductionConfig, scaler: StandardScaler) -> None:
        """
        Inicializa el proveedor de datos por polling.
        
        Args:
            config: Configuración de producción
            scaler: Scaler para normalización
        """
        super().__init__(config, scaler)
        
        # Cliente asíncrono de Binance
        self.client: Optional[AsyncClient] = None
        
        # Sincronización de tiempo
        self.time_sync: Optional[BinanceTimeSync] = None
        
        # Duración del intervalo en segundos
        self.intervalo_segundos = self.INTERVAL_TO_SECONDS.get(self.intervalo, 3600)
        
        # Control de estado
        self.velas_descargadas = 0
        self.ultima_vela_timestamp: Optional[datetime] = None
        
        log.info("✅ DataProviderPolling inicializado")
        log.info(f"   Símbolo: {self.simbolo}")
        log.info(f"   Intervalo: {self.intervalo} ({self.intervalo_segundos}s)")
        log.info(f"   Método: Polling (REST API)")
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
            log.info("✅ DataProviderPolling inicializado completamente")
            
        except Exception as e:
            log.error(f"Error al inicializar DataProviderPolling: {e}")
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
            
            # Guardar timestamp de la última vela
            self.ultima_vela_timestamp = df.index.max()
            
            log.info(f"✅ Descargadas {len(df)} velas históricas")
            log.info(f"   Rango: {df.index.min()} a {df.index.max()}")
            log.info(f"   Última vela: {self.ultima_vela_timestamp}")
            
            # Calcular indicadores
            self.df_ventana = self._calcular_indicadores(df)
            
            log.info(f"✅ Ventana inicial preparada con {len(self.df_ventana)} filas")
            log.debug(f"Columnas: {list(self.df_ventana.columns)}")
            
        except Exception as e:
            log.error(f"Error al descargar historial inicial: {e}")
            raise
    
    async def stream_velas(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream simulado de velas mediante polling.
        
        Espera hasta el cierre de cada vela y luego descarga la vela cerrada
        mediante REST API. Más robusto que WebSocket para timeframes largos.
        
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
            raise RuntimeError("DataProviderPolling no inicializado. Llama a inicializar() primero.")
        
        log.info(f"🔄 Iniciando polling cada {self.intervalo} ({self.intervalo_segundos}s)")
        
        try:
            while True:
                # Resincronizar tiempo si es necesario
                if self.time_sync and self.time_sync.should_resync():
                    await self.time_sync.sync()
                
                # Esperar hasta el próximo cierre de vela
                await self._wait_until_next_candle_close()
                
                # Descargar la última vela cerrada
                try:
                    vela = await self._fetch_latest_closed_candle()
                    
                    if vela:
                        self.velas_descargadas += 1
                        log.info(f"📊 Nueva vela descargada: {vela['timestamp']} - Close: {vela['close']:.2f}")
                        
                        # Actualizar ventana
                        self._actualizar_ventana(vela)
                        
                        # Yield la vela
                        yield vela
                    else:
                        log.warning("No se pudo obtener la última vela, reintentando en el próximo ciclo...")
                        
                except Exception as e:
                    log.error(f"Error al obtener vela: {e}")
                    log.error("Continuando con el siguiente ciclo...")
                    await asyncio.sleep(10)  # Esperar 10s antes de reintentar
                        
        except asyncio.CancelledError:
            log.info("Polling cancelado")
        except Exception as e:
            log.error(f"Error en stream de polling: {e}")
            raise
        finally:
            log.info(f"Polling detenido (total velas descargadas: {self.velas_descargadas})")
    
    async def _wait_until_next_candle_close(self) -> None:
        """
        Espera hasta el cierre de la próxima vela.
        
        Calcula cuándo debería cerrar la próxima vela basándose en el intervalo
        y el tiempo actual (sincronizado con Binance).
        """
        # Obtener tiempo actual de Binance
        now = self.time_sync.get_binance_time() if self.time_sync else datetime.now()
        
        # Calcular el timestamp del próximo cierre de vela
        # Las velas cierran en múltiplos exactos del intervalo
        timestamp_ms = int(now.timestamp() * 1000)
        intervalo_ms = self.intervalo_segundos * 1000
        
        # Próximo cierre = siguiente múltiplo del intervalo
        next_close_ms = ((timestamp_ms // intervalo_ms) + 1) * intervalo_ms
        next_close = datetime.fromtimestamp(next_close_ms / 1000)
        
        # Calcular tiempo de espera
        wait_seconds = (next_close - now).total_seconds()
        
        # Añadir un pequeño buffer (5 segundos) para asegurar que la vela esté cerrada
        wait_seconds += 5
        
        if wait_seconds > 0:
            log.info(f"⏳ Esperando {wait_seconds:.0f}s hasta próximo cierre de vela ({next_close.strftime('%Y-%m-%d %H:%M:%S')})")
            await asyncio.sleep(wait_seconds)
        else:
            log.debug("Vela ya cerrada, procediendo inmediatamente")
    
    async def _fetch_latest_closed_candle(self) -> Optional[Dict[str, Any]]:
        """
        Descarga la última vela cerrada desde Binance.
        
        Returns:
            Diccionario con datos de la vela o None si falla
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Descargar las últimas 2 velas (la última puede estar abierta)
                klines = await self.client.futures_klines(
                    symbol=self.simbolo,
                    interval=self.intervalo,
                    limit=2
                )
                
                if not klines or len(klines) < 2:
                    log.warning(f"No se obtuvieron suficientes velas (intento {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return None
                
                # Tomar la penúltima vela (asegurándonos de que esté cerrada)
                kline = klines[-2]
                
                vela_data = {
                    'timestamp': datetime.fromtimestamp(int(kline[6]) / 1000),  # close_time
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'is_closed': True
                }
                
                # Validar que no es una vela duplicada
                if self.ultima_vela_timestamp and vela_data['timestamp'] <= self.ultima_vela_timestamp:
                    log.debug(f"Vela duplicada detectada, esperando nueva vela...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return None
                
                # Actualizar timestamp de última vela
                self.ultima_vela_timestamp = vela_data['timestamp']
                
                return vela_data
                
            except BinanceAPIException as e:
                log.error(f"Error de API Binance al descargar vela (intento {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial
                    continue
                return None
                
            except Exception as e:
                log.error(f"Error inesperado al descargar vela (intento {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return None
        
        return None
    
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
            
            # Recalcular indicadores
            self.df_ventana = self._calcular_indicadores(self.df_ventana)
            
            # Mantener solo las últimas N filas necesarias
            if len(self.df_ventana) > self.ventana_total:
                self.df_ventana = self.df_ventana.tail(self.ventana_total)
            
            log.debug(f"Ventana actualizada: {len(self.df_ventana)} filas")
            
        except Exception as e:
            log.error(f"Error al actualizar ventana: {e}")
            log.error("Detalles del error:", exc_info=True)
    
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
            log.info("Cerrando DataProviderPolling...")
            
            if self.client:
                await self.client.close_connection()
                log.info("✅ Cliente de Binance cerrado")
            
            self.inicializado = False
            
            log.info(f"✅ DataProviderPolling cerrado (total velas descargadas: {self.velas_descargadas})")
            
        except Exception as e:
            log.error(f"Error al cerrar DataProviderPolling: {e}")
