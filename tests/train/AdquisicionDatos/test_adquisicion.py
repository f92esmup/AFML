"""Tests para el módulo de adquisición de datos (DataDownloader)."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import time

from src.train.AdquisicionDatos.adquisicion import DataDownloader, INTERVAL_MAP
from src.train.config.config import UnifiedConfig


class TestIntervalMap:
    """Tests para el mapeo de intervalos."""

    def test_interval_map_contains_expected_intervals(self):
        """Verifica que INTERVAL_MAP contiene los intervalos esperados."""
        expected_intervals = ['1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M']
        
        for interval in expected_intervals:
            assert interval in INTERVAL_MAP, f"Intervalo {interval} no encontrado en INTERVAL_MAP"

    def test_interval_map_values_are_timedelta(self):
        """Verifica que todos los valores son objetos timedelta."""
        for interval, delta in INTERVAL_MAP.items():
            assert isinstance(delta, timedelta), f"El valor para {interval} no es un timedelta"


class TestDataDownloaderInit:
    """Tests para la inicialización de DataDownloader."""

    def test_init_with_valid_config(self, mock_binance_client, sample_config):
        """Test de inicialización con configuración válida."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        assert downloader.client == mock_binance_client
        assert downloader.symbol == "BTCUSDT"
        assert downloader.interval_str == "1h"
        assert downloader.start_str == "2023-01-01"
        assert downloader.end_str == "2023-01-02"
        assert downloader.limit == 1000

    def test_init_extracts_config_correctly(self, mock_binance_client, sample_config):
        """Verifica que la configuración se extrae correctamente."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        assert downloader.symbol == sample_config.data_downloader.symbol
        assert downloader.interval_str == sample_config.data_downloader.interval
        assert downloader.start_str == sample_config.data_downloader.start_date
        assert downloader.end_str == sample_config.data_downloader.end_date
        assert downloader.limit == sample_config.data_downloader.limit


class TestDataDownloaderDownloadChunk:
    """Tests para el método _download_chunk."""

    def test_download_chunk_calls_api_correctly(self, mock_binance_client, sample_config):
        """Verifica que _download_chunk llama a la API correctamente."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        start_dt = datetime(2023, 1, 1, 0, 0)
        end_dt = datetime(2023, 1, 1, 12, 0)
        
        result = downloader._download_chunk(start_dt, end_dt)
        
        # Verificar que se llamó a la API
        mock_binance_client.futures_historical_klines.assert_called_once()
        
        # Verificar los argumentos
        call_args = mock_binance_client.futures_historical_klines.call_args
        assert call_args.kwargs['symbol'] == 'BTCUSDT'
        assert call_args.kwargs['interval'] == '1h'
        assert call_args.kwargs['limit'] == 1000

    def test_download_chunk_converts_datetime_to_milliseconds(self, mock_binance_client, sample_config):
        """Verifica que las fechas se convierten a milisegundos correctamente."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        start_dt = datetime(2023, 1, 1, 0, 0)
        end_dt = datetime(2023, 1, 1, 12, 0)
        
        downloader._download_chunk(start_dt, end_dt)
        
        call_args = mock_binance_client.futures_historical_klines.call_args
        start_ms = call_args.kwargs['start_str']
        end_ms = call_args.kwargs['end_str']
        
        # Verificar que son strings de milisegundos
        assert isinstance(start_ms, str)
        assert isinstance(end_ms, str)
        assert int(start_ms) == int(start_dt.timestamp() * 1000)
        assert int(end_ms) == int(end_dt.timestamp() * 1000)

    def test_download_chunk_returns_data(self, mock_binance_client, sample_config):
        """Verifica que _download_chunk retorna datos."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        start_dt = datetime(2023, 1, 1, 0, 0)
        end_dt = datetime(2023, 1, 1, 12, 0)
        
        result = downloader._download_chunk(start_dt, end_dt)
        
        assert isinstance(result, list)
        assert len(result) > 0


class TestDataDownloaderGetTimeIntervals:
    """Tests para el método _get_time_intervals."""

    def test_get_time_intervals_returns_list(self, mock_binance_client, sample_config):
        """Verifica que retorna una lista de tuplas."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        intervals = downloader._get_time_intervals()
        
        assert isinstance(intervals, list)
        assert len(intervals) > 0
        assert all(isinstance(i, tuple) for i in intervals)
        assert all(len(i) == 2 for i in intervals)

    def test_get_time_intervals_correct_range(self, mock_binance_client, sample_config):
        """Verifica que los intervalos cubren el rango completo."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        intervals = downloader._get_time_intervals()
        
        # Primer intervalo debe empezar en start_date
        assert intervals[0][0] == datetime(2023, 1, 1, 0, 0)
        
        # Último intervalo debe terminar en end_date o antes
        assert intervals[-1][1] <= datetime(2023, 1, 2, 0, 0)

    def test_get_time_intervals_no_overlap_gaps(self, mock_binance_client, sample_config):
        """Verifica que los intervalos son contiguos sin gaps."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        intervals = downloader._get_time_intervals()
        
        for i in range(len(intervals) - 1):
            # El fin de un intervalo debe ser el inicio del siguiente
            assert intervals[i][1] == intervals[i + 1][0]

    def test_get_time_intervals_respects_limit(self, mock_binance_client, sample_config):
        """Verifica que el tamaño de cada chunk respeta el límite."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        intervals = downloader._get_time_intervals()
        interval_delta = INTERVAL_MAP['1h']
        max_chunk_delta = interval_delta * sample_config.data_downloader.limit
        
        for start_dt, end_dt in intervals:
            chunk_delta = end_dt - start_dt
            assert chunk_delta <= max_chunk_delta

    def test_get_time_intervals_invalid_interval_raises_error(self, mock_binance_client, sample_config):
        """Verifica que un intervalo inválido lanza un error."""
        # Modificar el intervalo a uno inválido
        sample_config.data_downloader.interval = "invalid_interval"
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        with pytest.raises(ValueError, match="no soportado"):
            downloader._get_time_intervals()


