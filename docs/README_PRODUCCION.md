# Sistema de Trading en Producción - AFML

Sistema de trading automatizado en tiempo real usando Reinforcement Learning (SAC) con Binance Futures.

## 📋 Requisitos Previos

### Dependencias Python

Instalar las dependencias necesarias:

```bash
pip install python-binance pandas pandas-ta scikit-learn stable-baselines3 pydantic pyyaml
```

### Variables de Entorno

Configurar las credenciales de Binance en variables de entorno:

#### Para TESTNET (recomendado para pruebas):
```bash
export BINANCE_TESTNET_API_KEY="tu_api_key_testnet"
export BINANCE_TESTNET_API_SECRET="tu_api_secret_testnet"
```

#### Para PRODUCCIÓN REAL (⚠️ usar con precaución):
```bash
export BINANCE_API_KEY="tu_api_key_real"
export BINANCE_API_SECRET="tu_api_secret_real"
```

**Obtener credenciales de testnet:** https://testnet.binancefuture.com/

## 🚀 Uso

### Modo TESTNET (Recomendado)

```bash
python live.py --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_115513
```

### Modo PRODUCCIÓN REAL (⚠️ Cuidado)

```bash
python live.py --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_115513 --live
```

## 📊 Estructura del Sistema

### Componentes Principales

1. **`live.py`** - Orquestador principal del sistema
2. **`config.py`** - Gestión de configuración desde metadata del entrenamiento
3. **`dataprovider.py`** - Conexión WebSocket y streaming de datos en tiempo real
4. **`observacion.py`** - Constructor de observaciones normalizadas
5. **`agente_produccion.py`** - Agente SAC con predicciones determinísticas
6. **`binance.py`** - Conector con API de Binance Futures
7. **`control_riesgo.py`** - Sistema de validación y protocolo de emergencia
8. **`Registro.py`** - Logging estructurado en CSV

### Flujo de Ejecución

```
1. Inicialización
   ├── Cargar configuración desde train_id
   ├── Cargar modelo SAC entrenado
   ├── Cargar scaler de normalización
   ├── Conectar a Binance (Testnet o Real)
   └── Descargar historial inicial

2. Bucle Principal (por cada nueva vela)
   ├── A. Actualizar estado de cuenta (Binance API)
   ├── B. Verificar max drawdown
   ├── C. Construir observación normalizada
   ├── D. Predicción del agente (determinística)
   ├── E. Validar acción pre-ejecución
   ├── F. Ejecutar operación en mercado
   ├── G. Actualizar estado post-ejecución
   └── H. Registrar paso en CSV

3. Finalización
   ├── Mostrar estadísticas de sesión
   └── Cerrar conexiones
```

## 🛡️ Sistema de Control de Riesgo

### Max Drawdown

El sistema monitorea continuamente el drawdown y activa el **protocolo de emergencia** si se excede el límite configurado en el entrenamiento.

**Protocolo de emergencia:**
1. Cerrar todas las posiciones abiertas inmediatamente
2. Cancelar órdenes pendientes
3. Registrar evento en CSV de emergencias
4. Detener el sistema (no se reinicia automáticamente)

### Reintentos

Si una operación falla (error de API, conexión, etc.):
- Se reintenta hasta 3 veces con delay de 1 segundo
- Si fallan todos los intentos, se activa el protocolo de emergencia
- El sistema intenta cerrar todas las posiciones antes de detenerse

## 📁 Archivos Generados

Todos los archivos se guardan en:
```
entrenamientos/{train_id}/produccion/
├── registro_YYYYMMDD_HHMMSS.csv      # Log completo de operaciones
└── emergencias_YYYYMMDD_HHMMSS.csv   # Log de eventos críticos
```

### Estructura del Registro

Campos registrados por paso:

**ENTORNO:**
- timestamp, paso, action, precio

**PORTAFOLIO:**
- balance, equity, max_drawdown, pnl_total, posicion_abierta
- tipo_posicion_activa, precio_entrada_activa, cantidad_activa, pnl_no_realizado

**OPERACION:**
- tipo_accion, operacion, resultado, error
- trade_id, cantidad, precio_entrada, comision

## ⚙️ Configuración

La configuración se carga automáticamente del archivo `config_metadata.yaml` del entrenamiento especificado.

**Parámetros relevantes:**
- `window_size`: Tamaño de ventana de observación
- `max_drawdown_permitido`: Límite de drawdown (ej: 0.2 = 20%)
- `umbral_mantener_posicion`: Umbral para acciones neutras
- `normalizar_portfolio`: Si normalizar observación de portfolio
- Todos los parámetros de indicadores técnicos

## 🔍 Monitoreo

### Logs en Consola

El sistema genera logs detallados en tiempo real:

```
INFO - 📊 PASO 42 - 2025-10-04T15:30:00
INFO - 🤖 Acción del agente: 0.7234 → abrir_long
INFO - ✅ Operación ejecutada: {'trade_id': 123456, 'cantidad': 0.05}
INFO - 💰 Equity: 10250.50 | Drawdown: 2.5% | Posición: True
```

### Análisis Posterior

Los archivos CSV pueden analizarse con pandas:

```python
import pandas as pd

# Cargar registro
df = pd.read_csv('entrenamientos/{train_id}/produccion/registro_XXXXXXXX_XXXXXX.csv')

# Análisis de rendimiento
df['equity'].plot(title='Evolución del Equity')
df['max_drawdown'].max()  # Drawdown máximo alcanzado
df.groupby('tipo_accion').size()  # Distribución de acciones
```

## ⚠️ Advertencias Importantes

1. **TESTEAR EN TESTNET PRIMERO:** Siempre probar con testnet antes de usar dinero real
2. **VERIFICAR CREDENCIALES:** Asegurarse de usar las credenciales correctas según el modo
3. **MONITOREAR DRAWDOWN:** El sistema se detiene automáticamente si se excede el límite
4. **NO INTERRUMPIR BRUSCAMENTE:** Usar Ctrl+C para detener limpiamente
5. **VERIFICAR MODELO:** Asegurarse de que el `train_id` corresponde a un modelo validado

## 🐛 Troubleshooting

### Error: "Credenciales no encontradas"
- Verificar que las variables de entorno estén configuradas
- Usar `echo $BINANCE_TESTNET_API_KEY` para verificar

### Error: "Scaler no encontrado"
- Verificar que `scaler_train.pkl` existe en el directorio del train_id
- Verificar que el entrenamiento se completó correctamente

### WebSocket desconectado
- El sistema reintentará la conexión automáticamente
- Si falla repetidamente, verificar conexión a internet y estado de Binance API

### Operaciones rechazadas
- Revisar logs para ver la razón del rechazo
- Puede ser por balance insuficiente, límites de margen, o validaciones de riesgo

## 📚 Documentación Adicional

- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)
- [Stable Baselines3 Docs](https://stable-baselines3.readthedocs.io/)
- [python-binance Docs](https://python-binance.readthedocs.io/)

---

**Desarrollado por:** AFML Team  
**Última actualización:** 4 de octubre de 2025
