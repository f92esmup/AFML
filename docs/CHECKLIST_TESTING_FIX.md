# 🧪 CHECKLIST DE TESTING - Fix Cierre de Posiciones

**Versión:** 1.0  
**Fecha:** 8 de octubre de 2025  
**Ambiente:** TESTNET (OBLIGATORIO)  
**Archivo modificado:** `live.py`

---

## ⚠️ ANTES DE EMPEZAR

- [ ] Confirmar que estás en **TESTNET** (no producción real)
- [ ] Verificar que `live.py` tiene el código nuevo
- [ ] Hacer backup de logs anteriores
- [ ] Tener el documento `FIX_BUG_CIERRE_POSICIONES.md` a mano para referencia

---

## 🎯 Objetivo del Testing

Verificar que:
1. ✅ Los cierres de posición funcionan correctamente (incluso con balance bajo)
2. ✅ Las aperturas y aumentos siguen funcionando igual que antes
3. ✅ La interpretación de acciones NO cambió
4. ✅ Los logs son claros e informativos

---

## 📋 TEST SUITE

### CATEGORÍA A: Operaciones de Cierre (LO QUE SE CORRIGIÓ)

#### Test A1: Cerrar SHORT con Balance Parcialmente Comprometido
**Objetivo:** Verificar que se puede cerrar aunque balance_disponible < equity

**Setup:**
- [ ] Abrir una posición SHORT
- [ ] Esperar a que haya PnL no realizado (positivo o negativo)
- [ ] Verificar que: `balance_disponible < equity_total`

**Acción:**
- [ ] Dejar que el agente decida cerrar la posición SHORT

**Verificación en logs:**
```log
# DEBE aparecer:
🔄 Cerrando posición SHORT: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: cerrar_short | Cantidad: [cantidad] | Trade ID: [id]

# NO DEBE aparecer:
❌ Operación FALLÓ: cerrar_short | Error: Cantidad calculada es 0
⚠️ Balance insuficiente para ejecutar la operación
```

**Resultado esperado:** ✅ POSICIÓN CERRADA EXITOSAMENTE

---

#### Test A2: Cerrar LONG con Balance Parcialmente Comprometido
**Objetivo:** Mismo test pero con posición LONG

**Setup:**
- [ ] Abrir una posición LONG
- [ ] Esperar a que haya PnL no realizado
- [ ] Verificar que: `balance_disponible < equity_total`

**Acción:**
- [ ] Dejar que el agente decida cerrar la posición LONG

**Verificación en logs:**
```log
# DEBE aparecer:
🔄 Cerrando posición LONG: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: cerrar_long | Cantidad: [cantidad] | Trade ID: [id]
```

**Resultado esperado:** ✅ POSICIÓN CERRADA EXITOSAMENTE

---

#### Test A3: Intentar Cerrar sin Posición Abierta
**Objetivo:** Verificar validación de existencia de posición

**Setup:**
- [ ] Asegurarse de que NO hay posición abierta

**Acción:**
- [ ] Forzar (si es posible) o esperar a que el agente intente cerrar

**Verificación en logs:**
```log
# DEBE aparecer:
⚠️ No hay posición abierta para cerrar
❌ Operación FALLÓ: cerrar_[long/short] | Error: No hay posición abierta para cerrar
```

**Resultado esperado:** ⚠️ ERROR APROPIADO (no crash)

---

### CATEGORÍA B: Operaciones de Apertura (NO DEBE CAMBIAR)

#### Test B1: Abrir LONG con Balance Suficiente
**Objetivo:** Verificar que abrir sigue funcionando igual

**Setup:**
- [ ] NO tener posición abierta
- [ ] Tener balance suficiente

**Acción:**
- [ ] Dejar que el agente decida abrir LONG

**Verificación en logs:**
```log
# DEBE aparecer:
🆕 Abriendo posición LONG: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: abrir_long | Cantidad: [cantidad] | Trade ID: [id]
```

**Resultado esperado:** ✅ POSICIÓN ABIERTA (comportamiento SIN CAMBIOS)

---

#### Test B2: Abrir SHORT con Balance Suficiente
**Objetivo:** Verificar que abrir SHORT sigue funcionando

**Setup:**
- [ ] NO tener posición abierta
- [ ] Tener balance suficiente

