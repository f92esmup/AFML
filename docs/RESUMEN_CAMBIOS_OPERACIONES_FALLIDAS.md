# Resumen de Cambios - Gestión Correcta de Operaciones Fallidas

## Problema Identificado

En el sistema de trading en producción, cuando una operación fallaba (ej. por margen insuficiente con error `-2019`), el sistema:

1. ❌ Registraba la operación como **exitosa** (`resultado: True`) aunque falló
2. ❌ Mostraba log "✅ Operación ejecutada" sin verificar si realmente funcionó
3. ❌ No diferenciaba entre errores recuperables (reintentar) y no-recuperables (fallar inmediatamente)
4. ❌ Hacía 3 reintentos innecesarios para errores que nunca se resolverían

## Cambios Implementados

### 1. **`src/produccion/binance.py` - Separación de Errores**

**Antes:**
- Todos los `BinanceAPIException` se manejaban igual
- Siempre retornaba `None` sin distinguir el tipo de error

**Después:**
```python
ERRORES_NO_RECUPERABLES = {
    -2019,  # Margen insuficiente
    -1100,  # Parámetros inválidos
    -2015,  # Permisos insuficientes
    -1111,  # Precisión inválida
    -2021,  # Orden inmediatamente ejecutable
}

# Si es error no-recuperable → Retornar None INMEDIATAMENTE (sin reintentos)
# Si es error recuperable → Reintentar hasta 3 veces
```

**Beneficios:**
- ✅ No pierde tiempo reintentando errores irrecuperables
- ✅ Distingue entre problemas de red (temporales) y problemas lógicos (permanentes)
- ✅ Logging más claro indicando si el error es recuperable o no

---

### 2. **`live.py` - Función `ejecutar_operacion` con Verificación de Estado**

**Antes:**
```python
order = binance.create_order(...)
# Si order es None, igual retornaba resultado: True ❌
return {'resultado': True, 'trade_id': order.get('orderId') if order else None}
```

**Después:**
```python
# 1. Capturar estado ANTES
estado_previo = binance.get_position_info()

# 2. Ejecutar operación
order = binance.create_order(...)

# 3. VERIFICAR si order es None
if order is None:
    return {
        'resultado': False,  # ✅ Correcto
        'error': 'create_order retornó None - Operación no ejecutada',
        ...
    }

# 4. Actualizar estado DESPUÉS
binance.get_account_info()
estado_posterior = binance.get_position_info()

# 5. VERIFICAR cambio real en la posición
cambio_detectado = (estado_posterior['cantidad_activa'] > estado_previo['cantidad_activa'])

# 6. Advertir si hay inconsistencia
if not cambio_detectado and order.get('orderId'):
    log.warning("Orden reportada exitosa pero no se detectó cambio en posición")

return {'resultado': True, 'cambio_verificado': cambio_detectado, ...}
```

**Beneficios:**
- ✅ Detecta cuando `create_order` retorna `None` y marca como fallo
- ✅ Verifica el estado REAL de Binance antes/después
- ✅ Detecta inconsistencias entre lo que dice la API y el estado real
- ✅ Elimina el loop de reintentos redundante (ya está en `create_order`)

---

### 3. **`live.py` - Bucle Principal con Logging Diferenciado**

**Antes:**
```python
resultado = ejecutar_operacion(...)
log.info(f"✅ Operación ejecutada: {resultado}")  # Siempre ✅ ❌
```

**Después:**
```python
resultado = ejecutar_operacion(...)

# Logging diferenciado según resultado real
if resultado['resultado']:
    log.info(f"✅ Operación EXITOSA: {resultado['operacion']} | "
            f"Trade ID: {resultado.get('trade_id')} | "
            f"Cantidad: {resultado.get('cantidad'):.3f}")
else:
    log.warning(f"❌ Operación FALLÓ: {resultado['operacion']} | "
              f"Error: {resultado.get('error')}")
```

**Beneficios:**
- ✅ El usuario ve claramente si la operación funcionó o no
- ✅ Los logs reflejan la realidad del sistema
- ✅ Facilita debugging y análisis post-mortem

---

### 4. **Actualización de Estado Post-Ejecución**

**Mantuvimos:**
```python
# SIEMPRE actualizar estado (incluso si operación falló)
binance.get_account_info()
binance_state_final = binance.get_position_info()
```

