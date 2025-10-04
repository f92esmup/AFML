# Tests para el Módulo de Entorno

Este directorio contiene los tests para los módulos relacionados con el entorno de entrenamiento de trading.

## Estructura

- `conftest.py`: Fixtures compartidas para todos los tests del entorno
- `test_entorno.py`: Tests para la clase `TradingEnv` (53 tests)
- `test_info_builder.py`: Tests para el módulo `info_builder` (15 tests)
- `README.md`: Este archivo

## Fixtures Principales

### Configuración

- `valid_config_dict`: Diccionario con configuración válida
- `config`: Instancia de `UnifiedConfig` completa

### Datos

- `sample_data`: DataFrame con datos de mercado sintéticos (100 filas)
- `sample_data_normalized`: Datos normalizados + scaler
- `small_sample_data`: Dataset pequeño (50 filas) para tests específicos

### Componentes

- `portafolio`: Instancia de `Portafolio` inicializada
- `trading_env`: Entorno sin normalización
- `trading_env_normalized`: Entorno con normalización aplicada

## Ejecutar los Tests

### Todos los tests del entorno

```bash
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/ -v
```

### Tests específicos

```bash
# Solo test_entorno.py
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/test_entorno.py -v

# Solo test_info_builder.py
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/test_info_builder.py -v

# Una clase específica
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/test_entorno.py::TestReset -v

# Un test específico
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/test_entorno.py::TestReset::test_reset_returns_observation_and_info -v
```

### Con cobertura (si pytest-cov está instalado)

```bash
PYTHONPATH=/home/pedro/AFML:$PYTHONPATH pytest tests/train/Entrenamiento/entorno/ --cov=src.train.Entrenamiento.entorno --cov-report=html
```

## Cobertura de Tests

### test_entorno.py (53 tests)

- ✅ Inicialización del entorno
- ✅ Validación de parámetros
- ✅ Espacios de observación y acción
- ✅ Reset del entorno
- ✅ Ejecución de steps
- ✅ Cálculo de recompensas
- ✅ Ejecución de acciones
- ✅ Normalización de datos
- ✅ Métodos auxiliares
- ✅ Casos límite

### test_info_builder.py (15 tests)

- ✅ Función `_ensure_keys`
- ✅ Función `build_info_dict`
- ✅ Estructura de diccionarios
- ✅ Valores por defecto
- ✅ Consistencia de schema

## Resumen de Resultados

```
======================== 68 passed, 6 warnings in 0.49s ========================
```

**Total: 68 tests pasando exitosamente**

## Notas

- Los tests usan datos sintéticos generados con numpy
- Se prueban tanto casos exitosos como casos de error
- Se valida la estructura de observaciones e info dicts
- Se prueba con y sin normalización de datos
- Los warnings son sobre deprecaciones menores de pandas (usar 'h' en vez de 'H')

