# 🎯 RESUMEN RÁPIDO: Optimización de Hiperparámetros

## ✅ TU PREGUNTA: ¿Ya se optimiza max_drawdown?

**SÍ**, `max_drawdown_permitido` **YA ESTÁ** en el sistema de optimización.

**Rango ajustado:** `[0.10, 0.25]` (10% a 25% - más conservador que antes)

---

## 📊 TODOS LOS PARÁMETROS OPTIMIZABLES

### 🤖 SAC (8 parámetros)
```
✓ learning_rate        [1e-5, 1e-3]       (log scale)
✓ batch_size          [64, 128, 256, 512]
✓ gamma               [0.95, 0.999]
✓ tau                 [0.001, 0.02]
✓ ent_coef_target     [0.05, 0.3]
✓ learning_starts     [1000, 10000]
✓ gradient_steps      [-1, 1, 2]
✓ buffer_size         [100k, 500k, 1M]
```

### 🎯 ENTORNO (11 parámetros)
```
✓ window_size                  [20, 30, 50, 100]
✓ factor_aversion_riesgo       [1.0, 5.0]
✓ max_drawdown_permitido       [0.10, 0.25] ⭐ AJUSTADO
✓ factor_escala_recompensa     [50.0, 200.0]
✓ peso_retorno_base            [0.5, 2.0]
✓ peso_temporal                [0.1, 0.5]
✓ peso_gestion                 [0.05, 0.4]
✓ peso_drawdown                [0.05, 0.3]
✓ umbral_perdida_pct           [0.001, 0.01]
✓ umbral_ganancia_pct          [0.001, 0.01]
✓ penalizacion_no_operar       [0.0, 0.2]
```

### 🧠 RED NEURONAL (4 parámetros)
```
✓ n_layers          [2, 3]
✓ layer_size        [128, 256, 512]
✓ log_std_init      [-4.0, -2.0]
✓ n_critics         [2, 3]
```

### 💼 PORTAFOLIO (1 parámetro)
```
✓ apalancamiento    [5.0, 20.0]
```

**TOTAL: 24 parámetros optimizándose simultáneamente**

---

## 🔄 CÓMO FUNCIONA

```
┌─────────────────────────────────────────────┐
│  1. Optuna sugiere parámetros inteligentes │
│     (aprende de trials anteriores)          │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  2. Crea configuración temporal             │
│     (actualiza config.yaml con params)      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  3. Entrena modelo reducido                 │
│     (ej: 5000 timesteps en vez de 50000)    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  4. Evalúa en período de validación         │
│     (calcula retornos, DD, win rate, etc.)  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  5. Calcula Sortino Ratio ⭐                │
│     = Retorno / Volatilidad_downside        │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  6. Optuna registra: Params → Sortino       │
│     Aprende qué funciona mejor              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  7. NEXT TRIAL: Sugiere params mejores      │
│     (búsqueda bayesiana inteligente)        │
└─────────────────────────────────────────────┘
```

---

## 📈 MÉTRICAS CALCULADAS

| Métrica | Fórmula | Para qué |
|---------|---------|----------|
| **Sortino Ratio** ⭐ | `retorno / volatilidad_downside` | **MÉTRICA OBJETIVO** - Maximizar esto |
| Sharpe Ratio | `retorno / volatilidad_total` | Comparación (penaliza ganancias también) |
| Total Return | `(final - inicial) / inicial` | Ganancia bruta |
| Max Drawdown | `max((peak - actual) / peak)` | Peor pérdida |
| Win Rate | `trades_ganadores / total_trades` | % operaciones exitosas |

**¿Por qué Sortino?** → Solo penaliza pérdidas, no ganancias (ideal para trading)

---

## 🚀 USO RÁPIDO

### Prueba (10 trials, 30-60 min)
```bash
python3 hyperparameter_tuning.py \
  --symbol BTCUSDT --interval 1h \
  --train-start-date 2024-01-01 --train-end-date 2024-02-01 \
  --eval-start-date 2024-02-02 --eval-end-date 2024-03-01 \
  --n-trials 10 --timesteps-per-trial 3000
```

### Completa (100 trials, 8-12 horas)
```bash
python3 hyperparameter_tuning.py \
  --symbol BTCUSDT --interval 1h \
  --train-start-date 2024-01-01 --train-end-date 2024-06-01 \
  --eval-start-date 2024-06-02 --eval-end-date 2024-09-01 \
  --n-trials 100 --timesteps-per-trial 10000
```

---

## 📊 RESULTADOS

Se generan en: `optimizaciones/optimization_BTCUSDT_1h_YYYYMMDD_HHMMSS/`

```
best_params.yaml        ⭐ MEJORES PARÁMETROS ENCONTRADOS
optimization.log          Log detallado
tuning_BTCUSDT_1h.db     Base de datos Optuna
trials_history.csv        Historial de todos los trials
```

---

## 🔧 APLICAR MEJORES PARÁMETROS

### Automático (crea backup)
```bash
python3 scripts/apply_best_params.py \
  optimizaciones/optimization_20251007_110025/best_params.yaml
```

### Manual
Copia valores de `best_params.yaml` → `src/train/config/config.yaml`

---

## 📉 VISUALIZAR RESULTADOS

```bash
optuna-dashboard sqlite:///optimizaciones/.../tuning_BTCUSDT_1h.db
```

Abre: `http://localhost:8080`

**Verás:**
- 📈 Evolución del Sortino por trial
- 📊 Importancia de parámetros (cuáles afectan más)
- 🎯 Relaciones entre parámetros
- 📉 Efecto individual de cada parámetro

---

## 🎓 INTERPRETAR SORTINO RATIO

| Valor | Calidad | Acción |
|-------|---------|--------|
| < 0 | ❌ Perdiendo | Revisar estrategia |
| 0-1 | 🟨 Pobre | Optimizar más |
| 1-2 | 🟩 Aceptable | Probar más datos |
| 2-3 | ✅ Bueno | Listo para backtest extenso |
| > 3 | ⭐ Excelente | Considerar trading real |

---

## ⚙️ AJUSTAR RANGOS

Edita: `src/train/optimization/ranges.py`

**Ejemplo: Max DD más conservador (5%-12%)**
```python
# Línea 71
'max_drawdown_permitido': trial.suggest_float('max_drawdown_permitido', 0.05, 0.12),
```

**Ejemplo: Learning rate más alto**
```python
# Línea 26
'learning_rate': trial.suggest_float('learning_rate', 1e-4, 5e-3, log=True),
```

---

## ❓ FAQ RÁPIDO

**¿Necesito GPU?**
→ No obligatorio, pero 3-5x más rápido

**¿Puedo pausar/reanudar?**
→ Sí, Optuna guarda estado en SQLite

**¿Cómo sé qué parámetro es más importante?**
→ Dashboard de Optuna → "Hyperparameter Importance"

**¿Trials muy lentos?**
→ Reduce `--timesteps-per-trial` a 3000

**¿Sortino siempre negativo?**
→ Revisa datos, prueba período diferente (bull vs bear)

---

## 📚 DOCUMENTACIÓN COMPLETA

Lee: `docs/GUIA_OPTIMIZACION.md` para detalles exhaustivos

---

## 🎯 TIP CLAVE

1. ✅ Empieza con **10 trials rápidos** (validar que funciona)
2. ✅ Luego **100 trials completos** (encontrar óptimo)
3. ✅ Valida en **período diferente** (evitar overfitting)
4. ✅ Aplica mejores params y **entrena modelo final** con más timesteps (50k+)
