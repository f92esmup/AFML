# Guía de Tests - Módulo de Producción

## 📋 Resumen

Se han creado **tests completos con pytest** para todos los módulos de producción del sistema de trading:

### Archivos de Test Creados

1. **`conftest.py`** - Fixtures compartidas (238 líneas)
   - Configuraciones mock
   - Clientes Binance mock (sync y async)
   - Datos de mercado de ejemplo
   - Estados de portfolio
   - Modelo SAC mock

2. **`test_config.py`** - Tests de configuración (195 líneas)
   - Carga de configuración desde YAML
   - Validación de parámetros
   - Manejo de errores (archivo no encontrado, YAML inválido, etc.)
   - Modos LIVE vs TESTNET
   - Parser CLI

3. **`test_binance.py`** - Tests del conector Binance (234 líneas)
   - Inicialización y configuración de apalancamiento
   - Creación de órdenes (MARKET, LIMIT, reduceOnly)
   - Obtención de información de cuenta
   - Cierre de posiciones (normal y emergencia)
   - Cálculo de tamaño de posición

4. **`test_dataprovider.py`** - Tests del proveedor de datos (299 líneas)
   - Inicialización (testnet y producción)
   - Descarga de historial inicial
   - Cálculo de indicadores técnicos (SMA, RSI, MACD, Bollinger Bands)
   - Stream de velas desde WebSocket
   - Actualización de ventana rodante
   - Validación de indicadores

5. **`test_observacion.py`** - Tests del constructor de observaciones (240 líneas)
   - Construcción de observaciones normalizadas
   - Normalización de datos de mercado con scaler
   - Normalización de portfolio (opcional)
   - Manejo de ventana insuficiente
   - Casos extremos (equity negativo, PnL muy grande)

6. **`test_agente_produccion.py`** - Tests del agente SAC (249 líneas)
   - Carga del modelo entrenado
   - Predicción determinística
   - Interpretación de acciones:
     - Mantener posición
     - Abrir LONG/SHORT
     - Aumentar LONG/SHORT
     - Cerrar y abrir posición contraria
   - Validación de umbrales
   - Casos extremos

7. **`test_control_riesgo.py`** - Tests del control de riesgo (270 líneas)
   - Verificación de drawdown
   - Actualización de max_equity
   - Validación de acciones pre-ejecución
   - Protocolo de emergencia
   - Reinicio después de emergencia
   - Casos extremos (equity cero, negativo)

8. **`test_registro.py`** - Tests del sistema de registro (286 líneas)
   - Creación de directorios y archivos CSV
   - Registro de pasos del bucle principal
   - Registro de emergencias
   - Obtención de estadísticas de sesión
   - Manejo de valores None y campos faltantes

## 📊 Cobertura Total

- **8 archivos de test**
- **~2,000+ líneas de código de tests**
- **100+ casos de test**
- Cobertura esperada: **>90%** para todos los módulos

## 🚀 Cómo Ejecutar los Tests

### Opción 1: Script automatizado (Recomendado)

```bash
./run_tests_produccion.sh
```

### Opción 2: Comando directo con conda

```bash
# Activar ambiente
conda activate AFML

# Ejecutar todos los tests de producción
pytest tests/produccion/ -v

# Ejecutar un archivo específico
pytest tests/produccion/test_config.py -v

# Con reporte de cobertura
pytest tests/produccion/ --cov=src/produccion --cov-report=html

# Solo mostrar resumen
pytest tests/produccion/ -v --tb=short
```

### Opción 3: Ejecutar tests individuales

```bash
conda activate AFML

# Test específico
pytest tests/produccion/test_binance.py::TestBinanceConnector::test_init_and_setup_leverage -v

# Clase completa
pytest tests/produccion/test_agente_produccion.py::TestInterpretarAccion -v
```

## 🧪 Tipos de Tests Incluidos

### Tests Unitarios
- Inicialización de componentes
- Métodos individuales
- Validación de parámetros
- Manejo de errores

### Tests de Integración
- Flujo entre componentes
- Construcción de observaciones con datos reales
- Ejecución de operaciones

### Tests de Casos Extremos (Edge Cases)
- Valores None y faltantes
- Valores negativos y cero
- Límites de parámetros
- Errores de conexión

### Tests Asíncronos
- WebSocket streams
- Cliente asíncrono de Binance
- Descarga de datos históricos

## 📝 Fixtures Principales

Las fixtures están en `conftest.py` y son compartidas por todos los tests:

```python
# Configuración
- config_metadata_dict: Dict con configuración válida
- temp_training_dir: Directorio temporal con estructura completa
- production_config: Instancia de ProductionConfig

# Mocks de Binance
- mock_binance_client: Cliente sync mock
- mock_async_client: Cliente async mock

# Datos
- sample_market_data: DataFrame con 100 filas de OHLCV + indicadores
- fitted_scaler: StandardScaler ya ajustado
- binance_state_dict: Estado del portfolio
- vela_dict: Datos de una vela completa

# Modelo
- mock_sac_model: Modelo SAC mock con predict()
```

## ✅ Checklist de Validación

Cada módulo tiene tests para:

- [x] Inicialización correcta
- [x] Casos de éxito (happy path)
- [x] Manejo de errores
- [x] Validación de parámetros
- [x] Casos extremos (edge cases)
- [x] Integración con otros componentes
- [x] Valores por defecto
- [x] Tipos de datos correctos

## 🔍 Verificación de Calidad

Los tests verifican:

1. **Corrección funcional**: Los métodos hacen lo que deben hacer
2. **Manejo de errores**: Excepciones se manejan apropiadamente
3. **Validación de datos**: Tipos y rangos correctos
4. **Robustez**: Comportamiento con datos inesperados
5. **Integración**: Componentes funcionan juntos correctamente

## 📈 Próximos Pasos

1. **Ejecutar los tests**:
   ```bash
   ./run_tests_produccion.sh
   ```

2. **Revisar cobertura**:
   ```bash
   conda activate AFML
   pytest tests/produccion/ --cov=src/produccion --cov-report=html
   # Ver reporte en htmlcov/index.html
   ```

3. **Agregar tests adicionales** según sea necesario para casos específicos

4. **Integrar en CI/CD** para ejecución automática

## 🐛 Debugging

Si un test falla:

```bash
# Ver traceback completo
pytest tests/produccion/test_archivo.py::test_especifico -vv

# Ejecutar con pdb (debugger)
pytest tests/produccion/test_archivo.py::test_especifico --pdb

# Ver output de print statements
pytest tests/produccion/test_archivo.py::test_especifico -s
```

## 📚 Recursos

- **Pytest docs**: https://docs.pytest.org/
- **Pytest fixtures**: https://docs.pytest.org/en/stable/fixture.html
- **Pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Creado**: 4 de octubre de 2025
**Tests totales**: 100+ casos
**Cobertura esperada**: >90%
