# Preguntas
<details>
<summary> ¿Qué datos/indicadores voy a utilizar? </summary>

La librería `python-binance` permite descargar una amplia variedad de datos de la plataforma Binance. Se pueden dividir en:

*   **Datos de Mercado (Públicos):**
    *   **Datos históricos de velas (K-lines/Candlesticks):** Datos OHLCV (Open, High, Low, Close, Volume) en diferentes intervalos de tiempo. Son la base para la mayoría de análisis técnicos y modelos de Machine Learning.
    *   **Libro de órdenes (Order Book):** Órdenes de compra y venta activas.
    *   **Trades recientes:** Últimas operaciones ejecutadas.
    *   **Datos de Ticker:** Resumen de las últimas 24h.

*   **Datos de Cuenta (Privados, requieren API Key):**
    *   Balances, historial de órdenes y trades personales.

*   **Datos de Futuros:**
    *   Datos de mercado específicos de futuros como el *funding rate* y el *open interest*.

Inicialmente, nos centraremos en los **datos históricos de velas (K-lines)** para los pares de criptomonedas de interés. Ya que son los más comunes. 

A partir de los datos OHLCV, calcularemos **indicadores técnicos** que servirán como *features* para el modelo.

**¿Por qué usar indicadores?**
Los indicadores transforman los datos de precios para resaltar patrones específicos como la tendencia, el momentum o la volatilidad. Aportan valor al darle al modelo "pistas" que no son obvias en los datos brutos.

**¿Cuántos y cuáles usar?**
La clave es la diversidad, no la cantidad. Un exceso de indicadores puede generar ruido. Un conjunto inicial sólido incluye:
*   **MACD:** Para tendencia y momentum.
*   **RSI:** Para medir la velocidad del precio (sobrecompra/sobreventa).
*   **Bandas de Bollinger:** Para medir la volatilidad.
*   **Media Móvil Simple (SMA):** Para la tendencia a largo plazo (ej. 50 o 200 periodos).

**¿Se deben conservar los datos OHLCV?**
**Sí, es fundamental.** Los datos OHLCV son la fuente de verdad. Los indicadores son derivados de ellos. Debemos proporcionar al modelo **tanto los datos OHLCV como los indicadores** para que tenga la máxima información disponible para aprender.
</details>

<details>
<summary> ¿A que procesos se va a someter los datos?</summary>

El flujo de procesamiento de datos es un pipeline estándar para preparar series temporales para Machine Learning. El orden es importante para asegurar la calidad de los datos.

1.  **Adquisición de Datos**: Descargar los datos OHLCV brutos desde la API de Binance.

2.  **Verificación de Integridad**: Comprobar que no existen "huecos" (timestamps faltantes) en la serie de datos.

3.  **Ingeniería de Características (Feature Engineering)**: Calcular los indicadores técnicos (MACD, RSI, etc.) y añadirlos como nuevas columnas.

4.  **Limpieza de Nulos (NaN)**: Los indicadores basados en ventanas (ej. una media móvil de 50 periodos) crearán valores nulos en las primeras filas. Estas filas deben ser eliminadas ya que no pueden ser utilizadas por el modelo.

5.  **Normalización / Estandarización**: Escalar todas las características numéricas (OHLCV e indicadores) a un rango común. Esto es fundamental porque los modelos de ML son sensibles a la escala de los datos. Características con magnitudes muy diferentes (ej. precio en 50,000 vs. RSI en 70) pueden sesgar el aprendizaje.

    **¿Qué método usar?**
    *   **`MinMaxScaler` (Normalización a [0, 1])**: Es muy sensible a valores atípicos (*outliers*). Un solo pico extremo en los datos puede distorsionar la escala para el resto de los puntos.
    *   **`StandardScaler` (Estandarización)**: Transforma los datos para que tengan una media de 0 y desviación estándar de 1. Es mucho más robusto frente a outliers, lo que lo convierte en la **opción recomendada para datos financieros**.

    **Procedimiento Crítico para Evitar Fuga de Datos (Data Leakage):**
    1.  **Dividir los datos** en conjuntos de entrenamiento, validación y prueba.
    2.  **Ajustar el escalador (`fit`)** usando **únicamente** los datos de **entrenamiento**.
    3.  **Transformar (`transform`)** todos los conjuntos (entrenamiento, validación y prueba) con el escalador ya ajustado.

Este pipeline asegura que el modelo reciba datos limpios, enriquecidos y en un formato óptimo para el entrenamiento.

Ademśa, es útil mantener la columna de precios duplicada, sin hacerle la normalización. Ya que se usará para calcular stoploss y otras cosas en el entorno.

</details>