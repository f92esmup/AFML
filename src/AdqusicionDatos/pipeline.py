""" Script que define el flujo de acciones entre objetos para la descarga de datos"""
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler
from argparse import Namespace
from binance.client import Client
import joblib
import yaml

from .config import Config
from .adquisicion import DataDownloader
from .preprocesamiento import Preprocesamiento

class DataPipeline:

    def __init__(self, args: Namespace) -> None:
        """ Incializamos todos los objetos necesarios para la obtención de datos """
        
        self.config = Config.load_config(args)

        # Creamos el objeto DataDownloader
        self.data_downloader = DataDownloader(client=Client(), config=self.config)

        # Creamos el objeto preprocesamiento
        self.preprocesamiento = Preprocesamiento(config=self.config)

        #### LO QUE SIGA ####

    def run(self)-> None:
        """ metodo que ejecuta el pipeline de obtencion de datos """
        # 1. Descargamos los datos
        data = self.data_downloader.run()

        # 2. Preprocesamos los datos
        data, scaler  = self.preprocesamiento.run(data)

        # 3. Guardamos los datos y el scaler
        self._guardar_datos(data, scaler)

    def _guardar_datos(self, data: pd.DataFrame, scaler: StandardScaler) -> None:
        """ metodo para guardar los datos y el scaler """
        # Rutas de los archivos
        root_dir = self.config.output.root
        data_path = os.path.join(root_dir, self.config.output.data_filename)
        scaler_path = os.path.join(root_dir, self.config.output.scaler_filename)
        metadata_path = os.path.join(root_dir, self.config.output.metadata_filename)

        # Creamos las carpetas si no existen
        os.makedirs(root_dir, exist_ok=True)

        # Guardamos el DataFrame en CSV
        data.to_csv(data_path, index=True)

        # Guardamos el scaler usando joblib
        joblib.dump(scaler, scaler_path)

        # Guardamos los metadatos
        config_dict = self.config.model_dump()

        with open(metadata_path, 'w') as file:
            yaml.dump(config_dict, file, sort_keys=False, default_flow_style=False)

