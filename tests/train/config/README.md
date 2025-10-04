# Tests de Configuración del Sistema de Entrenamiento

Este directorio contiene los tests unitarios para los módulos de configuración del sistema de trading automatizado.

## Estructura de Archivos

```text
tests/train/config/
├── __init__.py           # Marca el directorio como paquete Python
├── conftest.py           # Fixtures compartidas para todos los tests
├── test_cli.py           # Tests para el módulo CLI (cli.py)
├── test_config.py        # Tests para el módulo de configuración (config.py)
└── README.md             # Este archivo
```

## Archivos Testeados

### 1. `test_cli.py` - Tests del módulo CLI

Tests para `src/train/config/cli.py`

**Cobertura:**

- ✅ Parseo de argumentos válidos
- ✅ Valores por defecto
- ✅ Argumentos requeridos faltantes (--symbol, --interval, fechas)
- ✅ Validación de argumentos vacíos
- ✅ Validación de episodios (cero, negativos)
- ✅ Validación de formatos de fecha (YYYY-MM-DD)
- ✅ Validación de coherencia temporal (fechas de fin > fechas de inicio)
- ✅ Validación de walk-forward (evaluación posterior a entrenamiento)
- ✅ Diferentes símbolos e intervalos
- ✅ Rutas de configuración personalizadas
- ✅ Números grandes de episodios

**Total de tests:** 22

### 2. `test_config.py` - Tests del módulo de configuración

Tests para `src/train/config/config.py`

**Cobertura:**

#### IndicadoresConfig (3 tests)

- ✅ Configuración válida de indicadores técnicos
- ✅ Validación de valores negativos
- ✅ Validación de valores cero

#### PreprocesamientoConfig (3 tests)

- ✅ Configuración válida de preprocesamiento
- ✅ Métodos de interpolación válidos
- ✅ Métodos de interpolación inválidos

#### DataDownloaderConfig (4 tests)

- ✅ Configuración válida de descarga de datos
- ✅ Validación de formato de fechas
- ✅ Validación de límite máximo (1500)
- ✅ Validación de límite cero

#### PortafolioConfig (3 tests)

- ✅ Configuración válida de portafolio
- ✅ Validación de capital inicial negativo
- ✅ Validación de comisión excesiva

#### EntornoConfig (3 tests)

- ✅ Configuración válida de entorno
- ✅ Validación de window_size cero
- ✅ Validación de max_drawdown > 1

#### SACModelConfig (3 tests)

- ✅ Configuración válida de modelo SAC
- ✅ Validación de learning_rate negativo
- ✅ Validación de gamma > 1

#### OutputConfig (2 tests)

- ✅ Configuración válida de output
- ✅ Configuración sin scaler de evaluación

#### UnifiedConfig (13 tests)

- ✅ Configuración unificada válida
- ✅ Validación de secciones faltantes
- ✅ Generación de train_id
- ✅ Generación de train_id con configuración incompleta
- ✅ Integración de argumentos CLI
- ✅ Manejo de sección 'entorno' faltante
- ✅ Adición de rutas de output
- ✅ Carga completa para entrenamiento unificado
- ✅ Validación de argumentos None
- ✅ Validación de ruta de configuración faltante
- ✅ Validación de archivo no encontrado
- ✅ Validación de archivo YAML vacío
- ✅ Validación de YAML inválido

#### DatasetConfig (2 tests)

- ✅ Configuración mínima de dataset
- ✅ Configuración completa de dataset

#### NetArchConfig (2 tests)

- ✅ Configuración válida de arquitectura de red
- ✅ Diferentes arquitecturas de red

#### PolicyKwargsConfig (1 test)

- ✅ Configuración válida de policy_kwargs

**Total de tests:** 39

## Fixtures Compartidas (`conftest.py`)

### Fixtures disponibles

1. **`valid_config_yaml`**: Diccionario con configuración YAML válida completa
2. **`temp_config_file`**: Archivo temporal YAML para tests (se limpia automáticamente)
3. **`valid_cli_args`**: Lista de argumentos CLI válidos
4. **`mock_args_namespace`**: Namespace de argumentos mock para tests

## Ejecutar los Tests

### Todos los tests de configuración

```bash
conda run -n AFML python -m pytest tests/train/config/ -v
```

### Solo tests de CLI

```bash
conda run -n AFML python -m pytest tests/train/config/test_cli.py -v
```

### Solo tests de configuración

```bash
conda run -n AFML python -m pytest tests/train/config/test_config.py -v
```

### Con cobertura de código

```bash
conda run -n AFML python -m pytest tests/train/config/ --cov=src.train.config --cov-report=html
```

### Tests específicos

```bash
# Ejecutar una clase de tests específica
conda run -n AFML python -m pytest tests/train/config/test_cli.py::TestParseArgsTraining -v

# Ejecutar un test específico
conda run -n AFML python -m pytest tests/train/config/test_cli.py::TestParseArgsTraining::test_parse_args_valid_arguments -v
```

## Estadísticas

- **Total de tests:** 61
- **Tests de CLI:** 22
- **Tests de Config:** 39
- **Fixtures compartidas:** 4
- **Tasa de éxito:** 100% ✅

## Cobertura de Casos de Uso

### Casos positivos ✅

- Configuraciones válidas con todos los parámetros correctos
- Valores por defecto
- Diferentes combinaciones de parámetros válidos

### Casos negativos ✅

- Argumentos faltantes
- Valores fuera de rango
- Formatos inválidos
- Validaciones de negocio (fechas coherentes, walk-forward, etc.)
- Archivos inexistentes o corruptos

### Casos edge ✅

- Valores mínimos y máximos
- Configuraciones parciales vs completas
- Archivos temporales y limpieza

## Dependencias

Los tests requieren las siguientes dependencias:

- `pytest >= 8.0`
- `pydantic >= 2.0`
- `pyyaml`
- Módulos del proyecto: `src.train.config.cli`, `src.train.config.config`

## Notas de Implementación

1. **Mocking:** Se utiliza `unittest.mock.patch` para:
   - Simular argumentos de línea de comandos (`sys.argv`)
   - Controlar timestamps en generación de train_id (`datetime.now`)

2. **Archivos temporales:** Los fixtures que crean archivos temporales incluyen cleanup automático usando `yield`

3. **Parametrización:** Se usa `@pytest.mark.parametrize` para tests con múltiples casos similares

4. **Organización:** Los tests están organizados en clases que corresponden a las clases del código fuente

## Mantenimiento

Al modificar los archivos fuente (`cli.py` o `config.py`):

1. Actualizar los tests correspondientes
2. Añadir nuevos tests para nueva funcionalidad
3. Verificar que todos los tests pasen: `pytest tests/train/config/ -v`
4. Actualizar este README si se añaden nuevas secciones

## Autor

Fecha de creación: Octubre 2025
Framework de testing: pytest
