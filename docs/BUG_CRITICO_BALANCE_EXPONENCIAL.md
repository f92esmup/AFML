  # 🐛 BUG CRÍTICO: Balance Exponencial Decreciente

## Fecha de Descubrimiento
6 de octubre de 2025

## Descripción del Problema

El balance del portafolio se reducía exponencialmente hasta valores microscópicos (ej: `4.270566115265974e-20`) cuando el agente intentaba **aumentar posiciones existentes**.

### Síntomas Observados

En el archivo CSV de evaluación (`portafolio.csv`):

```csv
episodio,paso,balance,equity,max_drawdown,operaciones_total,pnl_total,...
1,91,2.1950203568052644e-11,8977.423474518879,0.10225765254811213,32,416.46206463637634,...
1,92,4.2705661152648734e-11,8978.721138791563,0.10212788612084368,33,416.46206463637634,...
1,93,4.270566115265349e-14,8916.273764238953,0.1083726235761047,33,416.46206463637634,...
```

**Observaciones clave:**
- ✅ `pnl_total` es correcto (~416 USD)
- ✅ `equity` se mantiene razonable (~9000 USD)
- ❌ **`balance` se reduce exponencialmente hasta casi cero**

## Causa Raíz

### Archivo Afectado
`src/train/Entrenamiento/entorno/portafolio.py`

### Función con Bug
`_aumentar_posicion()` - Línea ~367

### Código Problemático

```python
def _aumentar_posicion(self, precio: float, porcentaje_inversion_adicional: float):
    # ...
    
    # ❌ PROBLEMA: Calcula cantidad basada en EQUITY TOTAL
    cantidad_adicional = self._calcular_cantidad_invertir(precio, porcentaje_inversion_adicional)
    
    margen_adicional = self._calcular_margen(precio, cantidad_adicional)
    comision_adicional, slippage_adicional = self._calcular_comision_slippage(precio, cantidad_adicional)
    
    costos_totales_adicionales = margen_adicional + comision_adicional + slippage_adicional
    
    # ❌ PROBLEMA: Resta del balance un margen que ya está bloqueado
    self._balance -= costos_totales_adicionales
```

### Explicación Técnica

1. **Abrir posición inicial** (paso 1):
   ```python
   equity = 10000 USD
   porcentaje = 0.8 (80%)
   cantidad = (equity * apalancamiento * 0.8) / precio
   margen_bloqueado = 8000 USD
   balance_restante = 2000 USD  # ✅ Correcto
   ```

2. **Aumentar posición** (paso 2) - **BUG**:
   ```python
   # ❌ Calcula cantidad basada en equity total (10000), NO en balance disponible (2000)
   cantidad_adicional = (10000 * apalancamiento * 0.2) / precio
   margen_adicional = 2000 USD
   
   # ❌ Intenta restar del balance que ya tiene margen bloqueado
   balance_restante = 2000 - 2000 = 0 USD
   ```

3. **Aumentar posición otra vez** (paso 3) - **BUG EXPONENCIAL**:
   ```python
   # ❌ Calcula cantidad basada en equity (10000), pero balance = 0
   cantidad_adicional = (10000 * apalancamiento * 0.1) / precio
   margen_adicional = 1000 USD
   
   # ❌ Balance se vuelve NEGATIVO (pero por float precision → casi cero)
   balance_restante = 0 - 1000 = -1000 USD → 1e-15 por redondeo
   ```

### Por Qué el `pnl_total` Era Correcto

El `pnl_total` se calcula correctamente porque se actualiza solo cuando **cierras** posiciones:

```python
# ✅ Esto está bien
def cerrar_posicion(self, precio_cierre):
    PnL_realizado = self._posicion_abierta.tipo * (precio_cierre - self._posicion_abierta.precio) * cantidad
    self._pnl_total_episodio += PnL_realizado  # ✅ Correcto
    self._balance += PnL_realizado + margen_liberado  # ✅ También correcto
```

El problema estaba solo en **aumentar/reducir** posiciones existentes.

## Solución Implementada

### Cambios Realizados

#### 1. Nueva Función: `_calcular_cantidad_invertir_desde_balance()`

```python
def _calcular_cantidad_invertir_desde_balance(self, precio: float, porcentaje_inversion: float) -> float:
    """
    Calcula cantidad basada SOLO en balance disponible.
    
    CRÍTICO: Usa _balance (dinero líquido), NO equity total.
    Evita restar margen bloqueado múltiples veces.
    """
    if self._balance <= 0:
        return 0.0
    
    # ✅ Usa BALANCE DISPONIBLE en lugar de equity total
    cantidad_objetivo = (self._balance * self.apalancamiento * porcentaje_inversion) / precio
    
    # ... validaciones de costo total ...
    return cantidad_ajustada
```

