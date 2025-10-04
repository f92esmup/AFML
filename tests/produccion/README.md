# Tests del Módulo de Producción

Este directorio contiene los tests para todos los componentes del sistema de trading en producción.

## Estructura

```
tests/produccion/
├── __init__.py
├── conftest.py                    # Fixtures compartidas
├── README.md                      # Este archivo
├── test_config.py                 # Tests de configuración
├── test_binance.py                # Tests del conector Binance
├── test_dataprovider.py           # Tests del proveedor de datos
├── test_observacion.py            # Tests del constructor de observaciones
├── test_agente_produccion.py      # Tests del agente SAC
├── test_control_riesgo.py         # Tests del sistema de control de riesgo
└── test_registro.py               # Tests del sistema de registro
```

## Ejecutar Tests

### Todos los tests de producción
```bash
pytest tests/produccion/ -v
```

### Un archivo específico
```bash
pytest tests/produccion/test_config.py -v
```

### Con cobertura
```bash
pytest tests/produccion/ --cov=src/produccion --cov-report=html
```

## Fixtures Disponibles

Ver `conftest.py` para la lista completa de fixtures compartidas:

- `config_metadata_dict`: Configuración válida de metadata
- `temp_training_dir`: Directorio temporal con estructura de entrenamiento
- `mock_binance_client`: Cliente mock de Binance
- `mock_async_client`: Cliente asíncrono mock
- `sample_market_data`: Datos de mercado con indicadores
- `fitted_scaler`: StandardScaler ya ajustado
- `mock_sac_model`: Modelo SAC mock
- `binance_state_dict`: Estado del portfolio
- `vela_dict`: Datos de una vela completa

## Cobertura Esperada

Objetivo: >90% de cobertura para todos los módulos de producción.
