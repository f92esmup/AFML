"""Factory para crear el proveedor de datos adecuado.

Selecciona automáticamente entre WebSocket y Polling según
el intervalo configurado.
"""

import logging
from typing import Dict, Any
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig
from .base import DataProviderBase
from .websocket import DataProviderWebSocket
from .polling import DataProviderPolling

log = logging.getLogger("AFML.DataProviderFactory")


class DataProviderFactory:
    """
    Factory para crear el proveedor de datos adecuado según el intervalo.
    
    Criterio de selección:
    - Intervalos < 15min: WebSocket (alta frecuencia, tiempo real)
    - Intervalos >= 15min: Polling (baja frecuencia, más robusto)
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
    
    # Umbral para decidir entre WebSocket y Polling
    THRESHOLD_SECONDS = 900  # 15 minutos
    
    @classmethod
    def create(cls, config: ProductionConfig, scaler: StandardScaler) -> DataProviderBase:
        """
        Crea el proveedor de datos adecuado según el intervalo.
        
        Args:
            config: ProductionConfig con intervalo definido
            scaler: StandardScaler para normalización
            
        Returns:
            Instancia de DataProviderWebSocket o DataProviderPolling
            
        Example:
            >>> config = ProductionConfig.load_config(args)
            >>> provider = DataProviderFactory.create(config, scaler)
            >>> await provider.inicializar(api_key, api_secret, testnet=True)
        """
        intervalo = config.intervalo
        
        # Obtener duración en segundos
        segundos = cls.INTERVAL_TO_SECONDS.get(intervalo)
        
        if segundos is None:
            # Intervalo no reconocido, usar WebSocket por defecto
            log.warning(f"⚠️  Intervalo '{intervalo}' no reconocido en mapeo estándar")
            log.warning(f"   Usando WebSocket por defecto")
            provider_class = DataProviderWebSocket
            metodo = "WebSocket"
            razon = "intervalo desconocido (default)"
        elif segundos < cls.THRESHOLD_SECONDS:
            # Alta frecuencia: usar WebSocket
            provider_class = DataProviderWebSocket
            metodo = "WebSocket"
            razon = f"alta frecuencia ({segundos}s < {cls.THRESHOLD_SECONDS}s)"
        else:
            # Baja frecuencia: usar Polling
            provider_class = DataProviderPolling
            metodo = "Polling"
            razon = f"baja frecuencia ({segundos}s >= {cls.THRESHOLD_SECONDS}s)"
        
        # Log de selección
        log.info("=" * 70)
        log.info("📡 SELECCIÓN AUTOMÁTICA DE PROVEEDOR DE DATOS")
        log.info("=" * 70)
        log.info(f"   Intervalo configurado: {intervalo}")
        if segundos:
            log.info(f"   Duración: {segundos} segundos ({segundos/60:.1f} minutos)")
        log.info(f"   Umbral de decisión: {cls.THRESHOLD_SECONDS}s (15 minutos)")
        log.info(f"   ✅ Proveedor seleccionado: {metodo}")
        log.info(f"   Razón: {razon}")
        log.info("=" * 70)
        
        return provider_class(config, scaler)
    
    @classmethod
    def get_provider_info(cls, intervalo: str) -> Dict[str, Any]:
        """
        Obtiene información sobre qué proveedor se usaría para un intervalo dado.
        
        Útil para testing y debugging sin crear el proveedor.
        
        Args:
            intervalo: Intervalo de tiempo (ej: '1h', '15m')
            
        Returns:
            Diccionario con información del proveedor:
            {
                'intervalo': str,
                'segundos': int or None,
                'provider': str,  # 'WebSocket' o 'Polling'
                'razon': str
            }
        """
        segundos = cls.INTERVAL_TO_SECONDS.get(intervalo)
        
        if segundos is None:
            return {
                'intervalo': intervalo,
                'segundos': None,
                'provider': 'WebSocket',
                'razon': 'Intervalo desconocido (default WebSocket)'
            }
        elif segundos < cls.THRESHOLD_SECONDS:
            return {
                'intervalo': intervalo,
                'segundos': segundos,
                'provider': 'WebSocket',
                'razon': f'Alta frecuencia ({segundos}s < {cls.THRESHOLD_SECONDS}s)'
            }
        else:
            return {
                'intervalo': intervalo,
                'segundos': segundos,
                'provider': 'Polling',
                'razon': f'Baja frecuencia ({segundos}s >= {cls.THRESHOLD_SECONDS}s)'
            }
    
    @classmethod
    def list_intervals(cls) -> Dict[str, str]:
        """
        Lista todos los intervalos soportados y su proveedor asignado.
        
        Returns:
            Diccionario {intervalo: provider_type}
        """
        result = {}
        for intervalo, segundos in cls.INTERVAL_TO_SECONDS.items():
            provider = 'WebSocket' if segundos < cls.THRESHOLD_SECONDS else 'Polling'
            result[intervalo] = provider
        return result
