# 📝 Sistema de Logging Centralizado en Producción

## 🎯 Objetivo
Todos los logs generados durante la ejecución en producción (logger, stdout, stderr, librerías externas) se registran en un único archivo `produccion_{timestamp}.log` dentro de la carpeta de registros de producción.

## 📂 Ubicación de Logs

```
entrenamientos/
└── {train_id}/
    └── produccion/
        ├── produccion_20250105_143022.log  ← TODOS los logs aquí
        ├── registro_20250105_143022.csv
        └── emergencias_20250105_143022.csv
```

## 🔧 Implementación

### 1. Funciones Nuevas en `src/utils/logger.py`

#### `configure_production_logging(base_dir, session_timestamp)`
Función principal que orquesta toda la configuración de logging para producción.

**Parámetros:**
- `base_dir`: Directorio de producción (ej: `entrenamientos/train_XXX/produccion`)
- `session_timestamp`: Timestamp de la sesión (ej: `20250105_143022`)

**Retorna:**
- Ruta completa del archivo de log

**Acciones:**
1. Configura el logger principal AFML
2. Configura loggers de librerías externas
3. Redirige stdout/stderr al archivo

#### `configure_external_loggers(log_file)`
Configura loggers de librerías externas para escribir en el archivo de producción.

**Librerías configuradas:**
- `binance` - Cliente de Binance
- `websockets` - WebSocket para streaming
- `asyncio` - Operaciones asíncronas
- `urllib3` - Requests HTTP
- `requests` - HTTP requests

**Nivel de log:** WARNING (solo warnings y errores para evitar ruido)

### 2. Métodos Nuevos en `src/produccion/Registro.py`

#### `get_session_timestamp()`
Retorna el timestamp de inicio de sesión en formato `YYYYMMDD_HHMMSS`

#### `get_base_dir()`
Retorna el Path del directorio base de producción

### 3. Flujo en `live.py`

```python
# FASE 0: Logging temporal en consola
setup_logger()
log = logging.getLogger("AFML.live")

# FASE 1: Crear directorio de producción
registro = RegistroProduccion(config.train_id)

# FASE 0.5: Reconfigurar logging a archivo
log_file_path = configure_production_logging(
    base_dir=str(registro.get_base_dir()),
    session_timestamp=registro.get_session_timestamp()
)

# Recrear referencia al logger
log = logging.getLogger("AFML.live")

# A partir de aquí, TODOS los logs van solo al archivo
```

## 📊 Contenido del Archivo de Log

El archivo `produccion_{timestamp}.log` contiene:

### 1. Logs del Sistema AFML
```
2025-01-05 14:30:22 - AFML.live - INFO - 🚀 INICIANDO SISTEMA DE TRADING EN PRODUCCIÓN
2025-01-05 14:30:22 - AFML.binance - INFO - ✅ Cuenta inicializada: Balance=1000.00 USDT
2025-01-05 14:30:23 - AFML.dataprovider - INFO - WebSocket conectado
```

### 2. Logs de Librerías Externas (solo warnings/errors)
```
2025-01-05 14:35:10 - websockets - WARNING - Connection lost, reconnecting...
2025-01-05 14:40:05 - binance - ERROR - API rate limit exceeded
```

### 3. Salidas de Consola (stdout/stderr)
```
Binance API response: {'status': 'ok'}
Processing market data...
```

## ✅ Ventajas

1. **Centralización Total**: Un solo archivo con toda la información
2. **Trazabilidad Completa**: Captura absolutamente todo
3. **Organización**: Logs junto a CSVs de registro
4. **Timestamp en Nombre**: Fácil identificación de sesiones
5. **Sin Ruido en Consola**: Terminal limpia
6. **Debugging Facilitado**: Todo en un lugar

## 🔍 Uso

### Ejecutar en Modo Testnet
```bash
python live.py --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_174919
```

### Verificar Logs
```bash
# Logs en tiempo real
tail -f entrenamientos/{train_id}/produccion/produccion_20250105_143022.log

# Buscar errores
grep -i "error" entrenamientos/{train_id}/produccion/produccion_20250105_143022.log

# Ver últimas 100 líneas
tail -n 100 entrenamientos/{train_id}/produccion/produccion_20250105_143022.log
```

## 🛠️ Mantenimiento

### Limpiar Logs Antiguos
```bash
# Eliminar logs de más de 30 días
find entrenamientos/*/produccion/ -name "produccion_*.log" -mtime +30 -delete
```

### Comprimir Logs
```bash
# Comprimir logs antiguos
find entrenamientos/*/produccion/ -name "produccion_*.log" -mtime +7 -exec gzip {} \;
```

## 📝 Notas Técnicas

- El archivo se crea en modo **append** (`'a'`), permitiendo reintentos sin perder logs
- Los loggers externos solo registran WARNING y ERROR para evitar spam
- stdout/stderr se redirigen completamente al archivo
- El formato incluye timestamp, nombre del logger, nivel y mensaje
- Compatible con rotación de logs si se implementa en el futuro

---

**Fecha de implementación:** 5 de octubre de 2025
**Autor:** Sistema de Logging Centralizado v1.0
