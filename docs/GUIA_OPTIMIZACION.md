# 📊 GUÍA COMPLETA DE OPTIMIZACIÓN DE HIPERPARÁMETROS

## 🎯 Objetivo

Encontrar la **mejor combinación de parámetros** para maximizar el **Sortino Ratio** del agente de trading.

---

## 🧠 ¿Cómo funciona?

### **Búsqueda Bayesiana con Optuna (TPE)**

No es una búsqueda aleatoria, es **inteligente**:

```
Trial 1:  Parámetros aleatorios      → Sortino = -5.2
Trial 2:  Aprende del Trial 1        → Sortino = -3.1  ✅ Mejor
Trial 3:  Aprende de 1 y 2           → Sortino = 1.8   ✅ Mucho mejor
Trial 10: Converge a zona prometedora → Sortino = 3.2   ✅ Excelente
...
Trial 50: Encuentra óptimo local     → Sortino = 4.5   ⭐ MEJOR
```

**Cada trial aprende de los anteriores** → Converge a buenos parámetros más rápido que búsqueda aleatoria.

---

## 📦 Parámetros Optimizados

### **1️⃣ MODELO SAC (Soft Actor-Critic)**

| Parámetro | Rango | Tipo | Explicación |
|-----------|-------|------|-------------|
| `learning_rate` | `[1e-5, 1e-3]` | Log scale | **Velocidad de aprendizaje**. Muy bajo = aprende lento, muy alto = inestable |
| `batch_size` | `[64, 128, 256, 512]` | Categórico | **Tamaño de lote**. Más grande = más estable pero más memoria |
| `gamma` | `[0.95, 0.999]` | Float | **Factor de descuento**. 0.95 = corto plazo, 0.999 = largo plazo |
| `tau` | `[0.001, 0.02]` | Float | **Soft update**. Qué tan rápido actualiza target networks |
| `ent_coef_target` | `[0.05, 0.3]` | Float | **Exploración**. Más alto = más exploración vs explotación |
| `learning_starts` | `[1000, 10000]` | Int | **Pasos antes de entrenar**. Llena el buffer primero |
| `gradient_steps` | `[-1, 1, 2]` | Categórico | **Updates por step**. -1 = mismo que env steps |
| `buffer_size` | `[100k, 500k, 1M]` | Categórico | **Replay buffer**. Memoria histórica de experiencias |

**¿Por qué estos rangos?**
- `learning_rate`: Basado en literatura de SAC + trading (típicamente 1e-4 a 5e-4)
- `batch_size`: Potencias de 2 por eficiencia GPU
- `gamma`: Trading requiere balance entre corto y largo plazo
- `buffer_size`: Más grande = aprende de más historia, pero más RAM

---

### **2️⃣ ENTORNO DE TRADING**

| Parámetro | Rango | Explicación |
|-----------|-------|-------------|
| `window_size` | `[20, 30, 50, 100]` | **Velas de historia**. 20 = ~1 día (1h), 100 = ~4 días |
| `factor_aversion_riesgo` | `[1.0, 5.0]` | **Aversión al riesgo**. 1 = neutral, 5 = muy conservador |
| `max_drawdown_permitido` | `[0.10, 0.25]` | **Pérdida máxima tolerada**. 10% a 25% |
| `factor_escala_recompensa` | `[50.0, 200.0]` | **Escala de rewards**. Normaliza % a rango [-1, 1] |

**Pesos de Recompensa Multifactorial:**

| Peso | Rango | Componente |
|------|-------|------------|
| `peso_retorno_base` | `[0.5, 2.0]` | **Cambio en equity** (principal) |
| `peso_temporal` | `[0.1, 0.5]` | **Penalización temporal** por mantener pérdidas |
| `peso_gestion` | `[0.05, 0.4]` | **Eficiencia en cierres** (bonifica cierre ganador) |
| `peso_drawdown` | `[0.05, 0.3]` | **Protección contra ruina** (penaliza DD grandes) |

**Umbrales:**

| Parámetro | Rango | Propósito |
|-----------|-------|-----------|
| `umbral_perdida_pct` | `[0.001, 0.01]` | 0.1%-1%. Pérdida mínima para activar penalización |
| `umbral_ganancia_pct` | `[0.001, 0.01]` | 0.1%-1%. Ganancia mínima para bonificar |
| `penalizacion_no_operar` | `[0.0, 0.2]` | Anti-inacción cuando equity cae |

**¿Por qué estos pesos?**
- Suman ~2.0 total para balance
- `peso_retorno_base` es el mayor (principal driver)
- Los demás modulan comportamiento (riesgo, eficiencia, etc.)

---

### **3️⃣ ARQUITECTURA DE RED NEURONAL**

