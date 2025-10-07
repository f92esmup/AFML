# Optimización de Hiperparámetros - Sistema de Trading RL

Sistema de optimización de hiperparámetros usando **Optuna** para búsqueda bayesiana inteligente de los mejores parámetros del modelo SAC y entorno de trading.

## 🎯 Objetivo

Maximizar el **Sortino Ratio** (retorno ajustado por downside risk) mediante la optimización automática de:

- **Hiperparámetros del modelo SAC** (learning rate, batch size, gamma, tau, etc.)
- **Parámetros del entorno de trading** (window size, pesos de recompensa, umbrales, etc.)
- **Arquitectura de red neuronal** (número de capas, neuronas por capa, etc.)
- **Parámetros del portafolio** (apalancamiento - opcional)

## 📋 Requisitos

Primero, instalar Optuna y dependencias de visualización:

```bash
pip install optuna plotly kaleido
```

## 🚀 Uso Básico

### Ejemplo Rápido (50 trials)

```bash
python hyperparameter_tuning.py \
    --symbol BTCUSDT \
    --interval 1h \
    --train-start-date 2024-01-01 \
    --train-end-date 2024-02-01 \
    --eval-start-date 2024-02-02 \
    --eval-end-date 2024-03-01 \
    --n-trials 50 \
    --timesteps-per-trial 5000
```

### Optimización Intensiva (200 trials)

```bash
python hyperparameter_tuning.py \
    --symbol BTCUSDT \
    --interval 1h \
    --train-start-date 2024-01-01 \
    --train-end-date 2024-03-01 \
    --eval-start-date 2024-03-02 \
    --eval-end-date 2024-04-01 \
    --n-trials 200 \
    --timesteps-per-trial 10000
```

## ⚙️ Parámetros Principales

| Parámetro | Descripción | Default | Recomendado |
|-----------|-------------|---------|-------------|
| `--n-trials` | Número de combinaciones a probar | 50 | 50-200 |
| `--timesteps-per-trial` | Timesteps de entrenamiento por trial | 5000 | 5000-10000 |
| `--n-eval-episodes` | Episodios de evaluación | 1 | 1-3 |
| `--optimize-sac` | Optimizar parámetros SAC | True | True |
| `--optimize-env` | Optimizar parámetros entorno | True | True |
| `--optimize-network` | Optimizar arquitectura red | True | True |
| `--optimize-portfolio` | Optimizar portafolio | False | False |

## 📊 Parámetros Optimizados

### Modelo SAC
- `learning_rate`: [1e-5, 1e-3] (log scale)
- `batch_size`: [64, 128, 256, 512]
- `gamma`: [0.95, 0.999]
- `tau`: [0.001, 0.02]
- `ent_coef_target`: [0.05, 0.3]
- `learning_starts`: [1000, 10000]
- `gradient_steps`: [-1, 1, 2]
- `buffer_size`: [100k, 500k, 1M]

### Entorno de Trading
- `window_size`: [20, 30, 50, 100]
- `factor_aversion_riesgo`: [1.0, 5.0]
- `max_drawdown_permitido`: [0.15, 0.3]
- `factor_escala_recompensa`: [50.0, 200.0]
- `peso_retorno_base`: [0.5, 2.0]
- `peso_temporal`: [0.1, 0.5]
- `peso_gestion`: [0.05, 0.4]
- `peso_drawdown`: [0.05, 0.3]
- Y más umbrales de recompensa...

### Arquitectura de Red
- `n_layers`: [2, 3]
- `layer_size`: [128, 256, 512]
- `log_std_init`: [-4.0, -2.0]
- `n_critics`: [2, 3]

## 📁 Estructura de Salida

```
optimizaciones/
└── optimization_20251007_150000/
    ├── optimization.log                    # Log completo del proceso
    ├── best_params.yaml                    # ⭐ MEJORES PARÁMETROS ENCONTRADOS
    ├── optimization_study.pkl              # Estudio completo (para análisis)
    └── visualizations/
        ├── optimization_history.html       # Evolución del Sortino Ratio
        ├── param_importances.html          # Importancia de cada parámetro
        ├── slice_plot.html                 # Efecto individual de parámetros
        └── parallel_coordinate.html        # Relaciones entre parámetros
```

## 📄 Formato de `best_params.yaml`

```yaml
optimization_metadata:
  study_name: trading_optimization_20251007_150000
  n_trials: 50
  best_trial: 34
  optimization_date: '2025-10-07T15:30:45'
  train_period: 2024-01-01 to 2024-02-01
  eval_period: 2024-02-02 to 2024-03-01
  timesteps_per_trial: 5000

best_metrics:
  sortino_ratio: 2.456      # ⭐ MÉTRICA PRINCIPAL
  sharpe_ratio: 1.892
  total_return: 0.234       # 23.4% retorno
  max_drawdown: 0.089       # 8.9% drawdown máximo
  final_equity: 12340.0

best_params:
  learning_rate: 0.0003456
  batch_size: 256
  gamma: 0.985
  tau: 0.0075
  ent_coef_target: 0.15
  window_size: 50
  factor_aversion_riesgo: 2.3
  # ... resto de parámetros optimizados

all_trials_summary:
  total: 50
  completed: 48
  pruned: 2
  failed: 0
```

