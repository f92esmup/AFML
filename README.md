# AFML: Segundo intento de crear un agente de *trading*

> **Resumen:**
> A partir de mi primer proyecto, *btcbot*, he aprendido una lección fundamental: debo asumir la mayor parte del trabajo y no delegarlo ciegamente a la IA. Esta es, sin duda, una herramienta valiosa de apoyo, pero no un sustituto del entendimiento humano.
> Uno de los principales errores que cometí fue incorporar de forma continua funcionalidades avanzadas que no llegué a comprender del todo, lo que derivó en un proyecto caótico y difícil de mantener.
> En esta nueva etapa, mi objetivo es construir un sistema **simple, funcional, documentado, testeado y escalable**. Ese será el propósito central. No pretendo que este repositorio represente el mejor sistema jamás creado, sino una base sólida sobre la que poder iterar.

> [!WARNING]
> **Advertencia de Riesgo:** Este proyecto interactúa con mercados financieros y realiza operaciones automatizadas en criptomonedas a través de la API de Binance. El uso de este software puede conllevar pérdidas financieras. Asegúrate de comprender los riesgos asociados y utiliza el sistema bajo tu propia responsabilidad. No se ofrece garantía de resultados ni soporte financiero.

## Uso Rápido

### Entrenamiento Unificado (Walk-Forward)

El sistema implementa un flujo unificado que ejecuta automáticamente:
1. Descarga de datos de entrenamiento
2. Entrenamiento del agente
3. Descarga de datos de evaluación  
4. Evaluación del modelo

```bash
python train.py \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2024-01-01 \
  --train-end-date 2024-06-30 \
  --eval-start-date 2024-07-01 \
  --eval-end-date 2024-09-30 \
  --total-timesteps 50000 \
  --episodios-eval 3
```

**Parámetros:**
- `--symbol`: Par de trading (ej: BTCUSDT, ETHUSDT)
- `--interval`: Intervalo de velas (1m, 5m, 15m, 1h, 4h, 1d)
- `--train-start-date`: Fecha inicio entrenamiento (YYYY-MM-DD)
- `--train-end-date`: Fecha fin entrenamiento (YYYY-MM-DD)
- `--eval-start-date`: Fecha inicio evaluación (YYYY-MM-DD)
- `--eval-end-date`: Fecha fin evaluación (YYYY-MM-DD)
- `--total-timesteps`: Número total de pasos de entrenamiento (default: 10000)
- `--episodios-eval`: Número de episodios de evaluación (default: 1)
- `--config`: Ruta al config.yaml (default: src/train/config/config.yaml)

**Salida:**
```
entrenamientos/
  train_BTCUSDT_20240101_20240630_lr0.0003_bs256_ws30_20251004_143022/
    ├── config_metadata.yaml    # Configuración completa + metadata
    ├── scaler_train.pkl         # Scaler del entrenamiento
    ├── scaler_eval.pkl          # Scaler de la evaluación (trazabilidad)
    ├── modelos/
    │   └── modelo.zip           # Modelo entrenado
    ├── evaluacion/
    │   ├── entorno.csv
    │   ├── operacion.csv
    │   └── portafolio.csv
    └── tensorboard/
        └── SAC_1/
```

## Workflow:
Este concepto es sumamente importante. Para impedir que en un momento dado delegue el trabajo sobre la IA voy a defirnir una seríe de reglas y procesos.

## Workflow

El flujo de trabajo será un aspecto clave. Para evitar delegar nuevamente tareas críticas a la IA, he definido una serie de reglas y procesos claros.

* **Documentación personal:**
  Todo el proceso de diseño, razonamiento y toma de decisiones se registrará en mi **libreta personal**. Allí anotaré tanto las conclusiones extraídas de mis conversaciones con la IA como las decisiones técnicas tomadas a lo largo del proyecto.
  En particular, incluiré:

  * Un registro de las preguntas que he planteado a la IA y la respuesta que *yo* he asimilado tras analizarlas, evitando simplemente copiar el texto literal.
  * Un apartado donde describa las funcionalidades que pretendo implementar en cada módulo o función, así como el comportamiento esperado de estas.

* **Uso controlado de la IA:**
  No emplearé el modo “agente” de la IA para generar grandes bloques de código de manera automática. Podré solicitar fragmentos de código concretos, pero me comprometo a estudiar y comprender cada uno de ellos antes de integrarlos.
  Este enfoque busca minimizar la generación masiva de código difícil de revisar y mantener, favoreciendo un mayor control sobre el resultado final y evitando comportamientos inesperados.

