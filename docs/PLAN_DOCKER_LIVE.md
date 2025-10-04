# Plan de Implementación - Dockerfile Live (Modo Producción)

## 📋 Resumen Ejecutivo

Este documento describe el proceso completo para construir, configurar y ejecutar el contenedor Docker del sistema de trading AFML en modo **LIVE** (producción) o **TESTNET** (pruebas).

---

## 🎯 Objetivos

1. Crear un contenedor Docker aislado para ejecutar el sistema de trading en producción
2. Garantizar que todas las dependencias estén correctamente instaladas
3. Proporcionar un método seguro para gestionar credenciales de API
4. Facilitar el despliegue en diferentes entornos (local, servidor, cloud)

---

## 📦 Prerrequisitos

### Software Requerido

- **Docker** >= 20.10
- **Docker Compose** >= 2.0 (opcional, pero recomendado)
- **Git** (para clonar el repositorio)

### Recursos Mínimos Recomendados

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disco**: 10 GB libres
- **Red**: Conexión estable a Internet

### Datos Necesarios

1. **Modelo entrenado** ubicado en `entrenamientos/<train_id>/modelos/modelo.zip`
2. **Scaler** ubicado en `entrenamientos/<train_id>/scaler_eval.pkl`
3. **Credenciales de Binance**:
   - API Key
   - API Secret
   - Para TESTNET o LIVE según el modo

---

## 🔧 Configuración Inicial

### 1. Preparar Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto con las credenciales:

```bash
# Credenciales para TESTNET (pruebas)
BINANCE_TESTNET_API_KEY=tu_api_key_testnet
BINANCE_TESTNET_API_SECRET=tu_api_secret_testnet

# Credenciales para LIVE (producción real) - ⚠️ USAR CON PRECAUCIÓN
BINANCE_API_KEY=tu_api_key_live
BINANCE_API_SECRET=tu_api_secret_live
```

**⚠️ IMPORTANTE**: 
- Nunca commitear el archivo `.env` al repositorio
- Asegurarse de que `.env` esté en `.gitignore`
- Usar credenciales de TESTNET para pruebas iniciales

### 2. Verificar Estructura del Proyecto

Asegurarse de que existe el directorio de entrenamiento:

```bash
ls entrenamientos/<TRAIN_ID>/
# Debe contener:
#   - config_metadata.yaml
#   - scaler_eval.pkl
#   - modelos/modelo.zip
```

---

## 🏗️ Construcción del Contenedor

### Paso 1: Construir la Imagen Docker

```bash
# Construcción básica
docker build -f Dockerfile.live -t afml-live:latest .

# Construcción con caché limpio (si hay problemas)
docker build --no-cache -f Dockerfile.live -t afml-live:latest .

# Construcción con etiqueta de versión
docker build -f Dockerfile.live -t afml-live:v1.0.0 .
```

**Tiempo estimado**: 10-15 minutos (primera vez)

**Nota**: El contenedor se ejecuta como usuario **root** para evitar problemas de permisos con volúmenes montados.

### Paso 2: Verificar la Imagen

```bash
# Listar imágenes
docker images | grep afml-live

# Ver detalles de la imagen
docker inspect afml-live:latest

# Verificar tamaño
docker images afml-live:latest --format "{{.Size}}"
```

**Tamaño esperado**: ~5-8 GB

---

## 🚀 Ejecución del Contenedor

### Modo TESTNET (Recomendado para Pruebas)

#### Opción 1: Comando Docker Directo

```bash
docker run -it --rm \
  --name afml-testnet \
  --env-file .env \
  -v $(pwd)/entrenamientos:/app/entrenamientos:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/registros_produccion:/app/registros_produccion \
  afml-live:latest \
  --train-id train_BTCUSDT_20250101_20250601_lr3e-4_bs256_ws30_20251004_190526
```

**Explicación de parámetros**:
- `-it`: Modo interactivo con terminal
- `--rm`: Eliminar contenedor al finalizar
- `--name`: Nombre del contenedor
- `--env-file`: Cargar variables de entorno desde `.env`
- `-v`: Montar volúmenes (modelos, logs, registros)
- `--train-id`: ID del entrenamiento a usar

