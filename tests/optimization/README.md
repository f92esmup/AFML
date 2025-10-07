# Guía de Tests para Sistema de Optimización

## Estructura de Tests

```
tests/optimization/
├── __init__.py
├── conftest.py                 # Configuración pytest
├── test_metrics.py            # Tests de métricas (Sortino, Sharpe, etc.)
├── test_ranges.py             # Tests de rangos de hiperparámetros
└── test_tuner.py              # Tests de integración Optuna
```

## Ejecución de Tests

### Tests Rápidos (solo unitarios)
```bash
pytest tests/optimization/ -v -m "not slow"
```

### Tests Completos (incluye integración)
```bash
pytest tests/optimization/ -v
```

### Test Específico
```bash
pytest tests/optimization/test_metrics.py::TestSortinoRatio::test_sortino_constant_equity_returns_zero -v
```

### Con Cobertura
```bash
pytest tests/optimization/ --cov=src/train/optimization --cov-report=html
```

## Tests Críticos

### 1. Test de Sortino con Equity Constante
**Archivo**: `test_metrics.py::TestSortinoRatio::test_sortino_constant_equity_returns_zero`

**Propósito**: Verificar que cuando el agente NO opera (equity constante), el Sortino Ratio sea **0.0** y NO 100.0

**Importancia**: Este era el bug crítico detectado en los logs donde agentes inactivos obtenían la mejor puntuación.

```python
def test_sortino_constant_equity_returns_zero(self):
    equity = np.array([10000] * 100)
    sortino = metrics.calculate_sortino_ratio(equity)
    assert sortino == 0.0, "Equity constante debe retornar Sortino=0, no 100"
```

### 2. Test de Sortino con Solo Ganancias
**Archivo**: `test_metrics.py::TestSortinoRatio::test_sortino_only_positive_returns`

**Propósito**: Cuando solo hay ganancias (sin pérdidas), el Sortino debe usar volatilidad total como proxy y retornar un valor razonable < 100.

```python
def test_sortino_only_positive_returns(self):
    equity = np.array([10000 * (1.01 ** i) for i in range(100)])
    sortino = metrics.calculate_sortino_ratio(equity)
    assert sortino > 0
    assert sortino < 100  # Debe usar volatilidad total, no infinito
```

### 3. Test de Validación learning_starts
**Archivo**: `test_tuner.py::TestProblematicCases::test_learning_starts_validation`

**Propósito**: Verificar que `learning_starts < timesteps_per_trial` para evitar agentes que nunca entrenan.

**Contexto**: En los logs, `learning_starts=6000-7000` con `timesteps=5000` causó que el agente nunca entrenara.

```python
def test_learning_starts_validation(self, minimal_config, temp_output_dir):
    tuner = HyperparameterTuner(
        config=minimal_config,
        n_trials=1,
        timesteps_per_trial=2000,
        output_dir=temp_output_dir
    )
    tuner.optimize()
    
    # Verificar que learning_starts se ajustó correctamente
    learning_starts = best_params['sac']['learning_starts']
    assert learning_starts < 2000
```

### 4. Test de Detección de Agente Inactivo
**Archivo**: `test_tuner.py::TestProblematicCases::test_detect_no_operation_agent`

**Propósito**: Verificar que si un agente no opera (Sortino=0), NO sea seleccionado como el mejor trial.

```python
def test_detect_no_operation_agent(self, minimal_config, temp_output_dir):
    tuner.optimize()
    
    no_operation_trials = [t for t in tuner.study.trials if t.value == 0.0]
    
    if no_operation_trials:
        best_trial = tuner.study.best_trial
        assert best_trial.number not in no_operation_trials
```

### 5. Test de Sortino ≠ 100 en Trials
**Archivo**: `test_tuner.py::TestMetricsValidation::test_sortino_not_100_for_inactive_agent`

**Propósito**: Verificar que ningún trial retorne Sortino=100 (indicaría bug de equity constante).

```python
def test_sortino_not_100_for_inactive_agent(self):
    tuner.optimize()
    
    for trial in tuner.study.trials:
        if trial.value is not None:
            assert trial.value != 100.0
```

