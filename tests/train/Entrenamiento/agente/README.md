# Tests del Módulo Agente SAC

Este directorio contiene los tests unitarios y de integración para el módulo `AgenteSac` del sistema de trading algorítmico.

## Estructura

```
tests/train/Entrenamiento/agente/
├── __init__.py
├── conftest.py           # Fixtures compartidas
├── test_agente.py        # Tests del AgenteSac
└── README.md            # Este archivo
```

## Fixtures Disponibles

### `temp_output_dir`
Crea un directorio temporal para outputs de prueba que se limpia automáticamente después de cada test.

### `mock_config`
Proporciona una configuración completa de `UnifiedConfig` con todos los parámetros necesarios para el agente SAC.

### `simple_gym_env`
Entorno Gymnasium simple para pruebas que implementa:
- Espacio de observación: Box(10,) con valores continuos
- Espacio de acción: Box(3,) con valores en [-1, 1]
- Información estructurada en 3 secciones: entorno, portafolio, operacion

### `mock_sac_model`
Mock del modelo SAC para pruebas sin necesidad de entrenamiento real.

### `sample_evaluation_data`
Datos de ejemplo para pruebas de evaluación con estructura de DataFrames.

## Clases de Tests

### `TestAgenteSacInit`
Tests del constructor del agente:
- ✅ Inicialización exitosa
- ✅ Validación de timesteps inválidos
- ✅ Asignación correcta de atributos de configuración

### `TestAgenteSacCrearModelo`
Tests del método `CrearModelo()`:
- ✅ Creación exitosa del modelo SAC
- ✅ Validación de entorno None o inválido
- ✅ Configuración correcta de policy_kwargs
- ✅ Validación de parámetros (buffer_size, batch_size, learning_rate)

### `TestAgenteSacTrain`
Tests del método `train()`:
- ✅ Entrenamiento exitoso
- ✅ Error cuando no se ha creado el modelo
- ✅ Verificación de llamada a `model.learn()`

### `TestAgenteSacGuardarModelo`
Tests del método `GuardarModelo()`:
- ✅ Guardado exitoso del modelo
- ✅ Error cuando no hay modelo para guardar
- ✅ Creación automática de directorios necesarios

### `TestAgenteSacEvaluarEnv`
Tests del método `EvaluarEnv()`:
- ✅ Evaluación exitosa del entorno
- ✅ Validación de entorno None
- ✅ Carga de modelo desde disco
- ✅ Guardado de archivos CSV (entorno, portafolio, operacion)
- ✅ Evaluación con múltiples episodios
- ✅ Estructura correcta de DataFrames retornados

### `TestAgenteSacIntegration`
Tests de integración del flujo completo:
- ✅ Flujo: crear → entrenar → guardar
- ✅ Flujo completo con evaluación

## Ejecutar los Tests

### Todos los tests del agente
```bash
pytest tests/train/Entrenamiento/agente/test_agente.py -v
```

### Una clase específica de tests
```bash
pytest tests/train/Entrenamiento/agente/test_agente.py::TestAgenteSacInit -v
```

### Un test específico
```bash
pytest tests/train/Entrenamiento/agente/test_agente.py::TestAgenteSacInit::test_init_success -v
```

### Con cobertura
```bash
pytest tests/train/Entrenamiento/agente/test_agente.py --cov=src.train.Entrenamiento.agente --cov-report=html
```

### Con salida detallada
```bash
pytest tests/train/Entrenamiento/agente/test_agente.py -vv -s
```

## Notas Importantes

### Mocking
- Los tests usan `@patch` para mockear el modelo SAC y evitar entrenamientos reales
- Los tests de integración verifican el flujo completo sin realizar entrenamientos largos
- Se usan timesteps pequeños (100-1000) para acelerar las pruebas

### Directorios Temporales
- Todos los tests usan `temp_output_dir` que se limpia automáticamente
- No se crean archivos permanentes durante los tests

### Dependencias
- `pytest`: Framework de testing
- `pytest-mock`: Para mocking avanzado
- `gymnasium`: Para entornos de prueba
- `stable-baselines3`: Para el modelo SAC
- `pandas`, `numpy`: Para manipulación de datos

## Cobertura Esperada

Los tests cubren:
- ✅ Todos los métodos públicos de `AgenteSac`
- ✅ Casos de éxito y error
- ✅ Validación de parámetros
- ✅ Manejo de excepciones
- ✅ Flujos de integración completos

## Mejoras Futuras

- [ ] Tests con diferentes configuraciones de red (arquitecturas)
- [ ] Tests de serialización/deserialización del modelo
- [ ] Tests de robustez con entornos complejos
- [ ] Tests de performance con grandes timesteps
- [ ] Tests de convergencia del entrenamiento