| Parámetro | Rango | Explicación |
|-----------|-------|-------------|
| `n_layers` | `[2, 3]` | **Profundidad**. Más capas = más capacidad pero más lento |
| `layer_size` | `[128, 256, 512]` | **Neuronas por capa**. Más = más capacidad |
| `log_std_init` | `[-4.0, -2.0]` | **Desviación estándar inicial**. Afecta exploración temprana |
| `n_critics` | `[2, 3]` | **Número de Q-networks**. Previene sobreestimación |

**Arquitecturas posibles:**
- `[128, 128]` - Rápida, menos capacidad
- `[256, 256]` - Balance (default típico)
- `[512, 512]` - Máxima capacidad, más lenta
- `[256, 256, 256]` - 3 capas, muy expresiva

---

### **4️⃣ PORTAFOLIO**

| Parámetro | Rango | Explicación |
|-----------|-------|-------------|
| `apalancamiento` | `[5.0, 20.0]` | **Multiplicador de capital**. 5x a 20x (Binance Futures) |

> **Nota**: `comision` y `slippage` están **fijos** (0.1%) para ser realistas con Binance.

---

## 📈 Métricas Calculadas

El sistema calcula **5 métricas** pero **optimiza solo Sortino Ratio**:

### **1. Sortino Ratio** ⭐ (MÉTRICA OBJETIVO)

```python
Sortino = (Retorno promedio - 0) / Desviación estándar de retornos negativos
```

**¿Por qué Sortino y no Sharpe?**
- Sharpe penaliza **toda** la volatilidad (incluso ganancias)
- Sortino penaliza **solo** volatilidad a la baja (pérdidas)
- En trading, queremos ganancias volátiles, no pérdidas volátiles

**Valores típicos:**
- `< 0`: Perdiendo dinero
- `0-1`: Pobre
- `1-2`: Aceptable
- `2-3`: Bueno
- `> 3`: Excelente

### **2. Sharpe Ratio** (Comparación)

```python
Sharpe = (Retorno promedio - 0) / Desviación estándar total
```

### **3. Total Return** (Ganancia bruta)

```python
Total Return = (Equity final - Equity inicial) / Equity inicial
```

### **4. Max Drawdown** (Peor pérdida)

```python
Max DD = max((Equity máximo - Equity actual) / Equity máximo)
```

### **5. Win Rate** (% operaciones ganadoras)

```python
Win Rate = Operaciones ganadoras / Total operaciones
```

---

## 🚀 Uso del Sistema

### **Optimización Rápida (10 trials de prueba)**

```bash
python3 hyperparameter_tuning.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-02-01 \
  --eval-start-date 2024-02-02 \
  --eval-end-date 2024-03-01 \
  --n-trials 10 \
  --timesteps-per-trial 3000
```

**Tiempo estimado:** ~30-60 min (depende de GPU/CPU)

### **Optimización Completa (100 trials)**

```bash
python3 hyperparameter_tuning.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-06-01 \
  --eval-start-date 2024-06-02 \
  --eval-end-date 2024-09-01 \
  --n-trials 100 \
  --timesteps-per-trial 10000
```

**Tiempo estimado:** ~8-12 horas

### **Opciones Avanzadas**

```bash
# Optimizar solo SAC (ignorar entorno/network)
--optimize-sac --no-optimize-env --no-optimize-network

# Cambiar directorio de salida
--output-dir custom_optimization

# Ajustar episodios de evaluación
--n-eval-episodes 3

# Usar archivo de configuración custom
--config mi_config.yaml
```

---

## 📊 Resultados

### **Archivos Generados**

```
optimizaciones/
└── optimization_BTCUSDT_1h_20251007_110025/
    ├── best_params.yaml          # ⭐ MEJORES PARÁMETROS
    ├── optimization.log          # Log completo
    ├── tuning_BTCUSDT_1h.db     # Base de datos Optuna
    └── trials_history.csv        # Historial de todos los trials
```

### **Contenido de `best_params.yaml`**

```yaml
optimization_metadata:
  best_trial: 47
  n_trials: 100
  optimization_date: '2025-10-07T11:00:42'
  
best_metrics:
  sortino_ratio: 4.52        # ⭐ Excelente
  sharpe_ratio: 3.89
  total_return: 0.45         # +45%
  max_drawdown: 0.12         # -12%
  final_equity: 14500.0
  
best_params:
  # SAC
  learning_rate: 0.000234
  batch_size: 256
  gamma: 0.987
  # ... todos los parámetros optimizados
```

---

## 🔧 Aplicar Mejores Parámetros

### **Opción 1: Script Automático**

```bash
python3 scripts/apply_best_params.py \
  optimizaciones/optimization_20251007_110025/best_params.yaml
```

Esto:
1. ✅ Crea backup de `config.yaml` → `config.yaml.backup`
2. ✅ Actualiza `config.yaml` con mejores parámetros
3. ✅ Muestra resumen de cambios