## Categorías de Tests

### Métricas (`test_metrics.py`)
- ✅ Cálculo de retornos
- ✅ Sortino Ratio (casos edge: constante, solo ganancias, pérdidas)
- ✅ Sharpe Ratio
- ✅ Max Drawdown
- ✅ Métricas completas (win rate, num trades, etc.)
- ✅ Casos edge (NaN, equity negativo, valores enormes)

### Rangos (`test_ranges.py`)
- ✅ Validación de rangos SAC (learning_rate, batch_size, gamma, etc.)
- ✅ Validación de rangos de entorno (window_size, max_drawdown)
- ✅ Validación de arquitectura de red (n_layers, layer_size)
- ✅ Consistencia entre parámetros (batch_size vs buffer_size)
- ✅ Reproducibilidad con seed

### Integración (`test_tuner.py`)
- ✅ Creación de HyperparameterTuner
- ✅ Ejecución de trials
- ✅ Generación de `best_params.yaml`
- ✅ Generación de base de datos SQLite
- ✅ Detección de casos problemáticos
- ✅ Validación de métricas finitas
- ✅ Manejo de errores

## Marcadores Pytest

### `@pytest.mark.slow`
Tests de integración que ejecutan trials completos (>10 segundos).

**Ejecutar solo tests rápidos**:
```bash
pytest tests/optimization/ -m "not slow"
```

**Ejecutar solo tests lentos**:
```bash
pytest tests/optimization/ -m "slow"
```

### `@pytest.mark.integration`
Tests que requieren ejecución completa del sistema.

## Fixtures Disponibles

### `temp_output_dir`
Directorio temporal para outputs de prueba (se limpia automáticamente).

```python
def test_example(temp_output_dir):
    # temp_output_dir es un Path object
    assert temp_output_dir.exists()
```

### `minimal_config`
Configuración mínima para tests rápidos (2 semanas de datos).

```python
def test_example(minimal_config):
    # minimal_config es UnifiedConfig con datos 2024-01-01 a 2024-01-15
    assert minimal_config.symbol == "BTCUSDT"
```

## Troubleshooting

### Test falla: "Sortino=100 detectado"
**Causa**: El fix en `src/train/optimization/metrics.py` no se aplicó correctamente.

**Solución**: Verificar que `calculate_sortino_ratio` tiene el check de equity constante:
```python
if np.std(returns) == 0:
    log.warning("Equity constante - Agente no opera. Penalizando con Sortino = 0.0")
    return 0.0
```

### Test falla: "learning_starts debe ser < timesteps_per_trial"
**Causa**: El tuner no valida `learning_starts` antes de ejecutar el trial.

**Solución**: Implementar validación en `HyperparameterTuner.objective()`:
```python
if suggested_params['learning_starts'] >= self.timesteps_per_trial:
    suggested_params['learning_starts'] = int(self.timesteps_per_trial * 0.3)
```

### Tests lentos
**Causa**: Los tests de integración ejecutan trials completos.

**Solución**: Usar `-m "not slow"` para ejecutar solo tests unitarios rápidos.

## Cobertura Esperada

- **Métricas**: >95% (crítico)
- **Ranges**: >90%
- **Tuner**: >80% (tiene componentes de integración complejos)

## Checklist de Validación

Antes de hacer commit, verificar:

- [ ] `pytest tests/optimization/ -m "not slow"` pasa (tests rápidos)
- [ ] `pytest tests/optimization/test_metrics.py::TestSortinoRatio::test_sortino_constant_equity_returns_zero -v` pasa (test crítico)
- [ ] No hay warnings sobre Sortino=100
- [ ] Todos los tests de validación de parámetros pasan
- [ ] Cobertura de métricas >95%

## Referencias

- **Bug Sortino=100**: Ver `docs/ANALISIS_LOGS_OPTIMIZACION.md` sección "Problema 1"
- **Bug learning_starts**: Ver `docs/ANALISIS_LOGS_OPTIMIZACION.md` sección "Problema 2"
- **Documentación Optuna**: https://optuna.readthedocs.io/
