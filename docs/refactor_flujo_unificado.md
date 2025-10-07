# Refactorización: Flujo Unificado de Entrenamiento

**Fecha:** 4 de Octubre de 2025  
**Branch:** `refactor/unified-training-flow`  
**Estado:** ✅ Completado

## 📋 Resumen Ejecutivo

Se ha completado una refactorización mayor del sistema de entrenamiento para eliminar la separación entre descarga de datos (`create_dataset.py`) y entrenamiento (`train.py`). Ahora existe un **único flujo unificado** que implementa un paso completo de walk-forward:

```
Descarga datos train → Entrena → Descarga datos eval → Evalúa → Guarda metadata
```

## 🎯 Objetivos Cumplidos

✅ Eliminar concepto de `data_id` (datasets pre-generados)  
✅ Integrar descarga de datos directamente en `train.py`  
✅ Usar solo `train_id` para identificar experimentos  
✅ Guardar scalers en directorio de entrenamiento (no en datasets/)  
✅ Guardar toda la configuración `UnifiedConfig` en metadata  
✅ Implementar gestión explícita de memoria entre fases  
✅ Usar scaler de train en evaluación (consistencia con producción)  

## 📁 Archivos Modificados/Eliminados

### Eliminados
- ❌ `create_dataset.py` - Funcionalidad integrada en train.py
- ❌ `src/train/AdquisicionDatos/pipeline.py` - Ya no necesario
- ❌ `DatasetConfig` class - Concepto de dataset eliminado

### Modificados
- ✏️ `train.py` - Refactorización completa (270 líneas modificadas)
- ✏️ `src/train/config/cli.py` - Nuevos argumentos CLI
- ✏️ `src/train/config/config.py` - Nuevas clases y métodos
- ✏️ `src/train/AdquisicionDatos/__init__.py` - Exports actualizados
- ✏️ `README.md` - Documentación actualizada

## 🔄 Cambios en CLI

### Antes (obsoleto)
```bash
# 1. Crear dataset
python create_dataset.py \
  --symbol BTCUSDT \
  --interval 1h \
  --start-date 2024-01-01 \
  --end-date 2024-06-30

# 2. Entrenar con dataset
python train.py \
  --data-id BTCUSDT_20241004_123456 \
  --data-eval-id BTCUSDT_20241004_234567 \
  --episodios 5
```

### Ahora (nuevo flujo)
```bash
python train.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-06-30 \
  --eval-start-date 2024-07-01 \
  --eval-end-date 2024-09-30 \
  --total-timesteps 50000 \
  --episodios-eval 3
```

**Argumentos eliminados:**
- `--data-id`
- `--data-eval-id`
- `--episodios` (reemplazado por `--total-timesteps`)

**Argumentos nuevos:**
- `--symbol` (requerido)
- `--interval` (requerido)
- `--train-start-date` (requerido)
- `--train-end-date` (requerido)
- `--eval-start-date` (requerido)
- `--eval-end-date` (requerido)
- `--total-timesteps` (opcional, default: 10000) - Especifica directamente los pasos de entrenamiento

## 🏗️ Cambios en Estructura de Directorios

### Antes
```
datasets/
  BTCUSDT_20241003_235804/
    data.csv          ← guardado en disco
    metadata.yaml
    scaler.pkl

entrenamientos/
  train_BTCUSDT_20241003_235804_lr3e-4_bs256_ws30_20241004_000314/
    config_metadata.yaml
    modelos/modelo.zip
    evaluacion/...
    tensorboard/...
```

### Ahora
```
entrenamientos/
  train_BTCUSDT_20240101_20240630_lr3e-4_bs256_ws30_20241004_143022/
    config_metadata.yaml       ← TODO UnifiedConfig + metadata ejecución
    scaler_train.pkl           ← Scaler de entrenamiento
    scaler_eval.pkl            ← Scaler de evaluación (opcional)
    modelos/modelo.zip
    evaluacion/...
    tensorboard/...
```