---

## Uso con Docker

El proyecto también puede ejecutarse dentro de un contenedor Docker. Esto asegura un entorno controlado y reproducible, eliminando problemas de dependencias o configuraciones locales.

### 1. Construir la imagen de Docker

Primero, construimos la imagen de Docker a partir del `Dockerfile.train` incluido en el proyecto:

```bash
docker build -t afml:latest -f Dockerfile.train .
```

**Explicación:**
- `docker build`: Comando para construir una imagen de Docker.
- `-t afml:latest`: Etiqueta (`tag`) para la imagen. En este caso, la llamamos `afml` con la versión `latest`.
- `-f Dockerfile.train`: Especifica el archivo Dockerfile a usar. Aquí usamos `Dockerfile.train`.
- `.`: Contexto de construcción. El punto indica que el contexto es el directorio actual.

### 2. Ejecutar el contenedor

Una vez construida la imagen, podemos ejecutar el entrenamiento dentro del contenedor:

```bash
docker run --rm -d \
  -v ./entrenamientos:/app/entrenamientos \
  afml:train \
  --symbol BTCUSDT \
  --interval 1m \
  --train-start-date 2024-01-01 \
  --train-end-date 2025-01-01 \
  --eval-start-date 2025-01-02 \
  --eval-end-date 2025-09-01 \
  --total-timesteps 50000
```

**Explicación:**
- `docker run`: Comando para ejecutar un contenedor.
- `--rm`: Elimina automáticamente el contenedor después de que termine su ejecución.
- `-d`: Ejecuta el contenedor en segundo plano (modo "detached").
- `--user $(id -u):$(id -g)`: Ejecuta el contenedor con el mismo usuario y grupo que el host. Esto asegura que los archivos creados dentro del contenedor tengan los permisos correctos en el sistema anfitrión.
- `-v ./entrenamientos:/app/entrenamientos`: Monta el directorio local `./entrenamientos` en el contenedor en la ruta `/app/entrenamientos`. Esto permite que los resultados del entrenamiento sean accesibles desde el host.
- `afml:latest`: Especifica la imagen de Docker a usar.
- `--symbol BTCUSDT`: Par de trading.
- `--interval 1h`: Intervalo de velas.
- `--train-start-date 2023-01-01`: Fecha de inicio del entrenamiento.
- `--train-end-date 2025-01-01`: Fecha de fin del entrenamiento.
- `--eval-start-date 2025-01-02`: Fecha de inicio de la evaluación.
- `--eval-end-date 2025-09-01`: Fecha de fin de la evaluación.
- `--total-timesteps 50000`: Número total de pasos de entrenamiento.

### 3. Verificar los resultados

Los resultados del entrenamiento se guardarán en el directorio `./entrenamientos` en el host. Puedes inspeccionarlos directamente:

```bash
ls ./entrenamientos
```

### 4. Monitorear logs

Si necesitas monitorear los logs en tiempo real, puedes usar el siguiente comando:

```bash
docker logs <container_id>
```

Reemplaza `<container_id>` con el ID del contenedor, que puedes obtener con:

```bash
docker ps
```

---

## Ejecución en Producción (Live Trading)

El sistema también puede ejecutarse en modo producción para trading en vivo usando un modelo previamente entrenado.

### 1. Construir la imagen de producción

```bash
docker build -f Dockerfile.live -t afml:live .
```

### 2. Ejecutar en modo producción (TESTNET)

```bash
docker run --rm -d \
  -v $(pwd)/entrenamientos:/app/entrenamientos \
  -e BINANCE_TESTNET_API_KEY='tu_api_key_testnet' \
  -e BINANCE_TESTNET_API_SECRET='tu_api_secret_testnet' \
  afml:live \
  --train-id train_BTCUSDT_20230101_20250101_lr3e-4_bs256_ws30_20251004_174919
```

**Explicación:**

- `-v $(pwd)/entrenamientos:/app/entrenamientos`: Monta el directorio de entrenamientos para acceder al modelo
- `-e BINANCE_TESTNET_API_KEY`: Variable de entorno con tu API key de testnet
- `-e BINANCE_TESTNET_API_SECRET`: Variable de entorno con tu API secret de testnet
- `--train-id`: ID del entrenamiento que contiene el modelo a usar

