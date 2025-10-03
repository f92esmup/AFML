""" Script que define el flujo de acciones entre objetos para la descarga de datos"""
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler
from argparse import Namespace
from binance.client import Client
import joblib
import yaml
import logging

from src.train.config import UnifiedConfig
from .adquisicion import DataDownloader
from .preprocesamiento import Preprocesamiento

log = logging.getLogger(f"AFML.{__name__}")

class DataPipeline:

    def __init__(self, args: Namespace) -> None:
        """ Incializamos todos los objetos necesarios para la obtención de datos """
        log.info("Inicializando DataPipeline...")
        
        self.config = UnifiedConfig.load_for_data_acquisition(args)
        log.debug("Configuración cargada.")

        # Creamos el objeto DataDownloader
        log.info("Creando instancia de DataDownloader.")
        self.data_downloader = DataDownloader(client=Client(), config=self.config)

        # Creamos el objeto preprocesamiento
        log.info("Creando instancia de Preprocesamiento.")
        self.preprocesamiento = Preprocesamiento(config=self.config)

        log.info("DataPipeline inicializado con éxito.")

    def run(self)-> None:
        """ metodo que ejecuta el pipeline de obtencion de datos """
        log.info("Iniciando ejecución del pipeline.")
        # 1. Descargamos los datos
        log.info("Paso 1: Descargando datos brutos.")
        data = self.data_downloader.run()
        log.info(f"Paso 1 completado. Se han descargado {len(data)} registros.")

        # 2. Preprocesamos los datos
        log.info("Paso 2: Preprocesando datos.")
        data, scaler  = self.preprocesamiento.run(data)
        log.info("Paso 2 completado. Datos preprocesados y escalados.")

        # 3. Guardamos los datos y el scaler
        log.info("Paso 3: Guardando artefactos (datos, scaler, metadatos).")
        self._guardar_datos(data, scaler)
        log.info("Ejecución del pipeline finalizada con éxito.")

    def _guardar_datos(self, data: pd.DataFrame, scaler: StandardScaler) -> None:
        """ metodo para guardar los datos y el scaler """
        # Rutas de los archivos
        # Para adquisición de datos, el output tiene estructura OutputDataAcquisitionConfig
        output_config = self.config.output
        root_dir = output_config.root  # type: ignore
        data_path = os.path.join(root_dir, output_config.data_filename)  # type: ignore
        scaler_path = os.path.join(root_dir, output_config.scaler_filename)  # type: ignore
        metadata_path = os.path.join(root_dir, output_config.metadata_filename)  # type: ignore

        # Creamos las carpetas si no existen
        log.debug(f"Asegurando que el directorio de salida exista: {root_dir}")
        os.makedirs(root_dir, exist_ok=True)

        # Guardamos el DataFrame en CSV
        log.info(f"Guardando datos en: {data_path}")
        data.to_csv(data_path, index=True)

        # Guardamos el scaler usando joblib
        log.info(f"Guardando scaler en: {scaler_path}")
        joblib.dump(scaler, scaler_path)

        # Guardamos los metadatos
        log.info(f"Guardando metadatos en: {metadata_path}")
        config_dict = self.config.model_dump()

        with open(metadata_path, 'w') as file:
            yaml.dump(config_dict, file, sort_keys=False, default_flow_style=False)

