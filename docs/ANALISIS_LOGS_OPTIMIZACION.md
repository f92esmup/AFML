# 🔍 ANÁLISIS DE LOGS - SISTEMA DE OPTIMIZACIÓN

**Fecha del análisis:** 2025-10-07  
**Optimización analizada:** `optimization_20251007_112003`  
**Total de trials:** 10  
**Timesteps por trial:** 5000  

---

## 🚨 PROBLEMAS CRÍTICOS DETECTADOS

### **1. SORTINO RATIO = 100.0 CUANDO NO HAY OPERACIONES**

**Severidad:** 🔴 **CRÍTICA**

**Descripción:**
```
Trial 1: Sortino = 100.0, Total Return = 0.00%, Num Trades = 0
Trial 2: Sortino = 100.0, Total Return = 0.00%, Num Trades = 0  
Trial 5: Sortino = 100.0, Total Return = 0.00%, Num Trades = 0
```

**Causa raíz:**
```python
# src/train/optimization/metrics.py (ANTES DEL FIX)
if len(downside_returns) == 0:
    return 100.0  # ❌ Se activa cuando NO OPERA (equity constante)
```

**Impacto:**
- Optuna selecciona parámetros que NO OPERAN como "óptimos"
- El agente aprende a NO HACER NADA (inacción total)
- La optimización converge a estrategias inútiles

**Solución aplicada:**
```python
# Detectar equity constante ANTES de calcular downside
if np.std(returns) == 0:
    log.warning("Equity constante - Agente no opera. Penalizando con Sortino = 0.0")
    return 0.0
```

**Estado:** ✅ CORREGIDO (pendiente de validar con nueva optimización)

---

### **2. EPISODIOS TERMINADOS POR MAX DRAWDOWN EXCESIVAMENTE**

**Severidad:** 🟡 **ALTA**

**Evidencia:**
```
2025-10-07 11:20:10 - WARNING - Episodio terminado por max drawdown: 0.2202
2025-10-07 11:20:10 - WARNING - Episodio terminado por max drawdown: 0.1940
2025-10-07 11:20:10 - WARNING - Episodio terminado por max drawdown: 0.3309
... (repetido ~200 veces en 3 segundos)
```

**Análisis:**
- **Frecuencia:** ~66 terminaciones por drawdown por segundo
- **Timesteps:** 5000 totales → ~75 episodios en 3 segundos
- **Promedio de vida:** ~66 steps por episodio
- **Max DD alcanzado:** 15%-39% (rango)

**Causas posibles:**
1. **`max_drawdown_permitido` muy conservador** (actual: 0.10-0.25)
2. **Agente inexperto** (primeros timesteps de entrenamiento)
3. **Entorno volátil** (período de datos con alta volatilidad)
4. **Learning starts alto** (7000) → No aprende antes de operar

**Implicaciones:**
- ✅ **Positivo:** Protección contra ruina funciona
- ❌ **Negativo:** Episodios muy cortos → Poco aprendizaje
- ❌ **Negativo:** Agente no explora suficiente antes de morir

**Recomendaciones:**
```yaml
# Ajustar en ranges.py
'max_drawdown_permitido': trial.suggest_float('max_drawdown_permitido', 0.20, 0.40)  # Más permisivo

# O reducir learning_starts
'learning_starts': trial.suggest_int('learning_starts', 1000, 5000)  # Aprende antes
```

**Estado:** ⚠️ REQUIERE AJUSTE (no crítico, pero subóptimo)

---

### **3. AGENTE NO OPERA (0 TRADES) EN EVALUACIÓN**

**Severidad:** 🟠 **MEDIA**

**Evidencia:**
```
Trial 0: Num Trades = 0, Win Rate = 0.00%
Trial 1: Num Trades = 0, Win Rate = 0.00%
Trial 2: Num Trades = 0, Win Rate = 0.00%
Trial 3: Num Trades = 0, Win Rate = 0.00%
```

**Posibles causas:**
1. **Entrenamiento insuficiente** (5000 timesteps es muy poco)
2. **Learning starts muy alto** (6000-7000) → No aprende en 5000 steps
3. **Exploración insuficiente** (ent_coef muy bajo)
4. **Penalizaciones demasiado fuertes** en función de recompensa

**Análisis detallado:**
```python
# Trial con learning_starts=7000 y timesteps=5000
# → El agente NUNCA empieza a entrenar la red
# → Solo recopila experiencias en buffer
# → En evaluación usa red sin entrenar (randomness)
```

**Recomendaciones:**
```python
# SOLUCIÓN 1: Reducir learning_starts
'learning_starts': trial.suggest_int('learning_starts', 500, 2000)

# SOLUCIÓN 2: Aumentar timesteps por trial
--timesteps-per-trial 10000  # En vez de 5000

# SOLUCIÓN 3: Validar que learning_starts < timesteps
if learning_starts >= timesteps_per_trial:
    learning_starts = int(timesteps_per_trial * 0.3)  # 30% del total
```

**Estado:** 🔴 CRÍTICO (afecta viabilidad de optimización)

---

### **4. TRIAL 0 CON RETORNO POSITIVO PERO 0 TRADES**

**Severidad:** 🟡 **ALTA** (inconsistencia lógica)

**Evidencia:**
```
Trial 0:
  Total Return:   20.90%
  Final Equity:   $12090.37
  Num Trades:     0
  Win Rate:       0.00%
```