**Razón:**
- Necesitamos el estado REAL de Binance para el siguiente paso
- Permite detectar cambios inesperados
- Asegura que métricas (equity, drawdown) estén actualizadas

---

### 5. **Registro de Operaciones Fallidas**

El sistema de registro (`Registro.py`) ya soportaba el campo `'error'`, por lo que:

✅ Operaciones fallidas se registran con:
- `resultado = False`
- `error = "mensaje descriptivo"`
- `trade_id = None`

Esto permite:
- Análisis posterior de por qué fallaron operaciones
- Métricas de tasa de éxito/fallo
- Debugging de problemas recurrentes

---

## Casos de Uso Cubiertos

### ✅ Caso 1: Margen Insuficiente
**Comportamiento:**
1. Agente decide `aumentar_long`
2. `create_order` retorna `None` (error -2019, sin reintentos)
3. `ejecutar_operacion` retorna `resultado: False`
4. Log: `❌ Operación FALLÓ: aumentar_long | Error: create_order retornó None`
5. Sistema continúa normalmente (opción B)

### ✅ Caso 2: Error de Red Temporal
**Comportamiento:**
1. Agente decide `abrir_long`
2. `create_order` detecta timeout
3. Reintenta 3 veces con backoff exponencial
4. Si tiene éxito → `resultado: True`
5. Si falla tras 3 intentos → `resultado: False`

### ✅ Caso 3: Acción Rechazada por Control de Riesgo
**Comportamiento:**
1. Agente decide una acción
2. Control de riesgo la rechaza en validación pre-ejecución
3. `resultado = {'tipo_accion': 'rechazada', 'resultado': False, 'error': <razón>}`
4. Log: `⚠️ Acción rechazada por control de riesgo: <razón>`

### ✅ Caso 4: Mantener Posición (No hacer nada)
**Comportamiento:**
1. Agente decide `debe_ejecutar: False`
2. `resultado = {'tipo_accion': 'mantener', 'operacion': 'mantener', 'resultado': True}`
3. No se ejecuta ninguna operación (correcto)

---

## Verificación Realizada

Se creó script `verificar_errores.py` que valida:

✅ Error -2019 (margen insuficiente) → 1 intento, no reintenta  
✅ Error -1100 (parámetros inválidos) → 1 intento, no reintenta  
✅ Error -2015 (permisos insuficientes) → 1 intento, no reintenta  
✅ Error -1001 (servidor, recuperable) → 3 intentos con reintentos  
✅ Error genérico recuperable → 3 intentos con reintentos  

---

## Archivos Modificados

1. ✅ `src/produccion/binance.py` (líneas 101-180)
2. ✅ `live.py` (líneas 260-310, 366-480)
3. ✅ `tests/produccion/test_operaciones_fallidas.py` (nuevo)
4. ✅ `verificar_errores.py` (script de verificación)

---

## Logs Esperados Ahora

### Operación Exitosa:
```
2025-10-05 13:24:04 - AFML.Binance - INFO - Orden creada exitosamente: 5689038733
2025-10-05 13:24:06 - AFML.live - INFO - ✅ Operación EXITOSA: abrir_long | Trade ID: 5689038733 | Cantidad: 0.360
```

### Operación Fallida:
```
2025-10-05 13:25:04 - AFML.Binance - ERROR - ❌ Error NO recuperable al crear orden (código -2019): Margin is insufficient.
2025-10-05 13:25:04 - AFML.live - WARNING - ❌ Operación FALLÓ: aumentar_long | Error: create_order retornó None - Operación no ejecutada en Binance
```

---

## Próximos Pasos Recomendados

1. **Testing en Testnet:** Ejecutar `live.py` y provocar deliberadamente errores para verificar logs
2. **Monitoreo de Métricas:** Analizar CSV de registro para ver tasa de operaciones fallidas
3. **Ajuste de Parámetros:** Si hay muchos fallos por margen insuficiente, reducir tamaño de posiciones
4. **Alertas:** Considerar añadir alerta si tasa de fallos supera umbral (ej. >20%)

---

## Conclusión

✅ El sistema ahora diferencia correctamente entre operaciones exitosas y fallidas  
✅ No reintentar errores no-recuperables ahorra tiempo y recursos  
✅ Verificación de estado real previene inconsistencias  
✅ Logs claros facilitan debugging y análisis  
✅ Sistema sigue la filosofía del entrenamiento (opción B): fallos se registran pero no detienen el sistema