**Acción:**
- [ ] Dejar que el agente decida abrir SHORT

**Verificación en logs:**
```log
# DEBE aparecer:
🆕 Abriendo posición SHORT: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: abrir_short | Cantidad: [cantidad] | Trade ID: [id]
```

**Resultado esperado:** ✅ POSICIÓN ABIERTA (comportamiento SIN CAMBIOS)

---

#### Test B3: Intentar Abrir con Balance Insuficiente
**Objetivo:** Verificar que la validación de margen sigue funcionando

**Setup:**
- [ ] Reducir balance testnet a cantidad muy pequeña
- [ ] NO tener posición abierta

**Acción:**
- [ ] Esperar a que el agente intente abrir una posición

**Verificación en logs:**
```log
# DEBE aparecer:
⚠️ Balance insuficiente para ejecutar la operación
⚠️ No se puede ejecutar [operacion]: balance insuficiente para margen requerido
❌ Operación FALLÓ: [operacion] | Error: Cantidad calculada es 0 - Balance insuficiente para margen requerido
```

**Resultado esperado:** ⚠️ ERROR APROPIADO (comportamiento SIN CAMBIOS)

---

### CATEGORÍA C: Operaciones de Aumento (NO DEBE CAMBIAR)

#### Test C1: Aumentar LONG Existente
**Objetivo:** Verificar que aumentar sigue funcionando

**Setup:**
- [ ] Tener posición LONG abierta
- [ ] Tener balance suficiente para aumentar

**Acción:**
- [ ] Dejar que el agente decida aumentar LONG

**Verificación en logs:**
```log
# DEBE aparecer:
📈 Aumentando posición LONG: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: aumentar_long | Cantidad: [cantidad] | Trade ID: [id]
```

**Resultado esperado:** ✅ POSICIÓN AUMENTADA (comportamiento SIN CAMBIOS)

---

#### Test C2: Aumentar SHORT Existente
**Objetivo:** Verificar que aumentar SHORT sigue funcionando

**Setup:**
- [ ] Tener posición SHORT abierta
- [ ] Tener balance suficiente para aumentar

**Acción:**
- [ ] Dejar que el agente decida aumentar SHORT

**Verificación en logs:**
```log
# DEBE aparecer:
📉 Aumentando posición SHORT: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: aumentar_short | Cantidad: [cantidad] | Trade ID: [id]
```

**Resultado esperado:** ✅ POSICIÓN AUMENTADA (comportamiento SIN CAMBIOS)

---

### CATEGORÍA D: Interpretación de Acciones (CRÍTICO - NO DEBE CAMBIAR)

#### Test D1: Verificar Umbral de Mantener
**Objetivo:** Confirmar que el umbral de mantener sigue igual

**Acción:**
- [ ] Observar logs durante 10-20 pasos

**Verificación en logs:**
```log
# Cuando acción está cerca de 0, DEBE aparecer:
🤖 Acción del agente: [valor cercano a 0] → mantener
```

**Resultado esperado:** ✅ Mantener se activa apropiadamente

---

#### Test D2: Verificar Transición LONG → SHORT
**Objetivo:** Confirmar que cambiar de LONG a SHORT solo cierra (no reabre)

**Setup:**
- [ ] Tener posición LONG abierta

**Acción:**
- [ ] Esperar a que el agente genere acción negativa fuerte (< -umbral)

**Verificación en logs:**
```log
# DEBE aparecer (solo cierre, NO apertura):
🤖 Acción del agente: [valor negativo] → cerrar_long
🔄 Cerrando posición LONG: [cantidad] unidades @ $[precio]

# NO DEBE aparecer (no reabre en mismo paso):
🆕 Abriendo posición SHORT
```

**Resultado esperado:** ✅ Solo cierra, no reabre (comportamiento SIN CAMBIOS)

---

#### Test D3: Verificar Transición SHORT → LONG
**Objetivo:** Confirmar que cambiar de SHORT a LONG solo cierra (no reabre)

**Setup:**
- [ ] Tener posición SHORT abierta

**Acción:**
- [ ] Esperar a que el agente genere acción positiva fuerte (> umbral)

