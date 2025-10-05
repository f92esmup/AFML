# Mejoras de Timeout y Reintentos Automáticos

## 📋 Resumen de Cambios

Se han implementado mejoras críticas para manejar timeouts y problemas de red en las comunicaciones con la API de Binance.

## 🎯 Problema Resuelto

**Error Original:**
```
HTTPSConnectionPool(host='testnet.binancefuture.com', port=443): Read timed out. (read timeout=10)
```

El sistema fallaba inmediatamente ante problemas de red temporales, activando el protocolo de emergencia innecesariamente.

## ✅ Soluciones Implementadas

### 1. **Timeout Aumentado** (live.py)

```python
cliente_binance = Client(
    api_key=api_key,
    api_secret=api_secret,
    testnet=not args.live,
    requests_params={'timeout': 60}  # Aumentado de 10s a 60s
)
```

**Beneficio:** Mayor tolerancia a latencias de red sin fallar inmediatamente.

---

### 2. **Reintentos Automáticos con Backoff Exponencial** (binance.py)

#### Método: `get_account_info()`
- **Reintentos:** 3 intentos
- **Delays:** 2s → 4s → 8s (backoff exponencial)
- **Excepciones manejadas:** `ReadTimeout`, `ConnectionError`, `Timeout`

```python
max_retries = 3
base_delay = 2  # segundos

for attempt in range(max_retries):
    try:
        account_info = self._client.futures_account()
        # ... resto del código
        return True
    except (ReadTimeout, ConnectionError, Timeout) as e:
        if attempt_num < max_retries:
            delay = base_delay * (2 ** attempt)
            log.warning(f"⚠️ Timeout en API (intento {attempt_num}/{max_retries}). Reintentando en {delay}s...")
            time.sleep(delay)
```

---

#### Método: `create_order()`
- **Reintentos:** 3 intentos
- **Delays:** 1s → 2s → 4s (más rápido, crítico para trading)
- **Excepciones manejadas:** `ReadTimeout`, `ConnectionError`, `Timeout`

```python
max_retries = 3
base_delay = 1  # segundos (más corto para órdenes)
```

---

#### Método: `close_all_positions()` - Operaciones de Emergencia
- **Reintentos en:**
  - Cancelación de órdenes pendientes
  - Obtención de posiciones
  - Cierre de posiciones (usa `create_order()` que ya tiene reintentos)

**Implementación robusta:**
```python
for attempt in range(max_retries):
    try:
        positions = self._client.futures_position_information(symbol=self._config.simbolo)
        break  # Éxito
    except (ReadTimeout, ConnectionError, Timeout) as e:
        # Reintentar con backoff
    except BinanceAPIException as e:
        # No reintentar errores de API
        break
```

---

### 3. **Imports Actualizados**

```python
from requests.exceptions import ReadTimeout, ConnectionError, Timeout
import time
```

Permite capturar específicamente errores de red y aplicar delays entre reintentos.

---

## 🔍 Estrategia de Reintentos

### Backoff Exponencial
```
Intento 1: Inmediato
Intento 2: 2s delay (get_account) / 1s (create_order)
Intento 3: 4s delay / 2s
Intento 4: 8s delay / 4s
```

### Criterios de Reintento

**SÍ reintentar:**
- ✅ `ReadTimeout`: Timeout de lectura
- ✅ `ConnectionError`: Error de conexión
- ✅ `Timeout`: Timeout genérico

**NO reintentar:**
- ❌ `BinanceAPIException`: Errores de API (fondos insuficientes, símbolo inválido, etc.)
- ❌ Excepciones genéricas: Se loguean y retornan error

---

## 📊 Beneficios

### 1. **Resiliencia Mejorada**
- El sistema tolera problemas temporales de red
- No activa emergencia por timeouts recuperables

### 2. **Logs Mejorados**
```
⚠️ Timeout en API de Binance (intento 1/3). Reintentando en 2s... Error: ReadTimeout
⚠️ Timeout al crear orden (intento 2/3). Reintentando en 2s... Error: ConnectionError
```

### 3. **Protocolo de Emergencia Más Preciso**
- Solo se activa ante errores irrecuperables
- Incluso el cierre de emergencia tiene reintentos

### 4. **Mejor Experiencia de Usuario**
- Menos interrupciones innecesarias
- Sistema más robusto en producción

---

## 🧪 Testing Recomendado

### Escenarios a Probar:

1. **Red lenta:** Simular latencia alta
2. **Desconexión temporal:** Pérdida breve de conexión
3. **Testnet caído:** Servidor no responde
4. **Errores de API:** Fondos insuficientes, etc.

### Comandos de Testing:
```bash
# Simular latencia de red
sudo tc qdisc add dev eth0 root netem delay 100ms

# Probar con testnet
python live.py --train-id <train_id> --testnet

# Restaurar red
sudo tc qdisc del dev eth0 root
```

---

## 📝 Notas Importantes

1. **Timeout de 60s:** Puede parecer alto, pero es necesario para redes lentas y testnet inestable
2. **Máximo 3 reintentos:** Balance entre persistencia y rapidez de fallo
3. **Backoff exponencial:** Evita saturar la API con reintentos muy rápidos
4. **Logs detallados:** Cada reintento se registra para debugging

---

## 🔄 Próximos Pasos (Opcional)

1. **Circuit Breaker:** Detener reintentos si la API está completamente caída
2. **Métricas:** Trackear tasa de éxito/fallo de reintentos
3. **Configuración:** Hacer timeout y reintentos configurables
4. **Health Check:** Verificar conectividad antes del bucle principal

---

## ✨ Conclusión

El sistema ahora es **significativamente más robusto** ante problemas de red temporales, manteniendo la seguridad del protocolo de emergencia para errores críticos reales.

**Antes:** Timeout → Emergencia inmediata ❌
**Ahora:** Timeout → 3 reintentos inteligentes → Solo emergencia si falla todo ✅
