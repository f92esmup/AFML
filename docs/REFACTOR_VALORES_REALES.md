# Refactor: Uso de Valores Reales de Binance

## 📋 Problema Identificado

El sistema de producción estaba usando valores **simulados del entrenamiento** en lugar de valores **reales de la cuenta de Binance**, lo cual podía llevar a:

1. **Normalizaciones incorrectas** en las observaciones del agente
2. **Cálculo erróneo de drawdown** basado en capital simulado
3. **Decisiones incorrectas** del sistema de control de riesgo

## 🔧 Cambios Implementados

### 1. **ProductionConfig** (`src/produccion/config/config.py`)

**ELIMINADO:**
- Campo `capital_inicial` de la configuración
  - Este valor era el capital simulado del entrenamiento (ej: 10,000 USDT)
  - No reflejaba el capital real de la cuenta

**AGREGADO:**
- Comentarios explicativos sobre datos simulados vs reales
- Los valores de `comision` y `slippage` ahora son explícitamente referenciales

```python
# Antes (INCORRECTO)
capital_inicial: float = Field(..., description="Capital inicial del portfolio")

# Después (CORRECTO - removido completamente)
# IMPORTANTE: capital_inicial NO se carga porque debe obtenerse de Binance API
```

---

### 2. **BinanceConnector** (`src/produccion/binance.py`)

**AGREGADO:**

#### Nuevos atributos privados:
```python
self._equity_inicial: float = 0.0      # Equity REAL al iniciar
self._balance_inicial: float = 0.0     # Balance REAL al iniciar
```

#### Nuevo método `initialize_account()`:
```python
def initialize_account(self) -> bool:
    """
    Inicializa la cuenta obteniendo los valores REALES iniciales de Binance.
    DEBE llamarse ANTES de inicializar ControlRiesgo y ObservacionBuilder.
    
    Returns:
        True si la inicialización fue exitosa, False en caso contrario
    """
```

Este método:
- ✅ Obtiene información REAL de la cuenta desde Binance API
- ✅ Guarda `equity_inicial` y `balance_inicial` reales
- ✅ Inicializa `max_equity` con el equity real
- ✅ Detecta y advierte si ya hay posiciones abiertas

#### Nuevas propiedades públicas:
```python
@property
def equity_inicial(self) -> float:
    """Equity inicial REAL obtenido de Binance al iniciar"""
    
@property
def balance_inicial(self) -> float:
    """Balance inicial REAL obtenido de Binance al iniciar"""
```

---

### 3. **ControlRiesgo** (`src/produccion/control_riesgo.py`)

**MODIFICADO:**

#### Constructor actualizado:
```python
def __init__(self, config: ProductionConfig, binance: BinanceConnector) -> None:
    """
    IMPORTANTE: BinanceConnector.initialize_account() debe haberse llamado ANTES
    de crear esta instancia para obtener valores reales de la cuenta.
    """
```

**CAMBIOS CLAVE:**
- ❌ **Eliminado:** `self.capital_inicial = config.capital_inicial`
- ✅ **Agregado:** Validación que `binance.equity_inicial != 0.0`
- ✅ **Cambiado:** `self.max_equity_alcanzado = binance.equity_inicial`

**Ahora usa equity REAL:**
```python
# Antes (INCORRECTO)
self.max_equity_alcanzado = config.capital_inicial  # Valor simulado!

# Después (CORRECTO)
self.max_equity_alcanzado = binance.equity_inicial  # Valor REAL de Binance!
```

#### Prevención de errores:
```python
if binance.equity_inicial == 0.0:
    raise ValueError(
        "BinanceConnector no inicializado. Llamar a initialize_account() primero"
    )
```

---

### 4. **ObservacionBuilder** (`src/produccion/observacion.py`)

**MODIFICADO:**

#### Constructor actualizado:
```python
def __init__(
    self, 
    config: ProductionConfig, 
    scaler: StandardScaler,
    equity_inicial: float  # NUEVO PARÁMETRO REQUERIDO
) -> None:
```

**CAMBIOS CLAVE:**

**Escalas DINÁMICAS basadas en valores REALES:**
```python
# Antes (INCORRECTO - valores hardcodeados)
self.equity_scale = 10000.0  # Valor asumido!
self.pnl_scale = 1000.0      # Valor asumido!

# Después (CORRECTO - basado en equity REAL)
self.equity_scale = equity_inicial           # Escala real
self.pnl_scale = equity_inicial * 0.1        # 10% del equity real
```

#### Validación de entrada:
```python
if equity_inicial <= 0.0:
    raise ValueError(
        f"equity_inicial inválido: {equity_inicial}. "
        "Debe obtenerse de BinanceConnector.equity_inicial después de initialize_account()"
    )
```

---

### 5. **live.py** (Script principal)

**MODIFICADO - Nuevo flujo de inicialización:**