#### Opción 2: Docker Compose (Recomendado)

Crear archivo `docker-compose.live.yml`:

```yaml
version: '3.8'

services:
  afml-testnet:
    build:
      context: .
      dockerfile: Dockerfile.live
    image: afml-live:latest
    container_name: afml-testnet
    env_file:
      - .env
    volumes:
      - ./entrenamientos:/app/entrenamientos:ro
      - ./logs:/app/logs
      - ./registros_produccion:/app/registros_produccion
    command: >
      --train-id train_BTCUSDT_20250101_20250601_lr3e-4_bs256_ws30_20251004_190526
    restart: unless-stopped
    networks:
      - afml-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  afml-network:
    driver: bridge
```

Ejecutar con:

```bash
# Iniciar en modo testnet
docker-compose -f docker-compose.live.yml up

# Iniciar en background
docker-compose -f docker-compose.live.yml up -d

# Ver logs en tiempo real
docker-compose -f docker-compose.live.yml logs -f

# Detener
docker-compose -f docker-compose.live.yml down
```

### Modo LIVE (Producción Real) ⚠️

**⚠️ ADVERTENCIA**: Esto operará con dinero real. Usar solo después de pruebas exhaustivas en TESTNET.

```bash
docker run -it --rm \
  --name afml-live \
  --env-file .env \
  -v $(pwd)/entrenamientos:/app/entrenamientos:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/registros_produccion:/app/registros_produccion \
  afml-live:latest \
  --train-id train_BTCUSDT_20250101_20250601_lr3e-4_bs256_ws30_20251004_190526 \
  --live
```

**Nota**: El flag `--live` activa el modo producción real.

---

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real

```bash
# Con Docker directo
docker logs -f afml-testnet

# Con Docker Compose
docker-compose -f docker-compose.live.yml logs -f afml-testnet
```

### Acceder a Logs en el Sistema de Archivos

```bash
# Logs del sistema
tail -f logs/AFML_<timestamp>.log

# Registros de producción
ls -lh registros_produccion/
```

### Monitoreo del Estado del Contenedor

```bash
# Estado general
docker ps

# Uso de recursos
docker stats afml-testnet

# Inspeccionar contenedor
docker inspect afml-testnet
```

---

## 🛠️ Gestión del Contenedor

### Detener el Contenedor

```bash
# Detener gracefully (permite limpieza)
docker stop afml-testnet

# Forzar detención (si no responde)
docker kill afml-testnet
```

### Reiniciar el Contenedor

```bash
docker restart afml-testnet
```

### Entrar al Contenedor (Debug)

```bash
# Acceder a shell mientras está corriendo
docker exec -it afml-testnet /bin/bash

# Ejecutar comandos específicos
docker exec afml-testnet conda run -n AFML python -c "import binance; print('OK')"
```

### Limpiar Recursos

```bash
# Eliminar contenedores detenidos
docker container prune

# Eliminar imágenes no usadas
docker image prune

# Limpieza completa (cuidado!)
docker system prune -a
```

---

## 🔒 Consideraciones de Seguridad

### 1. Protección de Credenciales

- ✅ Usar archivo `.env` fuera del repositorio
- ✅ Considerar usar Docker Secrets en producción
- ✅ Rotar API keys regularmente
- ✅ Configurar permisos de solo lectura en API (si es posible)

### 2. Restricciones de API

En Binance, configurar la API key con:
- ✅ Habilitar Trading
- ✅ Restricción por IP (whitelist)
- ❌ NO habilitar retiros
- ❌ NO habilitar margin/futures (si solo se opera spot)

### 3. Límites y Control de Riesgo

Revisar parámetros en `src/produccion/config/config.py`:
- `max_drawdown`: Pérdida máxima permitida
- `max_trade_size`: Tamaño máximo por operación
- `balance_reservado`: Balance a mantener sin operar

---

## 📈 Optimizaciones de Producción

### 1. Reinicio Automático

Para producción real, configurar reinicio automático:

```bash
docker run -d \
  --restart=unless-stopped \
  --name afml-live \
  ...
```

### 2. Límites de Recursos

Limitar uso de CPU y memoria:

