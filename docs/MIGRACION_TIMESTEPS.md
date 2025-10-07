# Migración de Episodios a Total Timesteps

**Fecha:** 7 de Octubre de 2025  
**Estado:** ✅ Completado

## 📋 Resumen Ejecutivo

Se ha migrado el sistema de entrenamiento de usar **número de episodios** (`--episodios`) a usar directamente **total timesteps** (`--total-timesteps`) como argumento de entrada. Este cambio proporciona control directo sobre el número de pasos de entrenamiento, independiente del tamaño del dataset.

## 🎯 Motivación

**Problema anterior:**
- El usuario especificaba `--episodios 10`
- Se calculaba `total_timesteps = episodios * (len(data) - window_size)`
- El número real de timesteps variaba según el tamaño del dataset
- Difícil predecir el tiempo de entrenamiento
- No es el estándar de la industria (Stable-Baselines3 usa `total_timesteps`)

**Solución implementada:**
- El usuario especifica directamente `--total-timesteps 50000`
- Control preciso sobre el entrenamiento
- Predecible y reproducible
- Alineado con el estándar de la industria

## 🔄 Cambios Realizados

### 1. CLI (`src/train/config/cli.py`)

**Argumentos actualizados:**

```python
# NUEVO argumento (recomendado)
parser.add_argument(
    "--total-timesteps",
    type=int,
    default=10000,
    required=False,
    help="Número total de pasos (timesteps) para entrenar el agente",
)

# DEPRECATED (se mantiene temporalmente con warning)
parser.add_argument(
    "--episodios",
    type=int,
    default=None,
    required=False,
    help="[DEPRECATED] Usar --total-timesteps en su lugar.",
)
```

**Validación con deprecation warning:**
- Si se usa `--episodios`, se muestra un warning de deprecación
- Se requiere migrar a `--total-timesteps`

### 2. Configuración (`src/train/config/config.py`)

**EntornoConfig actualizado:**

```python
class EntornoConfig(BaseModel):
    # ANTES:
    # episodios: int = Field(0, ge=0, description="...")
    
    # AHORA:
    total_timesteps: int = Field(
        10000, 
        gt=0, 
        description="Número total de timesteps para entrenar el agente."
    )
```

### 3. Script de Entrenamiento (`train.py`)

**Cambios principales:**

```python
# ANTES:
max_steps_per_episode = len(train_data) - self.config.entorno.window_size
total_timesteps = calcular_steps(self.config.entorno.episodios, max_steps_per_episode)
log.info(f"Timesteps totales calculados: {total_timesteps}")

# AHORA:
total_timesteps = self.config.entorno.total_timesteps
log.info(f"Timesteps totales configurados: {total_timesteps}")
```

**Import eliminado:**
- Removida la importación de `calcular_steps` (ya no se necesita)

### 4. Utilidades (`src/utils/utils.py`)

**Función eliminada:**
- `calcular_steps()` completamente eliminada del codebase

### 5. Configuración YAML (`src/train/config/config.yaml`)

```yaml
entorno:
  # ANTES:
  # episodios: 0
  
  # AHORA:
  total_timesteps: 10000
```

### 6. Documentación

**Archivos actualizados:**
- ✅ `README.md` - Ejemplos de uso actualizados
- ✅ `docs/refactor_flujo_unificado.md` - Referencia al nuevo argumento
- ✅ `docs/MIGRACION_TIMESTEPS.md` - Nuevo documento (este)

## 📝 Guía de Migración para Usuarios

### Antes (DEPRECATED)

```bash
python train.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-06-30 \
  --eval-start-date 2024-07-01 \
  --eval-end-date 2024-09-30 \
  --episodios 10  # ❌ OBSOLETO
```

### Ahora (RECOMENDADO)

```bash
python train.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-06-30 \
  --eval-start-date 2024-07-01 \
  --eval-end-date 2024-09-30 \
  --total-timesteps 50000  # ✅ DIRECTO Y PREDECIBLE
```

### Cómo Calcular un Valor Equivalente

Si quieres replicar entrenamientos anteriores:

```python
# Supongamos que antes usabas:
# --episodios 10
# Y tu dataset tenía 5000 filas con window_size=30

timesteps_equivalentes = episodios * (len(data) - window_size)
# = 10 * (5000 - 30)
# = 49,700 timesteps

# Usa entonces:
# --total-timesteps 50000
```

**Nota:** Este cálculo es aproximado. Para entrenamientos nuevos, es mejor elegir valores redondos como 10k, 50k, 100k, etc.