## 🔄 Flujo de Trabajo Recomendado

### 1. Optimización Rápida (Exploración)
```bash
# 30-50 trials, 5k timesteps (2-3 horas)
python hyperparameter_tuning.py \
    --symbol BTCUSDT --interval 1h \
    --train-start-date 2024-01-01 --train-end-date 2024-02-01 \
    --eval-start-date 2024-02-02 --eval-end-date 2024-03-01 \
    --n-trials 30 --timesteps-per-trial 5000
```

### 2. Revisar Resultados
```bash
# Ver mejores parámetros
cat optimizaciones/optimization_*/best_params.yaml

# Abrir visualizaciones interactivas
firefox optimizaciones/optimization_*/visualizations/*.html
```

### 3. Optimización Refinada (Explotación)
```bash
# 100-200 trials, 10k timesteps (1-2 días)
python hyperparameter_tuning.py \
    --symbol BTCUSDT --interval 1h \
    --train-start-date 2024-01-01 --train-end-date 2024-03-01 \
    --eval-start-date 2024-03-02 --eval-end-date 2024-04-01 \
    --n-trials 150 --timesteps-per-trial 10000
```

### 4. Entrenar Modelo Final
```bash
# Usar los mejores parámetros encontrados (actualizar config.yaml)
# Luego entrenar con más timesteps (50k-100k)
python train.py \
    --symbol BTCUSDT --interval 1h \
    --train-start-date 2024-01-01 --train-end-date 2024-06-01 \
    --eval-start-date 2024-06-02 --eval-end-date 2024-07-01 \
    --total-timesteps 100000
```

## 🎓 Interpretación de Resultados

### Sortino Ratio
- **< 0**: Estrategia perdedora
- **0 - 1**: Débil (ajuste necesario)
- **1 - 2**: Aceptable
- **2 - 3**: Bueno ⭐
- **> 3**: Excelente ⭐⭐⭐

### Importancia de Parámetros
El gráfico `param_importances.html` muestra qué parámetros tienen más impacto:
- **Alta importancia**: Ajustar con cuidado
- **Baja importancia**: Menos críticos, pueden usar valores por defecto

### Slice Plot
Muestra el efecto individual de cada parámetro:
- Identificar rangos óptimos
- Detectar relaciones no lineales

## 💡 Tips y Mejores Prácticas

### ⚡ Para Rapidez
- Usar `--timesteps-per-trial 5000` (inicial)
- Empezar con `--n-trials 30-50`
- Desactivar optimización de portafolio (ya está en False por defecto)

### 🎯 Para Precisión
- Usar `--timesteps-per-trial 10000` o más
- Aumentar a `--n-trials 100-200`
- Validar en múltiples períodos

### 🔧 Troubleshooting

**Error de memoria:**
```bash
# Reducir timesteps o batch_size máximo
# Editar ranges.py y limitar batch_size a [64, 128, 256]
```

**Trials muy lentos:**
```bash
# Reducir timesteps-per-trial
--timesteps-per-trial 3000
```

**Todos los trials fallan:**
```bash
# Revisar optimization.log
# Verificar que los datos se descarguen correctamente
# Probar primero con train.py para validar configuración base
```

## 📈 Métricas Calculadas

Para cada trial se calculan:

1. **Sortino Ratio** ⭐ (métrica principal de optimización)
2. **Sharpe Ratio** (para comparación)
3. **Total Return** (retorno porcentual)
4. **Max Drawdown** (máxima caída desde pico)
5. **Final Equity** (capital final)

## 🔬 Estudios Persistentes (Opcional)

Para estudios que persistan entre ejecuciones:

```bash
# Crear base de datos SQLite
python hyperparameter_tuning.py \
    --storage sqlite:///optuna_trading.db \
    --study-name btc_1h_optimization \
    --n-trials 50

# Continuar el mismo estudio más tarde
python hyperparameter_tuning.py \
    --storage sqlite:///optuna_trading.db \
    --study-name btc_1h_optimization \
    --n-trials 50  # Se agregarán 50 trials más
```

## 🎯 Próximos Pasos

1. **Ejecutar optimización inicial** (30-50 trials)
2. **Analizar visualizaciones** para entender qué parámetros importan
3. **Refinar rangos** si es necesario (editar `src/train/optimization/ranges.py`)
4. **Ejecutar optimización final** (100-200 trials)
5. **Actualizar `config.yaml`** con mejores parámetros
6. **Entrenar modelo final** con `train.py` usando más timesteps

## 📚 Referencias

- [Optuna Documentation](https://optuna.readthedocs.io/)
- [Sortino Ratio Explained](https://www.investopedia.com/terms/s/sortinoratio.asp)
- [Stable-Baselines3 SAC](https://stable-baselines3.readthedocs.io/en/master/modules/sac.html)

---

**¿Necesitas ayuda?** Revisa `optimization.log` en el directorio de salida para diagnóstico detallado.