```python
# 1. Crear BinanceConnector
binance = BinanceConnector(cliente_binance, config)

# 2. CRÍTICO: Inicializar cuenta para obtener valores REALES
if not binance.initialize_account():
    raise RuntimeError("❌ Error al inicializar cuenta de Binance")

# 3. Constructor de observaciones (usa equity REAL)
observacion_builder = ObservacionBuilder(
    config, 
    config.scaler, 
    binance.equity_inicial  # ← Valor REAL obtenido de Binance
)

# 4. Control de riesgo (usa equity REAL)
control_riesgo = ControlRiesgo(config, binance)  # ← Valida internamente
```

**ORDEN CRÍTICO:**
1. Crear `BinanceConnector`
2. Llamar `binance.initialize_account()` **ANTES** de crear otros componentes
3. Pasar valores reales a `ObservacionBuilder` y `ControlRiesgo`

---

## 🧪 Tests Actualizados

### Archivos modificados:
- ✅ `tests/produccion/conftest.py` - Fixture `mock_binance_connector`
- ✅ `tests/produccion/test_observacion.py` - Todos los tests actualizados
- ✅ `tests/produccion/test_config.py` - Eliminada validación de `capital_inicial`
- ✅ `tests/produccion/test_control_riesgo.py` - Usa binance inicializado
- ✅ `tests/produccion/test_binance.py` - Tests para `initialize_account()`

### Nuevo fixture en `conftest.py`:
```python
@pytest.fixture
def mock_binance_connector(mock_binance_client, config_metadata_dict):
    """Mock del BinanceConnector ya inicializado con valores reales."""
    connector = BinanceConnector(mock_binance_client, config)
    
    # Simular initialize_account
    connector._equity_inicial = 10000.0
    connector._balance_inicial = 10000.0
    connector._equity = 10000.0
    connector._balance = 10000.0
    connector._max_equity = 10000.0
    
    return connector
```

---

## 📊 Comparación Antes/Después

### **Antes (INCORRECTO):**
```
config.yaml (entrenamiento)
  ↓
capital_inicial: 10000.0 (SIMULADO)
  ↓
ObservacionBuilder.equity_scale = 10000.0 (HARDCODED)
ControlRiesgo.max_equity = 10000.0 (HARDCODED)
  ↓
❌ Sistema opera con valores que NO reflejan la realidad
```

### **Después (CORRECTO):**
```
Binance API
  ↓
binance.initialize_account()
  ↓
equity_inicial = 15,247.82 USDT (REAL)
  ↓
ObservacionBuilder.equity_scale = 15,247.82 (DINÁMICO)
ControlRiesgo.max_equity = 15,247.82 (DINÁMICO)
  ↓
✅ Sistema opera con valores REALES de la cuenta
```

---

## 🎯 Beneficios

1. **Normalización correcta**: Las observaciones del agente usan escalas basadas en el equity real
2. **Drawdown preciso**: El control de riesgo calcula drawdown desde el equity real inicial
3. **Adaptabilidad**: El sistema funciona correctamente independientemente del capital de la cuenta
4. **Seguridad**: Validaciones previenen uso de valores no inicializados
5. **Transparencia**: Logs explícitos sobre valores reales vs simulados

---

## ⚠️ IMPORTANTE: Checklist de Uso

Cuando ejecutes el sistema en producción, asegúrate de:

- [ ] El archivo de configuración del entrenamiento NO se usa para capital inicial
- [ ] `binance.initialize_account()` se llama **ANTES** de crear otros componentes
- [ ] Los logs muestran "Equity inicial (REAL)" con el valor correcto de Binance
- [ ] Las advertencias sobre posiciones existentes se revisan si aparecen
- [ ] El sistema rechaza continuar si `initialize_account()` retorna `False`

---

## 🔍 Logs Esperados

Al iniciar correctamente verás:
```
✅ Conector de Binance creado
Inicializando cuenta desde Binance API...
✅ Cuenta inicializada correctamente
   Balance inicial: 15247.82 USDT
   Equity inicial: 15247.82 USDT
   Posición abierta: NO
✅ Cuenta de Binance inicializada con valores REALES
✅ Constructor de observaciones inicializado
   Window size: 30
   Normalización portfolio: SÍ
   Equity scale (REAL): 15247.82 USDT
   PnL scale (REAL): 1524.78 USDT
✅ Control de riesgo inicializado
   Max drawdown permitido: 20.0%
   Equity inicial (REAL): 15247.82 USDT
   Balance inicial (REAL): 15247.82 USDT
```

---

## 📝 Notas Finales

- El valor de `capital_inicial` en `config_metadata.yaml` es **solo informativo** del entrenamiento
- Los valores de `comision` y `slippage` en config son **referenciales**, no se usan para trading real
- Todos los valores críticos **DEBEN** provenir de la API de Binance
- El sistema **FALLA EXPLÍCITAMENTE** si no se inicializa correctamente

---

**Fecha de implementación:** 5 de octubre de 2025  
**Issue:** Valores sensibles tomados del archivo de configuración en lugar de Binance API
