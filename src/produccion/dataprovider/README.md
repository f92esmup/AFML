# DataProvider Module

Módulo de proveedores de datos para trading en producción con selección automática entre WebSocket y Polling.

## 🎯 Funcionalidad

Este módulo selecciona automáticamente el método óptimo para obtener datos de mercado según el timeframe configurado:

- **WebSocket** (< 15 minutos): Tiempo real, baja latencia, ideal para alta frecuencia
- **Polling** (>= 15 minutos): Más robusto, menos propenso a fallos, ideal para baja frecuencia

## 📐 Arquitectura

```
dataprovider/
├── __init__.py          # Exports públicos
├── base.py              # Clase abstracta DataProviderBase
├── websocket.py         # Implementación WebSocket
├── polling.py           # Implementación Polling
├── factory.py           # Factory para selección automática
└── timesync.py          # Sincronización con servidor Binance
```

## 🚀 Uso

### Uso Básico (Recomendado)

```python
from src.produccion.dataprovider import DataProviderFactory

# El factory selecciona automáticamente el proveedor adecuado
provider = DataProviderFactory.create(config, scaler)
await provider.inicializar(api_key, api_secret, testnet=True)

# Usar el stream de velas (funciona igual para ambos providers)
async for vela in provider.stream_velas():
    # Procesar vela...
    ventana = provider.get_ventana_normalizada()
    # ...
```

### Uso Manual (para testing)

```python
from src.produccion.dataprovider.websocket import DataProviderWebSocket
from src.produccion.dataprovider.polling import DataProviderPolling

# Forzar uso de WebSocket
provider = DataProviderWebSocket(config, scaler)

# O forzar uso de Polling
provider = DataProviderPolling(config, scaler)
```

## ⚙️ Configuración

No requiere configuración adicional. Lee el `intervalo` del `ProductionConfig`:

```yaml
# config_metadata.yaml
data_downloader:
  interval: "1h"  # Automáticamente usa Polling
  # interval: "5m"  # Automáticamente usa WebSocket
```

## 🔄 Selección Automática

| Intervalo | Duración | Provider | Razón |
|-----------|----------|----------|-------|
| 1m | 60s | WebSocket | Alta frecuencia |
| 5m | 300s | WebSocket | Alta frecuencia |
| 15m | 900s | Polling | Umbral exacto |
| 30m | 1800s | Polling | Baja frecuencia |
| 1h | 3600s | Polling | Baja frecuencia |
| 4h | 14400s | Polling | Baja frecuencia |

**Umbral de decisión:** 900 segundos (15 minutos)

## 🔍 Inspección

Para ver qué proveedor se usaría sin crear la instancia:

```python
from src.produccion.dataprovider import DataProviderFactory

# Ver info para un intervalo específico
info = DataProviderFactory.get_provider_info('1h')
print(info)
# {
#     'intervalo': '1h',
#     'segundos': 3600,
#     'provider': 'Polling',
#     'razon': 'Baja frecuencia (3600s >= 900s)'
# }

# Listar todos los intervalos soportados
intervals = DataProviderFactory.list_intervals()
print(intervals)
# {'1m': 'WebSocket', '5m': 'WebSocket', '15m': 'Polling', ...}
```

## 🕐 Sincronización de Tiempo

Ambos providers incluyen sincronización automática con el servidor de Binance:

- **Sincronización inicial:** Al inicializar
- **Resincronización automática:** Cada 1 hora
- **Compensación de latencia:** Calculada automáticamente
- **Logging detallado:** Offset y latencia en cada sync

```
⏱️  Tiempo sincronizado con Binance
   Offset: +127ms | Latencia: 45.3ms
```

## 🧪 Testing

```python
# Test manual de providers
import asyncio
from src.produccion.config.config import ProductionConfig
from src.produccion.dataprovider import DataProviderFactory

async def test():
    config = ProductionConfig.load_config(args)
    provider = DataProviderFactory.create(config, scaler)
    
    await provider.inicializar(api_key, api_secret, testnet=True)
    
    # Recibir solo 3 velas para testing
    count = 0
    async for vela in provider.stream_velas():
        print(f"Vela {count}: {vela['timestamp']} - Close: {vela['close']}")
        count += 1
        if count >= 3:
            break
    
    await provider.cerrar()

asyncio.run(test())
```

## 📊 Ventajas por Provider

### WebSocket
✅ Latencia ultra-baja (< 100ms)  
✅ Datos en tiempo real  
✅ Eficiente para alta frecuencia  
⚠️ Puede desconectarse  
⚠️ Requiere reconexión  

### Polling
✅ Muy robusto  
✅ No se desconecta  
✅ Más predecible  
✅ Menos recursos de red  
⚠️ Latencia de 5-10 segundos  
⚠️ No apto para < 15min  

## 🔧 Troubleshooting

### "DataProvider no inicializado"
```python
# Asegúrate de llamar inicializar() antes de stream_velas()
await provider.inicializar(api_key, api_secret, testnet=True)
```

### Velas duplicadas en Polling
- El provider detecta automáticamente y espera la siguiente
- Si persiste, verifica sincronización de tiempo del sistema

### WebSocket se desconecta
- Normal para intervalos largos (>= 1h)
- Considera usar Polling en su lugar
- O forzar manualmente: `provider = DataProviderPolling(...)`

## 📝 Migración desde DataProvider antiguo

**Antes:**
```python
from src.produccion.dataprovider import DataProvider
provider = DataProvider(config, scaler)
```

**Después:**
```python
from src.produccion.dataprovider import DataProviderFactory
provider = DataProviderFactory.create(config, scaler)
```

**El resto del código NO cambia** - ambos implementan la misma interfaz.

## 🔗 Referencias

- `base.py`: Interfaz común (DataProviderBase)
- `websocket.py`: Implementación WebSocket
- `polling.py`: Implementación Polling  
- `factory.py`: Lógica de selección
- `timesync.py`: Sincronización temporal
