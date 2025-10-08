"""Sincronización de tiempo con servidor de Binance.

Compensa el drift entre el reloj local y el servidor de Binance
para garantizar que las operaciones se ejecuten en el momento correcto.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from binance import AsyncClient

log = logging.getLogger("AFML.TimeSync")


class BinanceTimeSync:
    """
    Sincronizador de tiempo con servidor de Binance.
    
    Consulta periódicamente el servidor de Binance para calcular el offset
    entre el reloj local y el servidor, compensando drift temporal.
    """
    
    def __init__(self, client: AsyncClient, sync_interval_hours: int = 1) -> None:
        """
        Inicializa el sincronizador.
        
        Args:
            client: Cliente asíncrono de Binance
            sync_interval_hours: Horas entre resincronizaciones automáticas
        """
        self.client = client
        self.offset_ms: int = 0  # Diferencia entre tiempo local y Binance (ms)
        self.last_sync: Optional[datetime] = None
        self.sync_interval = timedelta(hours=sync_interval_hours)
        self.latencia_ms: float = 0.0  # Última latencia medida
    
    async def sync(self) -> int:
        """
        Sincroniza el reloj con el servidor de Binance.
        
        Mide la latencia de red y calcula el offset entre el reloj local
        y el servidor de Binance.
        
        Returns:
            Offset en milisegundos (positivo si Binance va adelantado)
        """
        try:
            # Timestamp local antes de la petición
            local_time_before = datetime.now()
            
            # Obtener tiempo del servidor
            server_time = await self.client.get_server_time()
            
            # Timestamp local después de la petición
            local_time_after = datetime.now()
            
            # Estimar latencia (tiempo de ida y vuelta / 2)
            latency_total_ms = (local_time_after - local_time_before).total_seconds() * 1000
            self.latencia_ms = latency_total_ms / 2
            
            # Calcular offset considerando latencia
            server_timestamp_ms = server_time['serverTime']
            local_timestamp_ms = int(local_time_before.timestamp() * 1000) + int(self.latencia_ms)
            self.offset_ms = server_timestamp_ms - local_timestamp_ms
            
            self.last_sync = datetime.now()
            
            log.info(f"⏱️  Tiempo sincronizado con Binance")
            log.info(f"   Offset: {self.offset_ms:+d}ms | Latencia: {self.latencia_ms:.1f}ms")
            
            # Advertir si el offset es muy grande
            if abs(self.offset_ms) > 1000:  # > 1 segundo
                log.warning(f"⚠️  Offset temporal grande: {self.offset_ms}ms")
                log.warning(f"   Considera sincronizar el reloj del sistema")
            
            return self.offset_ms
            
        except Exception as e:
            log.error(f"❌ Error al sincronizar tiempo con Binance: {e}")
            # Mantener offset anterior si falla
            return self.offset_ms
    
    def should_resync(self) -> bool:
        """
        Verifica si es necesario resincronizar.
        
        Returns:
            True si necesita sincronizar, False en caso contrario
        """
        if self.last_sync is None:
            return True
        
        time_since_sync = datetime.now() - self.last_sync
        return time_since_sync >= self.sync_interval
    
    def get_binance_time(self) -> datetime:
        """
        Obtiene la hora actual ajustada al servidor de Binance.
        
        Returns:
            Datetime ajustado con el offset calculado
        """
        local_ms = int(datetime.now().timestamp() * 1000)
        binance_ms = local_ms + self.offset_ms
        return datetime.fromtimestamp(binance_ms / 1000)
    
    def get_offset_seconds(self) -> float:
        """
        Obtiene el offset en segundos (para facilitar cálculos).
        
        Returns:
            Offset en segundos
        """
        return self.offset_ms / 1000.0
    
    def get_stats(self) -> dict:
        """
        Obtiene estadísticas de sincronización.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            'offset_ms': self.offset_ms,
            'offset_seconds': self.get_offset_seconds(),
            'latencia_ms': self.latencia_ms,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'next_sync': (self.last_sync + self.sync_interval).isoformat() if self.last_sync else None,
        }
