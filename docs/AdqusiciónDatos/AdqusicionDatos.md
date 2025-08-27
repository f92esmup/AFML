# Módulo de Adqusición de datos.

> **Borrador:** En este módulo quiero realizar el proceso de obtención de datos a traves de la api de binance, procesarlos y obtener métricas de los mismos para asegurarnos que son correctos para. Quiero una estructura desarticulada este módulo es independiente al entrenamiento. Se ejecuta y como resultado se obtiene una carpeta con los datos en un ".csv" y un archivo 'metadata.yaml' con toda la información sobre los datos. El nombre de la carpeta será un DATA_ID que será el que se introduzca en el entrenamiento. Tenemos así datos autocontenidos cuya configuración se hereda en el entrenamiento, lo que permite replicar un entrenamiento o conocer con exactitud los datos usados. Por esta razón tiene su propia  configuración. 

## 