**Verificación en logs:**
```log
# DEBE aparecer (solo cierre, NO apertura):
🤖 Acción del agente: [valor positivo] → cerrar_short
🔄 Cerrando posición SHORT: [cantidad] unidades @ $[precio]

# NO DEBE aparecer (no reabre en mismo paso):
🆕 Abriendo posición LONG
```

**Resultado esperado:** ✅ Solo cierra, no reabre (comportamiento SIN CAMBIOS)

---

## 📊 CRITERIOS DE ÉXITO

### ✅ Tests que DEBEN pasar:
- [ ] A1: Cerrar SHORT con balance parcial → EXITOSO
- [ ] A2: Cerrar LONG con balance parcial → EXITOSO
- [ ] A3: Cerrar sin posición → ERROR APROPIADO
- [ ] B1: Abrir LONG → EXITOSO
- [ ] B2: Abrir SHORT → EXITOSO
- [ ] B3: Abrir sin balance → ERROR APROPIADO
- [ ] C1: Aumentar LONG → EXITOSO
- [ ] C2: Aumentar SHORT → EXITOSO
- [ ] D1: Umbral mantener → CORRECTO
- [ ] D2: Transición LONG→SHORT → SOLO CIERRA
- [ ] D3: Transición SHORT→LONG → SOLO CIERRA

### ❌ Red Flags (DETENER testing si aparecen):
- [ ] Crash del sistema
- [ ] Loops infinitos
- [ ] Cambio en interpretación de acciones
- [ ] Operaciones inesperadas ejecutadas
- [ ] Pérdida total de balance testnet por bug

---

## 🔍 Monitoreo Durante Testing

### Variables a Observar en Logs:

```log
# En cada paso, verificar:
💰 Equity: [valor] | Drawdown: [%] | Posición: [True/False]

# En cada operación, verificar:
🤖 Acción del agente: [valor] → [operación_interpretada]
[Emoji] [Descripción de operación]: [cantidad] unidades @ $[precio]
✅ Operación ejecutada: [operación] | Cantidad: [cantidad] | Trade ID: [id]
```

### Métricas a Recolectar:

- [ ] Número total de operaciones ejecutadas: _____
- [ ] Número de cierres exitosos: _____
- [ ] Número de aperturas exitosas: _____
- [ ] Número de aumentos exitosos: _____
- [ ] Número de errores (con razón): _____
- [ ] Número de crashes: _____ (DEBE SER 0)

---

## 📝 REPORTE POST-TESTING

### Resumen de Resultados:

```
Fecha de testing: __________
Duración del test: __________ horas
Número de pasos ejecutados: __________

CATEGORÍA A (Cierres):
- A1: [ PASS / FAIL ]
- A2: [ PASS / FAIL ]
- A3: [ PASS / FAIL ]

CATEGORÍA B (Aperturas):
- B1: [ PASS / FAIL ]
- B2: [ PASS / FAIL ]
- B3: [ PASS / FAIL ]

CATEGORÍA C (Aumentos):
- C1: [ PASS / FAIL ]
- C2: [ PASS / FAIL ]

CATEGORÍA D (Interpretación):
- D1: [ PASS / FAIL ]
- D2: [ PASS / FAIL ]
- D3: [ PASS / FAIL ]

CONCLUSIÓN: [ APROBADO / REQUIERE AJUSTES ]
```

### Problemas Encontrados:

```
1. [Descripción del problema]
   - Severidad: [ CRÍTICO / ALTO / MEDIO / BAJO ]
   - Pasos para reproducir: ...
   - Log relevante: ...

2. ...
```

### Decisión Final:

- [ ] ✅ APROBADO para producción real
- [ ] ⚠️ APROBADO con observaciones (detallar)
- [ ] ❌ RECHAZADO - requiere más trabajo (detallar)

---

## 🚀 SIGUIENTE PASO

Si todos los tests pasan:
1. [ ] Documentar resultados en este checklist
2. [ ] Guardar logs completos del testing
3. [ ] Hacer commit del código con mensaje descriptivo
4. [ ] Preparar para despliegue en producción real

Si hay fallos:
1. [ ] Documentar todos los problemas encontrados
2. [ ] Adjuntar logs relevantes
3. [ ] Reportar a desarrollador
4. [ ] NO desplegar en producción

---

**Tester:** ___________________  
**Firma:** ___________________  
**Fecha:** ___________________
