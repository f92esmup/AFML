# AFML: Segundo intento de crear un agente de Trading.

> **Resumen:** Del primero proyecto que he realizado *btcbot* he aprendido que debo realizar yo todo el trabajo y no delegarselo a la IA. La IA es una gran herramienta de apoyo. Uno de los errores más graves que cometí es la implementación continua de características avanzadas que no llegue a entender realmente. Resultando en un proyecto caótico. En lo que me voy a enfocar en esta ocasión es en crear un proyecto **simple, funcional, documentado, testeado y escalable**. Este es el proposito principal. No espero que este repositorio sea el mejor sistema creado hasta la fecha.

> [!WARNING]
> **Advertencia de Riesgo:** Este proyecto interactúa con mercados financieros y realiza operaciones automatizadas en criptomonedas a través de la API de Binance. El uso de este software puede conllevar pérdidas financieras. Asegúrate de comprender los riesgos asociados y utiliza el sistema bajo tu propia responsabilidad. No se ofrece garantía de resultados ni soporte financiero.

## 🚀 Uso Rápido

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
  --episodios 5 \
  --episodios-eval 3
```

**Parámetros:**
- `--symbol`: Par de trading (ej: BTCUSDT, ETHUSDT)
- `--interval`: Intervalo de velas (1m, 5m, 15m, 1h, 4h, 1d)
- `--train-start-date`: Fecha inicio entrenamiento (YYYY-MM-DD)
- `--train-end-date`: Fecha fin entrenamiento (YYYY-MM-DD)
- `--eval-start-date`: Fecha inicio evaluación (YYYY-MM-DD)
- `--eval-end-date`: Fecha fin evaluación (YYYY-MM-DD)
- `--episodios`: Número de episodios de entrenamiento (default: 1)
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

* Todo va a ser documentado. En la carpeta "docs" creare distintos archivos con los resltuados de mis discusiones con la IA. Las herramientas utilizadas y el porque las he elegido sobre otras. En principio, el contenido será el siguiente:
    * Un documento donde registro cada pregunta que he intentado resolver con IA y la respuesta. No la respuesta literal de la IA si no la que yo he asimilado tras discutirlo con la IA.
    * Un documento donde explique las funcionalidades que quiero implementar a cada módulo o función. EL como espero que actúe.

* No voy a usar el modo agente de la IA para escribir código. Puedo pedir piezas de código concretas a la IA pero debo aprender lo que no entienda de ellas. La idea es reducir la cantidad de código que se genera de golpe y que resulta abrumador de analizar. Con este método mantengo un mayor control sobre el resultado y evito comportamientos inesperados.

## 🐳 Uso con Docker

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
  --user $(id -u):$(id -g) \
  -v ./entrenamientos:/app/entrenamientos \
  afml:latest \
  --symbol BTCUSDT \
  --interval 1h \
  --train-start-date 2023-01-01 \
  --train-end-date 2025-01-01 \
  --eval-start-date 2025-01-02 \
  --eval-end-date 2025-09-01 \
  --episodios 3
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
- `--episodios 3`: Número de episodios de entrenamiento.

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
