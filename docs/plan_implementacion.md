# Plan de Implementación - Sistema de Trading en Producción

## ✅ Estado de Implementación

**Fecha:** 4 de octubre de 2025  
**Estado:** COMPLETADO - Listo para testing

---

## 📋 Resumen del Plan

Sistema de trading automatizado en tiempo real que:
1. Se conecta a Binance Futures vía WebSocket
2. Recibe datos de mercado en tiempo real
3. Calcula indicadores técnicos
4. Genera predicciones con modelo SAC entrenado
5. Ejecuta operaciones automáticamente
6. Monitorea riesgos y activa protocolos de emergencia si es necesario

---

## 🏗️ Arquitectura Implementada

### Componentes Principales

#### 1. **Configuración** ✅
- **`src/produccion/config/config.py`**
  - Carga configuración desde `config_metadata.yaml` del entrenamiento
  - Carga `scaler_train.pkl` para normalización
  - Extrae todos los parámetros necesarios (entorno, portafolio, indicadores)
  - Valida mode (LIVE vs TESTNET)

- **`src/produccion/config/cli.py`** ✅
  - Argumentos: `--train-id` (requerido), `--live` (opcional)

#### 2. **Proveedor de Datos** ✅
- **`src/produccion/dataprovider.py`**
  - Conexión WebSocket asíncrona a Binance Futures
  - Descarga historial inicial (ventana + datos para indicadores)
  - Mantiene ventana rodante de datos
  - Calcula indicadores técnicos (SMA, RSI, MACD, Bollinger Bands)
  - Emite evento cada vez que se completa una vela nueva
  - Manejo de reconexión automática

#### 3. **Constructor de Observaciones** ✅
- **`src/produccion/observacion.py`**
  - Extrae últimas `window_size` barras de la ventana
  - Normaliza datos de mercado con `scaler.transform()`
  - Construye observación de portfolio `[equity, pnl_no_realizado, posicion]`
  - Normaliza portfolio si `normalizar_portfolio == True` (usando valores estáticos)
  - Retorna `{"market": np.array, "portfolio": np.array}`

#### 4. **Agente de Producción** ✅
- **`src/produccion/agente_produccion.py`**
  - Carga modelo SAC desde `modelo.zip`
  - Predicción determinística (`deterministic=True`)
  - Método `interpretar_accion()` idéntico a `entorno.py`:
    - Lógica para LONG/SHORT/MANTENER
    - Abrir, cerrar, aumentar posiciones
    - Basado en umbral de acción

#### 5. **Conector Binance** ✅
- **`src/produccion/binance.py`**
  - Métodos existentes mejorados:
    - `create_order()`: Ejecutar operaciones a mercado
    - `get_account_info()`: Actualizar balance, equity, PnL, posiciones
  - Métodos nuevos:
    - `get_position_info()`: Info completa del portfolio (compatible con `info_builder`)
    - `close_all_positions()`: Cierre de emergencia
    - `calculate_position_size()`: Cálculo de cantidad basado en acción y apalancamiento

#### 6. **Control de Riesgo** ✅
- **`src/produccion/control_riesgo.py`**
  - `verificar_drawdown()`: Monitoreo continuo del drawdown
  - `validar_accion_pre()`: Validaciones antes de ejecutar
  - `activar_protocolo_emergencia()`: Protocolo de cierre de emergencia
    - Cierra todas las posiciones
    - Cancela órdenes pendientes
    - Registra evento
    - Detiene sistema (no reinicia si es por drawdown)
  - `puede_reiniciar()`: Determina si se puede reiniciar tras emergencia

#### 7. **Sistema de Registro** ✅
- **`src/produccion/Registro.py`**
  - Registro en CSV con estructura compatible con `info_builder.py`
  - Archivo principal: `registro_YYYYMMDD_HHMMSS.csv`
  - Archivo de emergencias: `emergencias_YYYYMMDD_HHMMSS.csv`
  - Campos registrados:
    - **Entorno:** timestamp, paso, action, precio, etc.
    - **Portafolio:** balance, equity, drawdown, PnL, posición, etc.
    - **Operación:** tipo, resultado, cantidad, precio, comisión, etc.

