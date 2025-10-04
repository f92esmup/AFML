# Tests para el módulo utils

Este directorio contiene los tests para los módulos de utilidades del proyecto AFML.

## Estructura

```plaintext
tests/utils/
├── __init__.py
├── conftest.py           # Fixtures compartidas
├── test_logger.py        # Tests para el sistema de logging
├── test_utils.py         # Tests para funciones utilitarias
└── README.md            # Este archivo
```

## Módulos testeados

### test_logger.py

Tests para el módulo `src/utils/logger.py`:

- **TestSetupLogger**: Tests para la función `setup_logger()`
  - Configuración por defecto (consola)
  - Configuración con archivo
  - Creación de directorios
  - Limpieza de handlers
  - Formato de logs

- **TestConfigureFileLogging**: Tests para `configure_file_logging()`
  - Configuración del logger principal
  - Configuración del logger de Stable-Baselines3
  - Escritura en archivos

- **TestConfigureSb3Logger**: Tests para `configure_sb3_logger()`
  - Configuración específica de SB3
  - Propagación de logs

- **TestStreamToLogger**: Tests para la clase `StreamToLogger`
  - Redirección de streams a logger
  - Manejo de múltiples líneas

- **TestRedirectStdoutToFile**: Tests para `redirect_stdout_to_file()`
  - Captura de stdout/stderr

- **TestIntegration**: Tests de integración
  - Flujo completo de configuración
  - Cambios de configuración

### test_utils.py

Tests para el módulo `src/utils/utils.py`:

- **TestCalcularSteps**: Tests para la función `calcular_steps()`
  - Cálculos correctos con diferentes valores
  - Validación de errores (valores negativos o cero)
  - Tipos de datos
  - Tests parametrizados

## Ejecución de tests

### Ejecutar todos los tests del módulo utils

```bash
pytest tests/utils/ -v
```

### Ejecutar tests específicos

```bash
# Solo tests de logger
pytest tests/utils/test_logger.py -v

# Solo tests de utils
pytest tests/utils/test_utils.py -v

# Un test específico
pytest tests/utils/test_logger.py::TestSetupLogger::test_setup_logger_consola_por_defecto -v
```

### Con cobertura

```bash
pytest tests/utils/ --cov=src/utils --cov-report=html
```

## Fixtures disponibles

Definidas en `conftest.py`:

- `temp_log_dir`: Directorio temporal para logs
- `temp_log_file`: Archivo temporal para logs
- `clean_logger`: Logger AFML limpio para testing
- `clean_sb3_logger`: Logger SB3 limpio para testing
- `training_base_dir`: Directorio simulado de entrenamiento

## Notas importantes

1. Los tests limpian automáticamente los handlers de logging después de cada test para evitar interferencias.

2. Se usan directorios y archivos temporales que se limpian automáticamente al finalizar.

3. Los tests de redirección de stdout/stderr pueden requerir restauración manual del stdout/stderr original si fallan.

4. Para los tests de integración, se simula el flujo completo de configuración de logging en un entrenamiento.

## Dependencias

- pytest
- Fixtures de pytest: `tmp_path`

## Cobertura esperada

Los tests cubren:

- ✅ Configuración básica de logging
- ✅ Configuración con archivos
- ✅ Integración con Stable-Baselines3
- ✅ Redirección de stdout/stderr
- ✅ Manejo de errores
- ✅ Casos edge (valores límite)
- ✅ Flujos de integración completos
