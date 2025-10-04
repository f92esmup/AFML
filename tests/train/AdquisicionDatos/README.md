# Tests para AdquisicionDatos

Este directorio contiene los tests unitarios y de integración para los módulos de adquisición y preprocesamiento de datos.

## Estructura

```
tests/train/AdquisicionDatos/
├── __init__.py                    # Inicialización del paquete de tests
├── conftest.py                    # Fixtures compartidas
├── test_adquisicion.py           # Tests para el módulo de adquisición
├── test_preprocesamiento.py      # Tests para el módulo de preprocesamiento
└── README.md                      # Este archivo
```

## Fixtures Disponibles

### `mock_binance_client`
Mock del cliente de Binance que simula las respuestas de la API para descargas de datos históricos.

### `sample_config`
Configuración completa de ejemplo basada en `UnifiedConfig` con todos los parámetros necesarios.

### `sample_ohlcv_dataframe`
DataFrame con datos OHLCV sintéticos pero realistas (100 registros).

### `sample_ohlcv_with_gaps`
DataFrame con gaps en el índice temporal para probar la continuidad.

### `sample_ohlcv_with_nans`
DataFrame con valores NaN para probar la interpolación.

## Tests de Adquisición (`test_adquisicion.py`)

### Cobertura

- **TestIntervalMap**: Validación del mapeo de intervalos
- **TestDataDownloaderInit**: Inicialización correcta del downloader
- **TestDataDownloaderDownloadChunk**: Descarga de chunks individuales
- **TestDataDownloaderGetTimeIntervals**: Cálculo de intervalos temporales
- **TestDataDownloaderProcessToDataframe**: Procesamiento de datos a DataFrame
- **TestDataDownloaderRun**: Ejecución completa del proceso de descarga
- **TestDataDownloaderIntegration**: Tests de integración

### Ejecutar tests de adquisición

```bash
# Todos los tests de adquisición
pytest tests/train/AdquisicionDatos/test_adquisicion.py -v

# Una clase específica
pytest tests/train/AdquisicionDatos/test_adquisicion.py::TestDataDownloaderRun -v

# Un test específico
pytest tests/train/AdquisicionDatos/test_adquisicion.py::TestDataDownloaderRun::test_run_returns_dataframe -v
```

## Tests de Preprocesamiento (`test_preprocesamiento.py`)

### Cobertura

- **TestPreprocesamientoInit**: Inicialización del preprocesador
- **TestPreprocesamientoContinuidad**: Verificación de continuidad temporal
- **TestPreprocesamientoInterpolacion**: Interpolación de valores faltantes
- **TestPreprocesamientoCalculoIndicadores**: Cálculo de indicadores técnicos
- **TestPreprocesamientoEliminarFaltantes**: Eliminación de valores NaN
- **TestPreprocesamientoScaler**: Ajuste del StandardScaler
- **TestPreprocesamientoRun**: Pipeline completo de preprocesamiento
- **TestPreprocesamientoIntegration**: Tests de integración

### Ejecutar tests de preprocesamiento

```bash
# Todos los tests de preprocesamiento
pytest tests/train/AdquisicionDatos/test_preprocesamiento.py -v

# Una clase específica
pytest tests/train/AdquisicionDatos/test_preprocesamiento.py::TestPreprocesamientoRun -v

# Un test específico
pytest tests/train/AdquisicionDatos/test_preprocesamiento.py::TestPreprocesamientoRun::test_run_returns_dataframe_and_scaler -v
```

## Ejecutar todos los tests

```bash
# Todos los tests de AdquisicionDatos
pytest tests/train/AdquisicionDatos/ -v

# Con cobertura
pytest tests/train/AdquisicionDatos/ --cov=src.train.AdquisicionDatos --cov-report=html

# Con marcadores específicos (si se añaden)
pytest tests/train/AdquisicionDatos/ -v -m "not slow"
```

## Notas Importantes

1. **Datos Mock**: Los tests usan datos simulados para no depender de la API de Binance
2. **Fixtures Compartidas**: Todas las fixtures están en `conftest.py` para reutilización
3. **Cobertura**: Se recomienda mantener cobertura > 80%
4. **Integración**: Los tests de integración validan el flujo completo

## Dependencias

```bash
pytest
pytest-cov
pandas
numpy
pandas-ta
scikit-learn
```

## Contribuir

Al añadir nuevos tests:
1. Seguir la convención de nombres `test_<función>_<caso>`
2. Agrupar tests relacionados en clases
3. Usar fixtures cuando sea posible
4. Documentar casos edge y comportamientos esperados
5. Mantener tests independientes entre sí