#### 8. **Orquestador Principal** ✅
- **`live.py`**
  - Inicialización de todos los componentes
  - Bucle principal asíncrono:
    1. Actualizar estado de cuenta
    2. Verificar drawdown
    3. Construir observación
    4. Predicción del agente
    5. Validar acción
    6. Ejecutar operación (con reintentos)
    7. Actualizar estado final
    8. Registrar paso
  - Manejo de errores y protocolo de emergencia
  - Limpieza y cierre de conexiones

---

## 🔄 Flujo de Ejecución

### Inicialización
```
1. Parsear args (--train-id, --live)
2. Cargar config desde config_metadata.yaml
3. Cargar scaler_train.pkl
4. Crear cliente Binance (testnet/real según flag)
5. Inicializar BinanceConnector
6. Inicializar DataProvider
   ├── Crear cliente asíncrono
   └── Descargar historial inicial (ventana + indicadores)
7. Crear ObservacionBuilder
8. Cargar modelo SAC (AgenteProduccion)
9. Crear ControlRiesgo
10. Crear RegistroProduccion (archivos CSV)
```

### Bucle Principal (cada vela nueva)
```
📊 NUEVA VELA COMPLETA desde WebSocket

A. ACTUALIZAR ESTADO
   └── binance.get_account_info()

B. VERIFICAR RIESGO
   ├── control_riesgo.verificar_drawdown()
   └── Si excede límite → Protocolo emergencia → FIN

C. CONSTRUIR OBSERVACIÓN
   ├── data_provider.get_ventana_normalizada()
   ├── binance.get_position_info()
   └── observacion_builder.construir_observacion()

D. DECISIÓN DEL AGENTE
   ├── agente.predict(obs)
   └── agente.interpretar_accion()

E. VALIDACIÓN PRE-EJECUCIÓN
   ├── control_riesgo.validar_accion_pre()
   └── Si no válida → Registrar rechazo → Siguiente vela

F. EJECUCIÓN
   ├── ejecutar_operacion() con reintentos (3 intentos)
   ├── binance.create_order()
   └── Si falla todos los intentos → Error registrado

G. ACTUALIZAR POST-EJECUCIÓN
   └── binance.get_account_info()

H. REGISTRO
   ├── construir_info_dict()
   └── registro.registrar_paso()

↻ Esperar siguiente vela...
```

### Finalización
```
1. Ctrl+C o error crítico
2. Activar protocolo emergencia (si necesario)
3. Registrar emergencia en CSV
4. Cerrar DataProvider (WebSocket)
5. Mostrar estadísticas de sesión
6. FIN
```

---

## 🛡️ Gestión de Errores

### Niveles de Error

1. **Error leve** (operación rechazada)
   - Log warning
   - Registrar paso con error
   - Continuar con siguiente vela

2. **Error de conexión WebSocket**
   - Reintentar conexión automáticamente
   - Si falla repetidamente → Protocolo emergencia

3. **Error en operación**
   - Reintentar hasta 3 veces (delay 1 segundo)
   - Si fallan todos → Registrar error y continuar
   - Si es error crítico → Protocolo emergencia

4. **Max Drawdown excedido**
   - **PROTOCOLO DE EMERGENCIA INMEDIATO**
   - Cerrar todas las posiciones
   - NO permitir reinicio
   - Sistema detenido permanentemente

### Protocolo de Emergencia

```
🚨 ACTIVACIÓN

1. Cancelar todas las órdenes pendientes
2. Obtener lista de posiciones abiertas
3. Para cada posición:
   └── Crear orden MARKET con reduceOnly=True
4. Actualizar estado final
5. Registrar en emergencias.csv:
   ├── Timestamp
   ├── Razón de emergencia
   ├── Balance final
   ├── Equity final
   ├── Posiciones cerradas
   └── Detalles/errores
6. Si razón == "max drawdown":
   └── NO permitir reinicio automático
7. Si razón == "error operacional":
   └── Permitir reinicio manual

FIN DEL SISTEMA
```

---

## 📊 Datos Registrados

### Archivo: `registro_YYYYMMDD_HHMMSS.csv`

Campos por paso:

**ENTORNO:**
- timestamp, paso, episodio, action, precio, recompensa, terminated, truncated, status

**PORTAFOLIO:**
- balance, equity, max_drawdown, operaciones_total, pnl_total
- posicion_abierta, trade_id_activo, tipo_posicion_activa
- precio_entrada_activa, cantidad_activa, velas_activa, pnl_no_realizado