**¿Cómo es posible ganar 20.9% sin operar?**

**Hipótesis:**
1. **Bug en cálculo de trades** (no cuenta correctamente)
2. **Posición abierta sin cerrar** (no cuenta como trade completado)
3. **Equity != capital real** (confusión en métricas)

**Necesita investigación:**
```python
# Revisar en src/train/Entrenamiento/entorno/portafolio.py
# Método para contar trades completados
def _registrar_cierre_posicion(self):
    # ¿Se incrementa self.num_trades aquí?
```

**Estado:** 🔍 REQUIERE INVESTIGACIÓN

---

## 📊 MÉTRICAS AGREGADAS DE LOS TRIALS

| Trial | Sortino | Total Return | Max DD | Trades | Status |
|-------|---------|--------------|--------|--------|--------|
| 0     | 12.84   | +20.90%     | 23.74% | 0      | ⚠️ Inconsistente |
| 1     | 100.00  | 0.00%       | 0.00%  | 0      | ❌ No opera |
| 2     | 100.00  | 0.00%       | 0.00%  | 0      | ❌ No opera |
| 3     | -5.72   | -8.73%      | ?      | 0      | ❌ Pérdida |
| 4     | ?       | ?           | ?      | 0      | ⚠️ Datos faltantes |
| 5     | 100.00  | 0.00%       | 0.00%  | 0      | ❌ No opera |

**Estadísticas:**
- **Trials sin operar:** 4/6 (66.67%) 🔴
- **Trials con Sortino=100:** 3/6 (50%) 🔴
- **Trials rentables:** 1/6 (16.67%) 🟡
- **Promedio Sortino (excluyendo 100):** 3.56
- **Promedio Return:** +2.04%

---

## ⚙️ PROBLEMAS DE CONFIGURACIÓN

### **A. Learning Starts vs Timesteps**

```python
# Trials con problemas:
Trial 1: learning_starts=6000, timesteps=5000  # ❌ Nunca entrena
Trial 2: learning_starts=7000, timesteps=5000  # ❌ Nunca entrena

# El agente necesita learning_starts < timesteps para aprender
```

**Fix recomendado:**
```python
# En tuner.py, añadir validación:
if suggested_params['learning_starts'] >= self.timesteps_per_trial:
    suggested_params['learning_starts'] = int(self.timesteps_per_trial * 0.5)
    log.warning(f"learning_starts ajustado a {suggested_params['learning_starts']}")
```

---

### **B. Window Size vs Datos Disponibles**

```
Datos evaluación: 522 registros
Window size sugerido: 20-100
Episodios máximos: 522 - 100 = 422 steps
```

✅ **OK:** Suficiente para evaluar

---

### **C. Arquitecturas de Red Muy Profundas**

```python
Trial 1: n_layers=10  # [128, 128, 128, 256, 128, 256, 128, 256, 128, 128]
# ¿Es necesario 10 capas para trading?
```

**Recomendación:** Limitar a 2-4 capas:
```python
'n_layers': trial.suggest_int('n_layers', 2, 4)  # En vez de 2-10
```

---

## 🎯 RECOMENDACIONES PRIORITARIAS

### **1. CRÍTICO - Arreglar Sortino cuando no opera** ✅ YA HECHO

```python
# Aplicado en metrics.py
if np.std(returns) == 0:
    return 0.0  # Penalizar inacción
```

---

### **2. CRÍTICO - Validar learning_starts < timesteps**

```python
# Añadir en tuner.py
def _validate_trial_params(self, params: Dict) -> Dict:
    if params.get('learning_starts', 0) >= self.timesteps_per_trial:
        params['learning_starts'] = max(1000, int(self.timesteps_per_trial * 0.3))
        log.warning(f"learning_starts reducido a {params['learning_starts']}")
    return params
```

---

### **3. ALTO - Aumentar timesteps mínimos por trial**

```bash
# Mínimo recomendado: 10,000 timesteps
python3 hyperparameter_tuning.py ... --timesteps-per-trial 10000
```

---

### **4. MEDIO - Reducir rango de learning_starts**

```python
# ranges.py
'learning_starts': trial.suggest_int('learning_starts', 500, 3000, step=500)
# En vez de: 1000-10000
```

---

### **5. MEDIO - Investigar bug de conteo de trades**

Ver `src/train/Entrenamiento/entorno/portafolio.py` línea donde se incrementa `num_trades`.

---

## 📈 PRÓXIMOS PASOS

1. ✅ **Aplicar fix de Sortino=100** (HECHO)
2. ⏳ **Ejecutar nueva optimización de prueba** (2-3 trials, 10k timesteps)
3. ⏳ **Validar que Sortino=0 cuando no opera**
4. ⏳ **Implementar validación de learning_starts**
5. ⏳ **Crear tests automáticos** (siguiente paso)
6. ⏳ **Optimización completa con fixes** (50+ trials)

---

## 🧪 TESTS NECESARIOS

1. **Test de métricas con equity constante** → Sortino = 0
2. **Test de métricas con solo ganancias** → Sortino > 0
3. **Test de validación de parámetros** (learning_starts < timesteps)
4. **Test de conteo de trades** (verificar inconsistencia)
5. **Test de integración completa** (trial end-to-end)

---

**Generado por:** Análisis automático de logs  
**Próxima acción:** Crear suite de tests