**Cambios clave:**
- ❌ Carpeta `datasets/` ya no se usa
- ✅ Scalers guardados en carpeta de entrenamiento
- ✅ Nuevo formato de `train_id` incluye fechas: `train_{symbol}_{start}_{end}_...`
- ✅ Metadata completa (toda la configuración) en un solo archivo

## 🔧 Cambios en config.py

### Clases Eliminadas
```python
class OutputDataAcquisitionConfig  # Ya no necesaria
class OutputTrainingConfig         # Ya no necesaria  
class DatasetConfig                # Concepto eliminado
```

### Clases Nuevas/Modificadas
```python
class OutputConfig(BaseModel):
    """Configuración de salida unificada."""
    base_dir: str
    model_path: str
    tensorboard_log: str
    scaler_train_path: str        # NUEVO
    scaler_eval_path: str          # NUEVO
    metadata_filename: str

class DataDownloaderConfig(BaseModel):
    # Campos ahora son REQUERIDOS (no Optional)
    symbol: str                    # antes: Optional[str]
    interval: str                  # antes: Optional[str]
    start_date: str                # antes: Optional[str]
    end_date: str                  # antes: Optional[str]
```

### Métodos Eliminados
```python
UnifiedConfig.load_for_data_acquisition()  # Ya no usado
UnifiedConfig._add_dataset_info()          # Ya no necesario
UnifiedConfig._data_id()                   # Concepto eliminado
UnifiedConfig._train_id()                  # Reemplazado
```

### Métodos Nuevos
```python
UnifiedConfig.load_for_unified_training(args)      # Carga config para flujo unificado
UnifiedConfig._add_cli_args_unified(args, yaml)    # Integra args CLI
UnifiedConfig._generate_train_id(...)             # Nuevo formato de train_id
UnifiedConfig._add_output_paths_unified(...)      # Configura rutas de salida
```

## 🔄 Cambios en train.py

### Clase `Entrenamiento` - Nuevos Métodos

```python
def _descargar_y_preprocesar(start_date, end_date) -> Tuple[pd.DataFrame, StandardScaler]:
    """Descarga y preprocesa datos para un rango de fechas."""
    # 1. Actualizar config con fechas
    # 2. Descargar datos (DataDownloader)
    # 3. Preprocesar (Preprocesamiento)
    # 4. Retornar (data, scaler)

def _guardar_scaler(scaler, filepath):
    """Guarda el scaler en la ruta especificada."""
    
def entrenar():
    """Entrena con descarga integrada."""
    # 1. Descargar datos train
    # 2. Guardar scaler_train
    # 3. Crear entorno + agente
    # 4. Entrenar
    # 5. Guardar modelo
    # 6. LIBERAR MEMORIA (del, gc.collect)
    
def evaluar():
    """Evalúa con descarga integrada."""
    # 1. Descargar datos eval
    # 2. Guardar scaler_eval (opcional)
    # 3. Cargar scaler_train
    # 4. Crear entorno eval (con train_scaler)
    # 5. Evaluar
    # 6. LIBERAR MEMORIA

def _guardar_metadata():
    """Guarda TODA la config + metadata de ejecución."""
    # Serializa UnifiedConfig.model_dump()
    # Añade metadata de ejecución
```

### Métodos Eliminados
```python
_cargar_datos(data_id)           # Ya no carga de datasets/
_cargar_scaler(data_id)          # Ya no carga de datasets/
```

## 🧠 Decisiones de Diseño Importantes

### 1. Scaler en Evaluación
**Decisión:** Usar `scaler_train` en el entorno de evaluación  
**Razón:** Consistencia con producción (donde solo tendremos el scaler de train)  
**Implementación:**
```python
# En evaluar()
train_scaler = joblib.load(self.config.Output.scaler_train_path)
eval_env = TradingEnv(..., scaler=train_scaler)  # NO eval_scaler
```