## 🎯 Valores Recomendados

| Propósito | Total Timesteps | Tiempo Aprox. |
|-----------|----------------|---------------|
| Prueba rápida | 10,000 | ~2-5 min |
| Desarrollo/Debug | 50,000 | ~10-20 min |
| Entrenamiento corto | 100,000 | ~30-60 min |
| Entrenamiento medio | 500,000 | ~4-8 horas |
| Entrenamiento largo | 1,000,000+ | ~12-24 horas |

**Nota:** Los tiempos son aproximados y dependen del hardware (CPU/GPU).

## ✅ Ventajas del Cambio

1. **Control directo**: El usuario especifica exactamente cuántos pasos
2. **Predecibilidad**: Mismo número de timesteps independiente del dataset
3. **Estándar de la industria**: Consistente con Stable-Baselines3 y otros frameworks
4. **Código más limpio**: Elimina cálculos intermedios innecesarios
5. **Mejor documentación**: Más claro para usuarios nuevos

## 🔧 Cambios Técnicos Internos

### Metadata Guardada

El archivo `config_metadata.yaml` ahora guarda:

```yaml
metadata_execution:
  fecha_ejecucion: "2025-10-07T15:30:45"
  train_date_range: "2024-01-01 to 2024-06-30"
  eval_date_range: "2024-07-01 to 2024-09-30"
  total_timesteps: 50000  # ← NUEVO (antes era episodios_entrenamiento)
  episodios_evaluacion: 3
  train_id: "train_BTCUSDT_20240101_20240630_lr0.0003_bs256_ws30_20251007_153045"
```

### Logs Actualizados

```
INFO - Timesteps totales configurados: 50000
# Antes decía: "Timesteps totales calculados: 49700"
```

## ⚠️ Compatibilidad Hacia Atrás

**Opción A (implementada):** Deprecation Warning

- `--episodios` aún existe pero muestra warning
- Requiere migrar a `--total-timesteps`
- Se eliminará en futuras versiones

**Comportamiento actual:**

```bash
# Si usas --episodios:
python train.py ... --episodios 10

# Salida:
# ⚠️  DEPRECATION: --episodios está obsoleto. 
# Usa --total-timesteps para especificar directamente el número de pasos.
# ValueError: Debe usar --total-timesteps en lugar de --episodios.
```

## 🧪 Testing

Para verificar que todo funciona correctamente:

```bash
# 1. Prueba rápida (10k timesteps)
python train.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-02-01 \
  --eval-start-date 2024-02-01 \
  --eval-end-date 2024-03-01 \
  --total-timesteps 10000

# 2. Verificar metadata
cat entrenamientos/train_*/config_metadata.yaml | grep total_timesteps

# 3. Verificar que no se usa calcular_steps
grep -r "calcular_steps" src/  # No debería encontrar nada
```

## 📊 Impacto en el Proyecto

### Archivos Modificados

| Archivo | Tipo de Cambio | Líneas |
|---------|----------------|--------|
| `src/train/config/cli.py` | Actualizado | ~30 |
| `src/train/config/config.py` | Actualizado | ~10 |
| `train.py` | Simplificado | ~15 |
| `src/utils/utils.py` | Eliminado | -7 |
| `src/train/config/config.yaml` | Actualizado | 1 |
| `README.md` | Documentación | ~20 |
| `docs/refactor_flujo_unificado.md` | Documentación | ~10 |
| `docs/MIGRACION_TIMESTEPS.md` | Nuevo | +300 |

**Total:** ~8 archivos, ~370 líneas modificadas/añadidas

### Backward Compatibility

- ✅ Deprecation warning implementado
- ✅ Metadata actualizada automáticamente
- ✅ Código existente requiere actualización mínima
- ❌ No hay conversión automática de episodios a timesteps

## 🚀 Próximos Pasos

1. ✅ Implementación completada
2. ✅ Documentación actualizada
3. ⏳ Testing extensivo en diferentes configuraciones
4. ⏳ Comunicar cambio a usuarios (si aplica)
5. ⏳ En futuras versiones: eliminar completamente `--episodios`

## 📚 Referencias

- [Stable-Baselines3 Documentation](https://stable-baselines3.readthedocs.io/)
- Commit: `[HASH]` (actualizar después del commit)
- Issue/PR: N/A (cambio interno)

---

**Autor:** Pedro  
**Fecha:** 7 de Octubre de 2025  
**Versión:** 1.0
