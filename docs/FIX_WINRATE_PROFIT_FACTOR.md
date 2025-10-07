# Fix: Win Rate y Profit Factor siempre en 0

## Problema Identificado

### Síntomas
- Win Rate siempre mostraba 0.00%
- Profit Factor siempre mostraba 0.00
- Num Trades contaba todos los pasos (ej: 318) en lugar de solo los cierres

### Causa Raíz

El DataFrame `df_operacion` generado por `agente.EvaluarEnv()` contiene **una fila por cada paso del episodio**, no solo las operaciones de cierre:

```csv
episodio,paso,tipo_accion,operacion,pnl_realizado
1,100,mantener,,                     <- Sin PnL
1,101,mantener,,                     <- Sin PnL
1,102,mantener,,                     <- Sin PnL
1,196,long,abrir_long,               <- Sin PnL (apertura)
1,202,long,aumento_posicion,         <- Sin PnL (modificación)
1,203,long,reduccion_parcial,-0.17   <- PnL parcial
```

Las funciones `calculate_win_rate()` y `calculate_profit_factor()` intentaban calcular métricas usando **todas las filas**, incluyendo:
- Acciones "mantener" (sin PnL)
- Aperturas de posición (sin PnL realizado)
- Modificaciones de posición (pueden tener PnL parcial)

Como resultado, buscaban `pnl_realizado` en todas las filas, pero esta columna solo tiene valores en operaciones de cierre completo.

## Solución Implementada

### Cambios en `src/train/optimization/metrics.py`

#### 1. `calculate_win_rate()`
**Antes:**
```python
winning_trades = (trades_df[pnl_col] > 0).sum()
total_trades = len(trades_df)  # ❌ Cuenta TODAS las filas
```

**Después:**
```python
# ✅ FILTRAR solo filas con PnL realizado (operaciones de cierre)
closed_trades = trades_df[trades_df[pnl_col].notna() & (trades_df[pnl_col] != '')]

if len(closed_trades) == 0:
    return 0.0

# Convertir a numérico por si acaso hay strings
pnl_values = pd.to_numeric(closed_trades[pnl_col], errors='coerce')
pnl_values = pnl_values.dropna()

winning_trades = (pnl_values > 0).sum()
total_trades = len(pnl_values)  # ✅ Solo operaciones cerradas
```

#### 2. `calculate_profit_factor()`
**Antes:**
```python
gross_profit = trades_df[trades_df[pnl_col] > 0][pnl_col].sum()
gross_loss = abs(trades_df[trades_df[pnl_col] < 0][pnl_col].sum())
# ❌ Falla si hay NaN o strings vacíos
```

**Después:**
```python
# ✅ FILTRAR solo filas con PnL realizado
closed_trades = trades_df[trades_df[pnl_col].notna() & (trades_df[pnl_col] != '')]

if len(closed_trades) == 0:
    return 0.0

# Convertir a numérico
pnl_values = pd.to_numeric(closed_trades[pnl_col], errors='coerce')
pnl_values = pnl_values.dropna()

gross_profit = pnl_values[pnl_values > 0].sum()
gross_loss = abs(pnl_values[pnl_values < 0].sum())
```

#### 3. `calculate_metrics()`
**Antes:**
```python
metrics['num_trades'] = len(trades_df)  # ❌ Cuenta todas las filas
```

**Después:**
```python
# ✅ Contar solo las operaciones con PnL realizado (cierres)
pnl_col = None
for col in ['pnl_realizado', 'profit', 'pnl', 'return']:
    if col in trades_df.columns:
        pnl_col = col
        break

if pnl_col is not None:
    closed_trades = trades_df[trades_df[pnl_col].notna() & (trades_df[pnl_col] != '')]
    metrics['num_trades'] = len(closed_trades)  # ✅ Solo cierres
else:
    metrics['num_trades'] = 0
```

## Prueba de Validación

```python
# DataFrame de prueba con 10 filas: 6 "mantener" + 4 cierres
test_data = {
    'pnl_realizado': ['', 150.5, '', '', -50.25, '', 80.0, '', -30.0, '']
}
# 2 ganadores (150.5, 80.0) y 2 perdedores (-50.25, -30.0)

# Resultados:
# Win Rate: 50.00% ✅ (2/4 operaciones ganadoras)
# Profit Factor: 2.87 ✅ (230.50 / 80.25)
# Num Trades: 4 ✅ (solo cuenta cierres)
```

## Observación Adicional: Falta de Cierres en Evaluación

Al analizar los logs, se detectó que **muchos episodios terminan sin cierres de posición**:
- Los episodios terminan prematuramente por `max_drawdown`
- Las posiciones abiertas no se cierran forzosamente al final del episodio
- Resultado: `Num Trades: 0`, `Win Rate: 0.00%`, `Profit Factor: 0.00`

### Implicación
Las métricas de trading (win rate, profit factor) **solo son significativas cuando hay cierres de posición**. Si un episodio no tiene cierres, estas métricas correctamente reportan 0.

### Posible Mejora Futura
Considerar implementar un cierre forzoso de posiciones abiertas al final de cada episodio de evaluación para:
1. Obtener métricas de trading más completas
2. Reflejar el PnL realizado total del episodio
3. Evitar posiciones "colgadas" sin cierre

## Archivos Modificados

- `src/train/optimization/metrics.py`:
  - `calculate_win_rate()` - Filtra solo operaciones cerradas
  - `calculate_profit_factor()` - Filtra solo operaciones cerradas
  - `calculate_metrics()` - Cuenta solo operaciones cerradas en `num_trades`

## Impacto

✅ **Win Rate** ahora calcula correctamente el porcentaje de operaciones ganadoras vs perdedoras
✅ **Profit Factor** ahora calcula correctamente la relación ganancia/pérdida bruta
✅ **Num Trades** ahora cuenta solo operaciones cerradas, no todos los pasos
✅ Manejo robusto de valores NaN y strings vacíos en columna `pnl_realizado`
✅ Conversión automática a numérico para evitar errores de tipo

## Fecha de Fix
7 de octubre de 2025
