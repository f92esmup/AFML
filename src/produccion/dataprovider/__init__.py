"""
Módulo de proveedores de datos para trading en producción.

Selecciona automáticamente entre WebSocket y Polling según el intervalo configurado:
- Intervalos < 15min: WebSocket (tiempo real, alta frecuencia)
- Intervalos >= 15min: Polling (más robusto, baja frecuencia)

Uso:
    from src.produccion.dataprovider import DataProviderFactory
    
    provider = DataProviderFactory.create(config, scaler)
    await provider.inicializar(api_key, api_secret, testnet=True)
    
    async for vela in provider.stream_velas():
        # Procesar vela...
"""

from .factory import DataProviderFactory
from .base import DataProviderBase

__all__ = ['DataProviderFactory', 'DataProviderBase']
