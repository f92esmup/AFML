# 🚀 Configuración del Entorno de Producción

Este documento explica cómo configurar el entorno necesario para ejecutar el sistema de trading en producción (`live.py`).

## 📋 Requisitos Previos

1. **Ambiente Python configurado** (conda o venv)
2. **Dependencias instaladas** (ver `environment.yml`)
3. **Cuenta en Binance Futures** (Testnet o Real)

---

## 🔧 Configuración Paso a Paso

### 1. Obtener Credenciales de Binance

#### Opción A: Testnet (Recomendado para pruebas)

1. Visita: https://testnet.binancefuture.com/
2. Inicia sesión con tu cuenta de GitHub o Google
3. Ve a **API Keys** en el menú
4. Crea una nueva API Key:
   - ✅ Enable Futures
   - ✅ Enable Reading
   - ⚠️ NO habilites "Enable Withdrawals" (no necesario)
5. Copia tu **API Key** y **API Secret**
6. Obtén fondos de prueba gratis desde el faucet de testnet

#### Opción B: Producción Real (⚠️ Usar con precaución)

1. Visita: https://www.binance.com/es/my/settings/api-management
2. Crea una nueva API Key
3. Configuración de seguridad recomendada:
   - ✅ Enable Futures
   - ✅ Enable Reading
   - ⚠️ **NO** habilites "Enable Withdrawals" a menos que sea absolutamente necesario
   - ✅ Configura **restricción de IP** si es posible
   - ✅ Usa autenticación de dos factores (2FA)
4. Copia tu **API Key** y **API Secret**

---

### 2. Configurar Variables de Entorno

#### A. Copiar el archivo de ejemplo

```bash
cp .env.example .env
```

#### B. Editar el archivo `.env`

Abre el archivo `.env` con tu editor favorito:

```bash
nano .env
# o
code .env
```

#### C. Añadir tus credenciales

**Para Testnet:**
```bash
BINANCE_TESTNET_API_KEY=tu_api_key_de_testnet_aqui
BINANCE_TESTNET_API_SECRET=tu_api_secret_de_testnet_aqui
```

**Para Producción Real:**
```bash
BINANCE_API_KEY=tu_api_key_real_aqui
BINANCE_API_SECRET=tu_api_secret_real_aqui
```

⚠️ **IMPORTANTE**: 
- Nunca compartas tus API Keys
- Nunca subas el archivo `.env` a GitHub (ya está en `.gitignore`)
- Usa API Keys diferentes para cada bot/proyecto

---

### 3. Verificar la Instalación

```bash
# Verificar que python-dotenv está instalado
pip list | grep python-dotenv

# Si no está instalado:
pip install python-dotenv
```

---

## 🎯 Ejecutar el Sistema

### Modo Testnet (Recomendado para pruebas)

```bash
python live.py --train-id <nombre_del_entrenamiento>
```

Por ejemplo:
```bash
python live.py --train-id train_BTCUSDT_20250101_20250601_lr3e-4_bs256_ws30_20251004_190526
```

### Modo Producción Real (⚠️ Dinero real en riesgo)

```bash
python live.py --train-id <nombre_del_entrenamiento> --live
```

⚠️ **ADVERTENCIA**: El flag `--live` opera con dinero real. Asegúrate de:
- Haber probado exhaustivamente en testnet
- Entender completamente los riesgos
- Monitorear constantemente el sistema
- Empezar con cantidades pequeñas

---

## 🔍 Verificación de Configuración

Para verificar que todo está configurado correctamente:

```bash
# Verificar que las variables de entorno se cargan
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key cargada:', bool(os.getenv('BINANCE_TESTNET_API_KEY')))"
```

Debería mostrar: `API Key cargada: True`

---

## 🛡️ Seguridad

### ✅ Mejores Prácticas

1. **Usa Testnet primero**: Siempre prueba en testnet antes de ir a producción
2. **Restricción de IP**: Configura IP whitelisting en Binance si es posible
3. **Permisos mínimos**: Solo habilita los permisos necesarios
4. **API Keys únicas**: Usa una API Key diferente para cada bot
5. **Monitoreo**: Mantén logs y monitorea constantemente
6. **Stop Loss**: Asegúrate de que el control de riesgo está activo

### ❌ NO Hacer

1. NO subas `.env` a GitHub
2. NO compartas tus API Keys
3. NO habilites "Enable Withdrawals" a menos que sea necesario
4. NO uses la misma API Key en múltiples bots
5. NO ejecutes en producción sin haber probado en testnet

---

## 📊 Estructura de Archivos

```
AFML/
├── .env                    # ⚠️ TUS CREDENCIALES (no subir a git)
├── .env.example           # ✅ Plantilla (subir a git)
├── live.py                # Script principal de producción
└── entrenamientos/        # Modelos entrenados
    └── train_XXXX/
        ├── config_metadata.yaml
        ├── scaler_train.pkl
        └── modelos/
            └── modelo.zip
```

---

## 🆘 Solución de Problemas

### Error: "Credenciales de Binance no encontradas"

**Causa**: El archivo `.env` no existe o las variables no están definidas.

**Solución**:
1. Verifica que el archivo `.env` existe: `ls -la .env`
2. Verifica que contiene las credenciales: `cat .env` (sin compartir la salida)
3. Verifica que no hay espacios extra en las variables

### Error: "Invalid API-key, IP, or permissions for action"

**Causa**: Credenciales incorrectas o permisos insuficientes.

**Solución**:
1. Verifica que copiaste correctamente la API Key y Secret
2. Verifica que habilitaste "Enable Futures" en Binance
3. Si usas restricción de IP, verifica tu IP pública actual

### Error: "ModuleNotFoundError: No module named 'dotenv'"

**Causa**: El paquete `python-dotenv` no está instalado.

**Solución**:
```bash
pip install python-dotenv
```

---

## 📝 Notas Adicionales

- Las credenciales se cargan automáticamente al iniciar `live.py`
- El archivo `.env` está protegido en `.gitignore`
- Puedes tener credenciales de testnet Y producción al mismo tiempo
- El modo se selecciona con el flag `--live` al ejecutar el script

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs del sistema
2. Verifica la documentación de Binance API
3. Asegúrate de que el modelo entrenado existe y es válido
4. Verifica que `config_metadata.yaml` contiene todos los parámetros necesarios

---

**¡Feliz trading! 📈**

*Recuerda: El trading conlleva riesgos. Solo invierte lo que puedes permitirte perder.*
