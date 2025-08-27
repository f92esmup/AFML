# Módulo de Adqusición de datos.

> **Borrador:** En este módulo quiero realizar el proceso de obtención de datos a traves de la api de binance, procesarlos y obtener métricas de los mismos para asegurarnos que son correctos para. Quiero una estructura desarticulada este módulo es independiente al entrenamiento. Se ejecuta y como resultado se obtiene una carpeta con los datos en un ".csv" y un archivo 'metadata.yaml' con toda la información sobre los datos. El nombre de la carpeta será un DATA_ID que será el que se introduzca en el entrenamiento. Tenemos así datos autocontenidos cuya configuración se hereda en el entrenamiento, lo que permite replicar un entrenamiento o conocer con exactitud los datos usados. Por esta razón tiene su propia  configuración. 

## **Arquitectura:**


## Datos (adquisicion.py)
Vamos a centrarnos en la descarga de datos de velas OHCLV de futuros. La descarga se guardará en un dataframe (NO se guarda en un .csv hasta que se complete todo el proceso). La llamada a la api se realiza de forma serial (no asincrónica). 

## Procesos (procesamiento.py)
Una vez con los datos descargados, realizamos los siguientes procesos:
1. Comprobamos que no falte ningun valor del timestamp, si falta se añade como vacio y se interpola su valor.

2. Añadimos los indicadores.

3. Eliminamos las columnas nulas debido al calculo de indicadores que usan ventana N de velas.

4. Normalizamos todas las columnas. Excepto la duplicada del precio.

5. Guardar los datos en un .csv

## Indicadores (indicadores.py) No se si realmente necesita un script único.
Vamos a emplear unicamente los siguientes indicadores, que calcularemos con pandas-ta:

- MACD: Para tendencia y momentum.
- RSI: Para medir la velocidad del precio (sobrecompra/sobreventa).
- Bandas de Bollinger: Para medir la volatilidad.
- Media Móvil Simple (SMA): Para la tendencia a largo plazo (ej. 50 o 200 periodos). 


# Cosas que quiero tener en cuenta:
- [ ] Tengo que crear la configuración
- [ ] Tener en cuenta el guardado de metadata, el como recopilar la información, run_id...
- [ ] Tengo que añadir el analisis de datos para ver el estado de los mismos.