```bash
docker run -d \
  --cpus="2" \
  --memory="4g" \
  --name afml-live \
  ...
```

### 3. Rotación de Logs

Configurar en `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

### 4. Health Checks

El contenedor incluye health check automático cada 60 segundos:

```bash
# Ver estado de health
docker inspect --format='{{.State.Health.Status}}' afml-testnet
```

---

## 🐛 Troubleshooting

### Problema: Error al cargar modelo

**Síntoma**: `FileNotFoundError: modelo.zip not found`

**Solución**:
```bash
# Verificar que el volumen esté montado correctamente
docker exec afml-testnet ls -la /app/entrenamientos/<train_id>/modelos/

# Verificar permisos
ls -la entrenamientos/<train_id>/modelos/
```

### Problema: Error de conexión con Binance

**Síntoma**: `Connection refused` o `401 Unauthorized`

**Solución**:
```bash
# Verificar variables de entorno
docker exec afml-testnet env | grep BINANCE

# Probar conexión manualmente
docker exec afml-testnet conda run -n AFML python -c "
from binance import Client
import os
client = Client(os.getenv('BINANCE_TESTNET_API_KEY'), os.getenv('BINANCE_TESTNET_API_SECRET'), testnet=True)
print(client.get_account())
"
```

### Problema: Contenedor se detiene inesperadamente

**Síntoma**: Contenedor en estado `Exited`

**Solución**:
```bash
# Ver logs de salida
docker logs afml-testnet

# Ver código de salida
docker inspect afml-testnet --format='{{.State.ExitCode}}'

# Verificar health check
docker inspect --format='{{json .State.Health}}' afml-testnet | jq
```

### Problema: Alto uso de memoria

**Síntoma**: OOM (Out of Memory) errors

**Solución**:
```bash
# Aumentar límite de memoria
docker update --memory="8g" afml-testnet

# O reconstruir con más recursos
docker run -d --memory="8g" --name afml-testnet ...
```

---

## 📝 Checklist Pre-Producción

Antes de ejecutar en modo LIVE:

- [ ] Probar extensivamente en TESTNET (mínimo 1 semana)
- [ ] Verificar que el modelo funciona correctamente
- [ ] Revisar y ajustar parámetros de control de riesgo
- [ ] Configurar alertas y monitoreo
- [ ] Preparar plan de contingencia
- [ ] Documentar configuración específica
- [ ] Verificar límites de API en Binance
- [ ] Configurar restricción por IP
- [ ] Comenzar con capital pequeño
- [ ] Tener plan de stop-loss manual

---

## 🚦 Próximos Pasos Recomendados

### Corto Plazo (1-2 semanas)
1. Ejecutar en TESTNET con diferentes configuraciones
2. Monitorear comportamiento y rendimiento
3. Ajustar parámetros según resultados
4. Documentar casos extremos observados

### Mediano Plazo (1 mes)
1. Implementar sistema de alertas (email/Telegram)
2. Agregar dashboard de monitoreo (Grafana)
3. Crear scripts de backup automático
4. Implementar testing automatizado

### Largo Plazo (3+ meses)
1. Considerar deployment en cloud (AWS/GCP/Azure)
2. Implementar CI/CD para actualizaciones
3. Explorar estrategias multi-símbolo
4. Desarrollar sistema de backtesting continuo

---

## 📚 Recursos Adicionales

- [Documentación Docker](https://docs.docker.com/)
- [API Binance](https://binance-docs.github.io/apidocs/spot/en/)
- [Stable Baselines3](https://stable-baselines3.readthedocs.io/)
- Logs del sistema: `logs/`
- Registros de trading: `registros_produccion/`

---

## ⚖️ Disclaimer

**Este sistema de trading automatizado opera con riesgo real de pérdida de capital.**

- El autor no se hace responsable de pérdidas financieras
- Usar solo capital que puedas permitirte perder
- Los rendimientos pasados no garantizan rendimientos futuros
- Trading de criptomonedas es altamente volátil
- Asegurarse de entender completamente el sistema antes de usar dinero real

---

**Versión**: 1.0  
**Fecha**: Octubre 2025  
**Última Actualización**: 4 de octubre de 2025