### 2. Gestión de Memoria
**Decisión:** Liberar explícitamente memoria entre fases  
**Razón:** Evitar out-of-memory con datasets grandes  
**Implementación:**
```python
# Después de entrenar
del train_data
del entorno_train
del train_scaler
gc.collect()

# Después de evaluar
del eval_data
del eval_env
del eval_scaler
gc.collect()
```

### 3. Metadata Completa
**Decisión:** Guardar TODO `UnifiedConfig` en metadata  
**Razón:** Trazabilidad completa, reproducibilidad  
**Implementación:**
```python
config_dict = self.config.model_dump()  # Serializa TODO
config_dict["metadata_execution"] = {...}  # Añade info de ejecución
```

### 4. Validación de Fechas Walk-Forward
**Decisión:** Validar que eval sea posterior a train  
**Razón:** Prevenir data leakage en walk-forward  
**Implementación:**
```python
if train_end >= eval_start:
    raise ValueError("eval debe ser posterior a train")
```

## 📊 Impacto en el Flujo de Trabajo

### Ventajas
✅ Menos pasos manuales (1 comando vs 2)  
✅ No necesidad de gestionar datasets/ manualmente  
✅ Menos uso de disco (no se guardan DataFrames)  
✅ Trazabilidad completa en un solo directorio  
✅ Consistencia: mismo scaler en eval que en producción  
✅ Walk-forward validado automáticamente  

### Consideraciones
⚠️ Descarga de datos en cada ejecución (más tiempo inicial)  
⚠️ Requiere conexión a internet para descargar datos  
⚠️ No hay reutilización de datos entre experimentos  

### Mitigaciones
- Datos se descargan una vez por fase (train/eval)
- Descarga es relativamente rápida con API de Binance
- Beneficio de memoria y simplicidad compensa el tiempo

## 🧪 Testing Recomendado

### Tests Unitarios a Actualizar
- [ ] `test_UnifiedConfig` - Nuevos métodos
- [ ] `test_cli_args` - Nuevos argumentos
- [ ] `test_train_id_generation` - Nuevo formato

### Tests de Integración
- [ ] Test flujo completo con datos pequeños (1 día train, 1 día eval)
- [ ] Verificar estructura de directorios generada
- [ ] Verificar contenido de metadata (todas las claves presentes)
- [ ] Verificar que scalers se guardan correctamente
- [ ] Test de liberación de memoria (no debe crecer indefinidamente)

### Tests Manuales Realizados
✅ Verificación de sintaxis (no errors con get_errors)  
✅ Commits atómicos con mensajes descriptivos  
✅ Actualización de documentación (README)  

## 📝 Próximos Pasos

### Pendientes (No Bloqueantes)
- [ ] Actualizar tests existentes para nueva estructura
- [ ] Crear tests para flujo unificado
- [ ] Opcional: Añadir cache de datos descargados (si se necesita)
- [ ] Opcional: Soporte para múltiples símbolos en paralelo

### Para Producción
- [ ] Validar con datos reales (semanas/meses de datos)
- [ ] Monitorear uso de memoria en entrenamiento largo
- [ ] Crear guía de troubleshooting
- [ ] Documentar casos de uso avanzados

## 🔗 Commits Relacionados

```
9cdfc8f - refactor(config): actualizar CLI y config para flujo unificado de entrenamiento
e21d26c - refactor(train): implementar flujo unificado de entrenamiento  
7c0f064 - chore: eliminar create_dataset.py obsoleto
8df0d05 - docs: actualizar README con instrucciones del flujo unificado
35d4bf2 - refactor: eliminar pipeline.py y actualizar exports
```

## 📚 Referencias

- Issue/Discusión: Conversación con IA sobre refactorización
- Documentación anterior: README.md (versión anterior)
- Flujo anterior: `create_dataset.py` + `train.py` (preservado en `train.py.backup`)

---

**Autor:** Pedro (con asistencia de GitHub Copilot)  
**Revisión:** Pendiente  
**Aprobación:** Pendiente merge a `dev`