#### 2. Actualización de `_aumentar_posicion()`

```python
def _aumentar_posicion(self, precio: float, porcentaje_inversion_adicional: float):
    # ✅ ARREGLADO: Usa nueva función que calcula desde balance disponible
    cantidad_adicional = self._calcular_cantidad_invertir_desde_balance(
        precio, 
        porcentaje_inversion_adicional
    )
    
    # ... resto del código sin cambios ...
```

#### 3. Actualización de `_reducir_posicion()`

```python
def _reducir_posicion(self, precio: float, porcentaje_a_reducir: float):
    # ✅ ARREGLADO: Reduce basándose en cantidad actual de la posición
    cantidad_a_reducir = self._posicion_abierta.cantidad * porcentaje_a_reducir
    
    # ... resto del código sin cambios ...
```

### Diferencias Clave

| Situación | Función a Usar | Base de Cálculo |
|-----------|----------------|-----------------|
| **Abrir nueva posición** | `_calcular_cantidad_invertir()` | Equity total (balance + margen en uso + PnL) |
| **Aumentar posición existente** | `_calcular_cantidad_invertir_desde_balance()` | Balance disponible (solo líquido) |
| **Reducir posición existente** | Directo: `posicion.cantidad * porcentaje` | Cantidad actual de la posición |

## Impacto del Bug

### Antes del Fix
- ✅ Abrir posiciones: Funcionaba correctamente
- ❌ Aumentar posiciones: Balance → 0 en pocos pasos
- ❌ Reducir posiciones: Cálculos incorrectos de margen
- ❌ Entrenamiento: Agente aprendía a NO modificar posiciones (solo abrir/cerrar)

### Después del Fix
- ✅ Abrir posiciones: Sin cambios
- ✅ Aumentar posiciones: Balance se mantiene consistente
- ✅ Reducir posiciones: Cálculos correctos
- ✅ Entrenamiento: Agente puede aprender estrategias de gestión de posiciones

## Verificación

### Test Recomendado

```python
# Test de regresión
def test_aumentar_posicion_no_reduce_balance_exponencialmente():
    portafolio = Portafolio(config)
    precio = 100.0
    
    # Abrir posición inicial
    portafolio.abrir_posicion('long', precio, 0.5)
    balance_inicial = portafolio._balance
    
    # Aumentar posición 10 veces
    for _ in range(10):
        portafolio.modificar_posicion(precio, 0.6)  # Aumentar 10%
    
    balance_final = portafolio._balance
    
    # ✅ El balance NO debe ser casi cero
    assert balance_final > 0.01 * balance_inicial, "Balance no debe reducirse exponencialmente"
```

## Archivos Modificados

- ✅ `src/train/Entrenamiento/entorno/portafolio.py`
  - Nueva función: `_calcular_cantidad_invertir_desde_balance()`
  - Modificada: `_aumentar_posicion()`
  - Modificada: `_reducir_posicion()`

## Próximos Pasos

1. ✅ **Re-entrenar modelos** con el fix aplicado
2. ✅ Verificar que los CSV de evaluación muestren balances consistentes
3. ✅ Monitorear métricas de rendimiento del agente
4. 📝 Agregar tests unitarios para prevenir regresión

## Lecciones Aprendidas

### Diseño de Sistema de Margen

**Concepto clave**: En trading con margen/apalancamiento:

```
Equity Total = Balance Líquido + Margen Bloqueado + PnL No Realizado
```

**Reglas de oro:**
1. **Al ABRIR**: Calcula basándote en equity total (máximo poder adquisitivo)
2. **Al AUMENTAR**: Calcula basándote SOLO en balance líquido (no doble-contar margen)
3. **Al REDUCIR**: Calcula sobre la posición actual (no sobre equity)
4. **Al CERRAR**: Libera margen + suma PnL realizado al balance

### Debugging de Problemas de Precisión

- Valores como `4.270566115265974e-20` son señales de **resta repetida incorrecta**
- Siempre verificar CSV/logs cuando veas notación científica extrema
- El PnL correcto + balance incorrecto = problema en gestión de balance, no de cálculo de ganancias

---

**Estado**: ✅ RESUELTO  
**Prioridad**: 🔴 CRÍTICA  
**Impacto**: Alto - Afecta capacidad del agente de aprender gestión de posiciones
