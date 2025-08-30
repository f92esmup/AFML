"""Este script se encarga de la descarga secuencial de datos usando la API de Binance"""
import pandas as pd
import time
from datetime import datetime, timedelta
import logging

from src.AdqusicionDatos.config import Config

log = logging.getLogger(f"AFML.{__name__}")

# Mapeo de intervalos de Binance a objetos timedelta de Python
INTERVAL_MAP = {
    '1m': timedelta(minutes=1),
    '5m': timedelta(minutes=5),
    '1h': timedelta(hours=1),
    '4h': timedelta(hours=4),
    '1d': timedelta(days=1),
    '1w': timedelta(weeks=1),
    '1M': timedelta(days=30),
}

class DataDownloader:

    def __init__(self, client, config: Config) -> None: # No he tipeado estos objetos.
        self.client = client
        # Asignamos los valores desde el objeto de configuración
        self.symbol = config.data_downloader.symbol
        self.interval_str = config.data_downloader.interval
        self.start_str = config.data_downloader.start_date
        # Si no hay end_date, usamos la fecha actual
        self.end_str = config.data_downloader.end_date
        self.limit = config.data_downloader.limit # Límite máximo para futuros
        log.debug(f"DataDownloader inicializado para {self.symbol} con intervalo {self.interval_str} desde {self.start_str} hasta {self.end_str}.")

    def _download_chunk(self, start_dt: datetime, end_dt: datetime) -> list:
        """Descarga un único trozo de datos."""
        log.debug(f"Descargando chunk desde {start_dt} hasta {end_dt}...")
        # Convertimos datetime a string en el formato que la API entiende
        start_ms = str(int(start_dt.timestamp() * 1000))
        end_ms = str(int(end_dt.timestamp() * 1000))

        return self.client.futures_historical_klines(
            symbol=self.symbol, 
            interval=self.interval_str, 
            start_str=start_ms, 
            end_str=end_ms, 
            limit=self.limit
        )
    
    def _get_time_intervals(self) -> list:
        """
        Calcula y devuelve una lista de tuplas (start_datetime, end_datetime)
        para cada llamada necesaria a la API.
        """
        log.debug("Calculando intervalos de tiempo para las llamadas a la API.")
        current_start_dt = datetime.strptime(self.start_str, '%Y-%m-%d')
        absolute_end_dt = datetime.strptime(self.end_str, '%Y-%m-%d')  #type: ignore
        
        interval_delta = INTERVAL_MAP.get(self.interval_str)
        if not interval_delta:
            # Es mejor lanzar un error si el intervalo no es válido
            log.error(f"Intervalo '{self.interval_str}' no soportado para cálculo de tiempo.")
            raise ValueError(f"Intervalo '{self.interval_str}' no soportado para cálculo de tiempo.")

        chunk_delta = interval_delta * self.limit
        intervals = []

        while current_start_dt < absolute_end_dt:
            chunk_end_dt = current_start_dt + chunk_delta
            # Nos aseguramos de no pasarnos de la fecha final absoluta
            chunk_end_dt = min(chunk_end_dt, absolute_end_dt)
            
            intervals.append((current_start_dt, chunk_end_dt))
            
            # La nueva fecha de inicio es la fecha de fin del trozo actual
            current_start_dt = chunk_end_dt
        
        log.debug(f"Se han calculado {len(intervals)} intervalos de tiempo.")
        return intervals

    def _process_to_dataframe(self, all_klines: list) -> pd.DataFrame:
        """Convierte la lista de datos descargados a un DataFrame con los formatos y nombres de columna adecuados."""
        log.info("Procesando datos descargados para convertirlos a DataFrame.")
        if not all_klines:
            log.warning("No se han recibido datos para procesar. Devolviendo DataFrame vacío.")
            return pd.DataFrame()
            
        columns = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 
            'taker_buy_quote_asset_volume', 'ignore'
        ]
        df = pd.DataFrame(all_klines, columns=columns)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Eliminar duplicados que pueden aparecer en los solapamientos de las llamadas
        initial_rows = len(df)
        df = df[~df.index.duplicated(keep='first')]
        final_rows = len(df)
        if initial_rows > final_rows:
            log.debug(f"Se eliminaron {initial_rows - final_rows} registros duplicados.")

        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def run(self) -> pd.DataFrame:
        """Realiza el proceso de descarga y devuelve el DataFrame resultante."""
        log.info("Iniciando proceso de descarga de datos históricos.")
        time_intervals = self._get_time_intervals()
        all_klines_data = []

        log.info(f"Se realizarán {len(time_intervals)} llamadas a la API de Binance.")

        for i, (start_dt, end_dt) in enumerate(time_intervals):
            try:
                log.info(f"Descargando chunk {i+1}/{len(time_intervals)}...")
                chunk = self._download_chunk(start_dt, end_dt)
                all_klines_data.extend(chunk)
                log.debug(f"Pausa de 0.5s para no saturar la API.")
                time.sleep(0.5) # Pausa para ser respetuosos con la API
            except Exception as e:
                log.error(f"Error durante la descarga del chunk {start_dt}-{end_dt}: {e}", exc_info=True)
        
        log.info("Descarga de todos los chunks completada.")
        final_df = self._process_to_dataframe(all_klines_data)
        log.info(f"Proceso finalizado. Se han obtenido {len(final_df)} velas.")
        return final_df