**⚠️ IMPORTANTE:**

- Por defecto ejecuta en **TESTNET** (simulación segura)
- Para usar en producción real, añade el flag `--live` y usa las variables `BINANCE_API_KEY` y `BINANCE_API_SECRET`
- **NUNCA** expongas tus API keys en el código. Usa siempre variables de entorno

### 3. Monitorear logs de producción

```bash
docker logs -f <container_id>
```

Los logs y registros de operaciones se guardarán en:

```text
entrenamientos/<train_id>/produccion/
├── produccion_<timestamp>.log     # Log completo de la sesión
├── registro_<timestamp>.csv       # Registro de todas las operaciones
└── emergencias_<timestamp>.csv    # Registro de eventos de emergencia
```

---

## Mejoras Pendientes

### Sistema de Descarga de Datos - Manejo de Errores de Red

**Fecha de análisis:** 6 de octubre de 2025

#### Problema Identificado

Durante la descarga de datos de evaluación se detectó un timeout en la API de Binance que resultó en pérdida de datos:

- **Error:** `ReadTimeout` en el chunk 1/233 (datos del 2025-01-02 al 2025-01-03)
- **Causa:** Timeout de lectura de 10 segundos en `fapi.binance.com`
- **Impacto:** El chunk fallido se perdió, generando un hueco en los datos históricos
- **Comportamiento actual:** El error se captura y registra, pero el proceso continúa sin reintentar la descarga del chunk fallido

#### Código Problemático

Ubicación: `src/train/AdquisicionDatos/adquisicion.py` (líneas 120-126)

```python
for i, (start_dt, end_dt) in enumerate(time_intervals):
    try:
        log.info(f"Descargando chunk {i+1}/{len(time_intervals)}...")
        chunk = self._download_chunk(start_dt, end_dt)
        all_klines_data.extend(chunk)  # Solo se añade si tiene éxito
        time.sleep(0.5)
    except Exception as e:
        log.error(f"Error durante la descarga del chunk {start_dt}-{end_dt}: {e}", exc_info=True)
        # PROBLEMA: No hay retry ni se marca el fallo
```

#### Aspectos Evaluados

**✅ Positivos:**
- El error fue capturado con `try-except`
- Se registró el error con traceback completo
- El proceso no se detuvo completamente

**❌ Negativos (CRÍTICOS):**
- El chunk fallido se perdió permanentemente
- No hay mecanismo de reintentos
- Un timeout puntual causa pérdida de datos
- No se reporta el número de chunks fallidos al finalizar
- El mensaje final "Descarga de todos los chunks completada" es engañoso si hubo fallos

#### Mejoras Propuestas

1. **Implementar sistema de reintentos con backoff exponencial:**
   - Intentar descargar 3-5 veces antes de marcar como fallo definitivo
   - Aumentar el tiempo de espera entre reintentos progresivamente (1s, 2s, 4s, 8s)
   
2. **Aumentar timeout de lectura:**
   - Cambiar de 10 a 30 segundos para conexiones lentas
   
3. **Contador de fallos y reporte:**
   - Llevar registro de chunks fallidos
   - Incluir en el log final: chunks exitosos vs fallidos
   - Alertar si el porcentaje de fallos supera un umbral (ej: >5%)
   
4. **Validación de completitud:**
   - Verificar que no hay huecos temporales en el DataFrame final
   - Advertir al usuario sobre datos faltantes antes de entrenar/evaluar

5. **Implementación sugerida:**
   ```python
   MAX_RETRIES = 5
   TIMEOUT = 30
   failed_chunks = []
   
   for i, (start_dt, end_dt) in enumerate(time_intervals):
       for retry in range(MAX_RETRIES):
           try:
               chunk = self._download_chunk(start_dt, end_dt)
               all_klines_data.extend(chunk)
               break  # Éxito, salir del retry loop
           except Exception as e:
               if retry == MAX_RETRIES - 1:
                   failed_chunks.append((start_dt, end_dt))
                   log.error(f"Fallo definitivo en chunk {start_dt}-{end_dt}")
               else:
                   wait_time = 2 ** retry
                   log.warning(f"Reintento {retry+1}/{MAX_RETRIES} en {wait_time}s")
                   time.sleep(wait_time)
   ```

**Prioridad:** Alta - Afecta la calidad e integridad de los datos de entrenamiento/evaluación