class TestDataDownloaderProcessToDataframe:
    """Tests para el método _process_to_dataframe."""

    def test_process_empty_list(self, mock_binance_client, sample_config):
        """Verifica el comportamiento con lista vacía."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader._process_to_dataframe([])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_process_valid_klines(self, mock_binance_client, sample_config):
        """Verifica el procesamiento de datos válidos."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        # Datos de prueba
        klines = [
            [1672531200000, "50000.0", "50100.0", "49900.0", "50050.0", "100.5",
             1672534799999, "5002500.0", 1000, "50.25", "2501250.0", "0"],
            [1672534800000, "50050.0", "50200.0", "50000.0", "50150.0", "110.5",
             1672538399999, "5522075.0", 1100, "55.75", "2761037.5", "0"]
        ]
        
        result = downloader._process_to_dataframe(klines)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']

    def test_process_sets_datetime_index(self, mock_binance_client, sample_config):
        """Verifica que el índice es DatetimeIndex."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        klines = [
            [1672531200000, "50000.0", "50100.0", "49900.0", "50050.0", "100.5",
             1672534799999, "5002500.0", 1000, "50.25", "2501250.0", "0"]
        ]
        
        result = downloader._process_to_dataframe(klines)
        
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == 'timestamp'

    def test_process_converts_to_numeric(self, mock_binance_client, sample_config):
        """Verifica que las columnas se convierten a numérico."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        klines = [
            [1672531200000, "50000.0", "50100.0", "49900.0", "50050.0", "100.5",
             1672534799999, "5002500.0", 1000, "50.25", "2501250.0", "0"]
        ]
        
        result = downloader._process_to_dataframe(klines)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            assert pd.api.types.is_numeric_dtype(result[col])

    def test_process_removes_duplicates(self, mock_binance_client, sample_config):
        """Verifica que se eliminan duplicados."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        # Datos con duplicados (mismo timestamp)
        klines = [
            [1672531200000, "50000.0", "50100.0", "49900.0", "50050.0", "100.5",
             1672534799999, "5002500.0", 1000, "50.25", "2501250.0", "0"],
            [1672531200000, "50010.0", "50110.0", "49910.0", "50060.0", "101.5",
             1672534799999, "5002600.0", 1001, "50.30", "2501300.0", "0"],
            [1672534800000, "50050.0", "50200.0", "50000.0", "50150.0", "110.5",
             1672538399999, "5522075.0", 1100, "55.75", "2761037.5", "0"]
        ]
        
        result = downloader._process_to_dataframe(klines)
        
        # Debe haber solo 2 filas (el duplicado se eliminó)
        assert len(result) == 2
        # Debe conservar el primero (keep='first')
        assert result.iloc[0]['open'] == 50000.0


class TestDataDownloaderRun:
    """Tests para el método run (método principal)."""

    def test_run_returns_dataframe(self, mock_binance_client, sample_config):
        """Verifica que run retorna un DataFrame."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader.run()
        
        assert isinstance(result, pd.DataFrame)

    def test_run_dataframe_has_correct_columns(self, mock_binance_client, sample_config):
        """Verifica que el DataFrame tiene las columnas correctas."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader.run()
        
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        assert list(result.columns) == expected_columns

    def test_run_dataframe_has_datetime_index(self, mock_binance_client, sample_config):
        """Verifica que el índice es DatetimeIndex."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader.run()
        
        assert isinstance(result.index, pd.DatetimeIndex)

    @patch('src.train.AdquisicionDatos.adquisicion.time.sleep')
    def test_run_pauses_between_calls(self, mock_sleep, mock_binance_client, sample_config):
        """Verifica que hay pausas entre llamadas a la API."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader.run()
        
        # Debe haber llamadas a sleep
        assert mock_sleep.called

    def test_run_handles_api_errors_gracefully(self, mock_binance_client, sample_config):
        """Verifica que los errores de API se manejan correctamente."""
        # Configurar el mock para lanzar un error
        mock_binance_client.futures_historical_klines.side_effect = Exception("API Error")
        
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        # No debe lanzar excepción, debe retornar DataFrame vacío
        result = downloader.run()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_run_with_long_date_range(self, mock_binance_client, sample_config):
        """Verifica el funcionamiento con un rango de fechas largo."""
        # Modificar las fechas para cubrir un mes
        sample_config.data_downloader.start_date = "2023-01-01"
        sample_config.data_downloader.end_date = "2023-02-01"
        
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        result = downloader.run()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        # Verificar que se hizo al menos una llamada
        assert mock_binance_client.futures_historical_klines.call_count >= 1


class TestDataDownloaderIntegration:
    """Tests de integración para DataDownloader."""

    def test_full_workflow(self, mock_binance_client, sample_config):
        """Test del flujo completo de descarga."""
        downloader = DataDownloader(mock_binance_client, sample_config)
        
        # Ejecutar el proceso completo
        result = downloader.run()
        
        # Verificaciones
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert isinstance(result.index, pd.DatetimeIndex)
        assert not result.isnull().any().any()  # No debe haber NaN
        assert len(result) == len(result.index.unique())  # No debe haber duplicados

    def test_different_intervals(self, mock_binance_client, sample_config):
        """Verifica que funciona con diferentes intervalos."""
        intervals_to_test = ['1h', '4h', '1d']
        
        for interval in intervals_to_test:
            sample_config.data_downloader.interval = interval
            downloader = DataDownloader(mock_binance_client, sample_config)
            
            result = downloader.run()
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