### **Opción 2: Manual**

Copia los valores de `best_params.yaml` a `src/train/config/config.yaml`.

---

## 📉 Visualización de Resultados

### **Dashboard Interactivo de Optuna**

```bash
optuna-dashboard sqlite:///optimizaciones/optimization_20251007_110025/tuning_BTCUSDT_1h.db
```

Abre en: `http://localhost:8080`

**Visualizaciones disponibles:**
- 📈 Evolución del Sortino Ratio por trial
- 📊 Importancia de cada parámetro (cuáles afectan más)
- 🎯 Parallel coordinates (relaciones entre parámetros)
- 📉 Slice plots (efecto individual de cada parámetro)

---

## 🧪 Estrategias de Optimización

### **Estrategia 1: Exploración amplia**

```bash
--n-trials 100 --timesteps-per-trial 5000
```

✅ Explora mucho espacio de búsqueda  
✅ Trials rápidos  
❌ Menos precisión por trial

### **Estrategia 2: Explotación precisa**

```bash
--n-trials 30 --timesteps-per-trial 20000
```

✅ Cada trial más preciso  
❌ Menos exploración  
❌ Más lento

### **Estrategia 3: Híbrida (Recomendada)**

```bash
# Fase 1: Exploración rápida
--n-trials 50 --timesteps-per-trial 5000

# Fase 2: Refinamiento (usa mejores params de Fase 1)
--n-trials 20 --timesteps-per-trial 15000
```

---

## ⚙️ Ajustar Rangos de Búsqueda

### **Archivo:** `src/train/optimization/ranges.py`

**Ejemplo: Hacer búsqueda más conservadora**

```python
# Antes
'max_drawdown_permitido': trial.suggest_float('max_drawdown_permitido', 0.10, 0.25)

# Después (más conservador, 5%-15%)
'max_drawdown_permitido': trial.suggest_float('max_drawdown_permitido', 0.05, 0.15)
```

**Ejemplo: Probar learning rates más altos**

```python
# Antes
'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)

# Después
'learning_rate': trial.suggest_float('learning_rate', 5e-5, 5e-3, log=True)
```

---

## 🎓 Interpretación de Resultados

### **¿Qué es un buen Sortino Ratio?**

| Sortino | Interpretación | Acción |
|---------|----------------|--------|
| `< 0` | Perdiendo dinero | ❌ Revisar estrategia completa |
| `0-1` | Retorno pobre | 🟨 Optimizar más o cambiar período |
| `1-2` | Aceptable | 🟩 Probar con más datos/timesteps |
| `2-3` | Bueno | ✅ Listo para backtesting extenso |
| `> 3` | Excelente | ⭐ Considerar trading real (con precaución) |

### **¿El mejor trial tiene overfitting?**

**Señales de alerta:**
- Sortino muy alto (> 5) pero Max DD también alto
- Win Rate > 80% (poco realista)
- Total Return > 100% en período corto

**Solución:**
- Validar en **período out-of-sample** diferente
- Usar **k-fold walk-forward** (implementar después)
- Probar en datos de otro símbolo (ej: ETHUSDT)

---

## 📚 Recursos Adicionales

- **Optuna Docs**: https://optuna.readthedocs.io/
- **SAC Paper**: https://arxiv.org/abs/1801.01290
- **Sortino Ratio**: https://en.wikipedia.org/wiki/Sortino_ratio

---

## ❓ FAQ

### **¿Puedo pausar y reanudar la optimización?**

Sí, Optuna guarda estado en la base de datos SQLite. Reinicia con:

```bash
# Mismo comando, añadirá más trials a la misma base de datos
python3 hyperparameter_tuning.py ... --n-trials 50
```

### **¿Cómo saber qué parámetros son más importantes?**

En el dashboard de Optuna, ve a **"Hyperparameter Importance"**.

### **¿Puedo optimizar otros parámetros?**

Sí, edita `src/train/optimization/ranges.py` y añade:

```python
'mi_parametro': trial.suggest_float('mi_parametro', min_val, max_val)
```

### **¿Necesito GPU?**

No es obligatorio, pero **acelera mucho** (3-5x más rápido). El sistema detecta GPU automáticamente.

---

## 🛠️ Troubleshooting

### **Error: "Out of memory"**

Reduce `batch_size` o `buffer_size` en los rangos.

### **Trials muy lentos**

Reduce `--timesteps-per-trial` a 3000-5000.

### **Sortino siempre negativo**

- Revisa que los datos sean correctos (suficientes velas)
- Prueba con período diferente (bull market vs bear market)
- Verifica que la función de recompensa tiene sentido

---

**🎯 TIP FINAL:** Empieza con 10-20 trials rápidos para validar que todo funciona, luego haz una optimización completa de 100+ trials.
