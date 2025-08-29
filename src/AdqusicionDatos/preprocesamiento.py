""" clase para el limpiado y calculo de indicadores """
import pandas as pd
import pandas_ta as ta
from sklearn.preprocessing import StandardScaler

from src.AdqusicionDatos.config import Config

class Preprocesamiento:
    
    def __init__(self, config: Config) -> None:

        self.df = pd.DataFrame()

        self.interval = config.data_downloader.interval
        self.interpol_method = config.preprocesamiento.interpol_method

        # Indicadores:
        self.sma_short = config.preprocesamiento.indicadores.SMA_short
        self.sma_long = config.preprocesamiento.indicadores.SMA_long
        self.rsi_length = config.preprocesamiento.indicadores.RSI_length
        self.macd_fast = config.preprocesamiento.indicadores.MACD_fast
        self.macd_slow = config.preprocesamiento.indicadores.MACD_slow
        self.macd_signal = config.preprocesamiento.indicadores.MACD_signal
        self.bbands_length = config.preprocesamiento.indicadores.BB_length
        self.bbands_std = config.preprocesamiento.indicadores.BB_std



    def run(self, df: pd.DataFrame) -> tuple[pd.DataFrame, StandardScaler]:
        """ metodo para ejecutar el preprocesamiento """
        # Asignamos el DataFrame
        self.df = df
        # _continuidad -> _interpolación -> _calculo_indicadores -> _eliminar_faltantes
        self.df = self._continuidad()
        self.df = self._interpolacion()
        self.df = self._calculo_indicadores()
        self.df = self._eliminar_faltantes()
        scaler = self._scaler()
        return self.df, scaler

    def _interpolacion(self) -> pd.DataFrame:
        """ metodo para realizar la interpolacion de los datos """
        # Interpolar linealmente los valores NaN que resultaron de la reindexación
        self.df.interpolate(method=self.interpol_method, inplace=True) #type: ignore
        return self.df

    def _continuidad(self) -> pd.DataFrame:
        """ 
        Metodo para asegurar que los datos no tienen saltos en tiempo.
        Identifica la frecuencia e inserta filas NaN para los timestamps faltantes.
        """
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise TypeError("El índice del DataFrame debe ser de tipo DatetimeIndex.")

        # 1. Crear un índice completo desde el inicio hasta el final con la frecuencia inferida
        full_index = pd.date_range(start=self.df.index.min(), end=self.df.index.max(), freq=self.interval)

        # 2. Comprobar si hay huecos
        missing_timestamps = full_index.difference(self.df.index)
        if not missing_timestamps.empty:
            print(f"Se encontraron {len(missing_timestamps)} timestamps faltantes. Rellenando huecos...")
            # Reindexar el DataFrame. Esto crea filas con NaN para los huecos.
            self.df = self.df.reindex(full_index)
        else:
            print("El índice es continuo. No se encontraron huecos.")
        
        return self.df
    
    def _calculo_indicadores(self) -> pd.DataFrame:
        """ 
        Metodo para calcular los indicadores técnicos usando la extensión .ta
        y añadirlos directamente al DataFrame.
        """

        print("Calculando indicadores técnicos...")
        # No lo he incluido, porque por defecto pandas_ta usa la columna 'close' para calcular indicadores.

        # Cálculo de SMA para la tendencia a corto y largo plazo
        self.df.ta.sma(length=self.sma_short, append=True)
        self.df.ta.sma(length=self.sma_long, append=True)

        # Cálculo de RSI
        self.df.ta.rsi(length=self.rsi_length, append=True)

        # Cálculo de MACD
        self.df.ta.macd(
            fast=self.macd_fast,
            slow=self.macd_slow,
            signal=self.macd_signal,
            append=True
        )

        # Cálculo de Bollinger Bands
        self.df.ta.bbands(
            length=self.bbands_length,
            std=self.bbands_std,
            append=True
        )

        print(f"Indicadores calculados: {self.df.columns}")
        
        return self.df

    def _eliminar_faltantes(self) -> pd.DataFrame:
        """ metodo para eliminar los datos faltantes tras el calculo de indicardores """
        # Eliminar filas con cualquier valor NaN
        self.df.dropna(inplace=True)
        return self.df
    
    def _scaler(self) -> StandardScaler:
        """ métdo para calcular el scaler """

        # Creamos el objeto StandardScaler:
        scaler = StandardScaler()
        # Ajustamos el scaler a los datos (aprendiendo los parámetros):
        scaler.fit(self.df)

        return scaler