**OPERACION:**
- tipo_accion, operacion, resultado, error
- trade_id, tipo_posicion, precio_entrada, precio_salida
- cantidad, cantidad_adicional, cantidad_total, cantidad_restante, cantidad_reducida
- porcentaje_inversion, comision, slippage
- margen, margen_liberado, pnl_realizado, pnl_parcial, velas_abiertas

### Archivo: `emergencias_YYYYMMDD_HHMMSS.csv`

Campos:
- timestamp, razon, balance_final, equity_final, posiciones_cerradas, detalles

---

## 🧪 Testing

### Fase 1: Validación Unitaria
- [ ] Test de carga de configuración
- [ ] Test de construcción de observaciones
- [ ] Test de normalización
- [ ] Test de interpretación de acciones
- [ ] Test de cálculo de tamaño de posición

### Fase 2: Testing en TESTNET
- [ ] Ejecutar en testnet con capital ficticio
- [ ] Validar conexión WebSocket
- [ ] Validar recepción de velas
- [ ] Validar cálculo de indicadores
- [ ] Validar ejecución de órdenes
- [ ] Validar registro en CSV
- [ ] Provocar max drawdown y verificar protocolo emergencia
- [ ] Verificar reintentos tras errores

### Fase 3: Dry Run (TESTNET con modelo real)
- [ ] Ejecutar 24-48 horas en testnet
- [ ] Analizar rendimiento del modelo
- [ ] Verificar drawdown máximo alcanzado
- [ ] Analizar distribución de acciones
- [ ] Verificar que no hay memory leaks
- [ ] Verificar estabilidad del WebSocket

### Fase 4: Producción Controlada (si se decide)
- [ ] Iniciar con capital mínimo
- [ ] Monitoreo continuo manual
- [ ] Límites de drawdown muy conservadores
- [ ] Revisión diaria de logs y CSV

---

## 📝 Checklist de Deployment

Antes de ejecutar en TESTNET:
- [ ] Variables de entorno configuradas (`BINANCE_TESTNET_API_KEY`, etc.)
- [ ] Verificar que `train_id` existe y tiene todos los archivos necesarios
- [ ] Verificar que `scaler_train.pkl` existe
- [ ] Verificar que `modelo.zip` existe
- [ ] Configurar logging adecuado
- [ ] Tener permisos de escritura en directorio de entrenamientos

Antes de ejecutar en PRODUCCIÓN REAL:
- [ ] ⚠️ **DETENER Y RECONSIDERAR**
- [ ] Haber completado todas las fases de testing
- [ ] Validar rendimiento en testnet por al menos 1 semana
- [ ] Configurar alertas de monitoreo
- [ ] Definir límites de drawdown muy conservadores
- [ ] Tener plan de contingencia
- [ ] Iniciar con capital mínimo
- [ ] Monitoreo 24/7 (al menos inicial)

---

## 🚀 Comando de Ejecución

### TESTNET (Recomendado)
```bash
# 1. Configurar variables de entorno
source .env.sh

# 2. Ejecutar
python live.py --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_115513
```

### PRODUCCIÓN REAL (⚠️ Extrema precaución)
```bash
# 1. Configurar variables de entorno
source .env.sh

# 2. Ejecutar
python live.py --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_115513 --live
```

---

## 📚 Archivos Creados/Modificados

### Creados
- `src/produccion/dataprovider.py` ✅
- `src/produccion/observacion.py` ✅
- `src/produccion/agente_produccion.py` ✅
- `src/produccion/control_riesgo.py` ✅
- `src/produccion/Registro.py` ✅
- `docs/README_PRODUCCION.md` ✅
- `.env.example.sh` ✅
- `docs/plan_implementacion.md` ✅ (este archivo)

### Modificados
- `src/produccion/config/config.py` ✅
- `src/produccion/binance.py` ✅
- `live.py` ✅

---

## ✅ Próximos Pasos

1. **Revisar código** - Verificar que todo esté correcto
2. **Testing unitario** - Crear tests para componentes críticos
3. **Ejecutar en TESTNET** - Primera ejecución real
4. **Debugging** - Corregir errores encontrados
5. **Optimización** - Mejorar rendimiento si es necesario
6. **Documentación** - Completar docs con ejemplos reales
7. **Monitoreo** - Añadir alertas y dashboards
8. **Producción** - Solo después de validación exhaustiva

---

**Implementación completada el:** 4 de octubre de 2025  
**Estado:** Listo para testing en TESTNET
