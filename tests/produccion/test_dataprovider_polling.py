"""Tests para DataProviderPolling - Sistema de reintentos robusto.

Tests que validan:
1. Obtención exitosa de última vela
2. Sistema de reintentos (15 intentos)
3. Verificación de progreso temporal con penúltima vela
4. Buffer adaptativo según intervalo
5. Fail-safe: sistema se para si falla después de 15 intentos
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call

from src.produccion.dataprovider.polling import DataProviderPolling
from src.produccion.config.config import ProductionConfig


class TestDataProviderPollingReintentos:
    """Tests del sistema de reintentos robusto."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción para 1h."""
        config_dict = config_metadata_dict.copy()
        config_dict["intervalo"] = "1h"  # Intervalo largo para polling
        config = ProductionConfig(
            **config_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def provider(self, production_config, fitted_scaler):
        """Fixture del DataProviderPolling."""
        return DataProviderPolling(production_config, fitted_scaler)
    
    @pytest.fixture
    def mock_klines_progreso(self):
        """Mock de klines que muestra progreso temporal."""
        now_ms = int(datetime.now().timestamp() * 1000)
        return [
            # Penúltima vela (1 hora antes)
            [
                now_ms - 3600000,  # open_time
                "50000", "50100", "49900", "50050",  # OHLC
                "100",  # volume
                now_ms - 3600000 + 3599999,  # close_time
                "5000000", 500, "50", "2500000", "ignore"
            ],
            # Última vela (actual)
            [
                now_ms,  # open_time
                "50050", "50150", "49950", "50100",  # OHLC
                "105",  # volume
                now_ms + 3599999,  # close_time
                "5250000", 520, "52", "2625000", "ignore"
            ]
        ]
    
    @pytest.fixture
    def mock_klines_sin_progreso(self):
        """Mock de klines sin progreso temporal (vela duplicada)."""
        now_ms = int(datetime.now().timestamp() * 1000)
        return [
            # Ambas velas son la misma
            [
                now_ms - 3600000,
                "50000", "50100", "49900", "50050",
                "100",
                now_ms - 3600000 + 3599999,
                "5000000", 500, "50", "2500000", "ignore"
            ],
            [
                now_ms - 3600000,  # Mismo timestamp!
                "50000", "50100", "49900", "50050",
                "100",
                now_ms - 3600000 + 3599999,
                "5000000", 500, "50", "2500000", "ignore"
            ]
        ]
    
    @pytest.mark.asyncio
    async def test_fetch_vela_exito_primer_intento(self, provider, mock_klines_progreso):
        """Test: Obtiene vela exitosamente en el primer intento."""
        # Mock del cliente
        mock_client = AsyncMock()
        mock_client.futures_klines.return_value = mock_klines_progreso
        provider.client = mock_client
        
        # Ejecutar
        vela = await provider._fetch_latest_closed_candle()
        
        # Verificaciones
        assert vela is not None
        assert vela['is_closed'] is True
        assert 'timestamp' in vela
        assert 'close' in vela
        assert vela['close'] == 50100.0  # Última vela
        
        # Solo debe hacer 1 llamada a la API
        assert mock_client.futures_klines.call_count == 1
    
    @pytest.mark.asyncio
    async def test_fetch_vela_reintenta_y_recupera(self, provider, mock_klines_progreso):
        """Test: Reintenta cuando falla y eventualmente recupera."""
        mock_client = AsyncMock()
        
        # Primeros 2 intentos fallan, tercero tiene éxito
        mock_client.futures_klines.side_effect = [
            [],  # Intento 1: vacío
            [mock_klines_progreso[0]],  # Intento 2: solo 1 vela
            mock_klines_progreso,  # Intento 3: éxito
        ]
        
        provider.client = mock_client
        
        # Ejecutar (con timeout para evitar espera larga)
        with patch('asyncio.sleep', new_callable=AsyncMock):
            vela = await provider._fetch_latest_closed_candle()
        
        # Verificaciones
        assert vela is not None
        assert vela['close'] == 50100.0
        
        # Debe haber hecho 3 llamadas
        assert mock_client.futures_klines.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_vela_sin_progreso_temporal_reintenta(self, provider, mock_klines_sin_progreso):
        """Test: Detecta falta de progreso temporal y reintenta."""
        mock_client = AsyncMock()
        
        # Establecer última vela procesada EXACTAMENTE igual a la penúltima
        # para forzar que no haya progreso
        provider.ultima_vela_timestamp = datetime.fromtimestamp(
            int(mock_klines_sin_progreso[0][6]) / 1000
        )
        
        # Crear mock de progreso que sea DESPUÉS
        timestamp_progreso = provider.ultima_vela_timestamp + timedelta(hours=1)
        timestamp_progreso_ms = int(timestamp_progreso.timestamp() * 1000)
        
        mock_klines_con_progreso = [
            # Penúltima vela (1 hora después de ultima_vela_timestamp)
            [
                timestamp_progreso_ms - 3600000,
                "50000", "50100", "49900", "50050",
                "100",
                timestamp_progreso_ms - 1,
                "5000000", 500, "50", "2500000", "ignore"
            ],
            # Última vela (más reciente aún)
            [
                timestamp_progreso_ms,
                "50050", "50150", "49950", "50100",
                "105",
                timestamp_progreso_ms + 3599999,
                "5250000", 520, "52", "2625000", "ignore"
            ]
        ]
        
        # Primer intento: sin progreso (penúltima <= ultima_vela_timestamp)
        # Segundo intento: con progreso
        mock_client.futures_klines.side_effect = [
            mock_klines_sin_progreso,  # Intento 1: sin progreso
            mock_klines_con_progreso,  # Intento 2: con progreso
        ]
        
        provider.client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            vela = await provider._fetch_latest_closed_candle()
        
        # Debe haber detectado progreso en el segundo intento
        assert vela is not None
        assert mock_client.futures_klines.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_vela_falla_despues_10_intentos(self, provider):
        """Test: Lanza RuntimeError después de 15 intentos fallidos."""
        mock_client = AsyncMock()
        
        # Todos los intentos fallan (retorna vacío)
        mock_client.futures_klines.return_value = []
        provider.client = mock_client
        
        # Ejecutar y esperar RuntimeError
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="CRÍTICO.*15 intentos"):
                await provider._fetch_latest_closed_candle()
        
        # Debe haber intentado exactamente 15 veces
        assert mock_client.futures_klines.call_count == 15
    
    @pytest.mark.asyncio
    async def test_fetch_vela_sin_progreso_10_intentos_falla(self, provider, mock_klines_sin_progreso):
        """Test: Falla después de 15 intentos sin progreso temporal."""
        mock_client = AsyncMock()
        
        # Establecer última vela procesada
        provider.ultima_vela_timestamp = datetime.fromtimestamp(
            int(mock_klines_sin_progreso[0][6]) / 1000
        )
        
        # Todos los intentos retornan sin progreso
        mock_client.futures_klines.return_value = mock_klines_sin_progreso
        provider.client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="Sin progreso temporal.*15 intentos"):
                await provider._fetch_latest_closed_candle()
        
        assert mock_client.futures_klines.call_count == 15
    
    @pytest.mark.asyncio
    async def test_fetch_vela_backoff_incremental(self, provider, mock_klines_progreso):
        """Test: Verifica que el backoff es incremental."""
        mock_client = AsyncMock()
        mock_sleep = AsyncMock()
        
        # Primeros 3 intentos fallan
        mock_client.futures_klines.side_effect = [
            [],
            [],
            [],
            mock_klines_progreso,  # Cuarto intento: éxito
        ]
        
        provider.client = mock_client
        
        with patch('asyncio.sleep', mock_sleep):
            vela = await provider._fetch_latest_closed_candle()
        
        # Verificar llamadas a sleep con backoff incremental
        # Configuración actual: base_wait=11s, incremento=1.0s
        # Intento 1 → espera 11.0s
        # Intento 2 → espera 12.0s
        # Intento 3 → espera 13.0s
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == pytest.approx(11.0, abs=0.1)
        assert sleep_calls[1] == pytest.approx(12.0, abs=0.1)
        assert sleep_calls[2] == pytest.approx(13.0, abs=0.1)
    
    @pytest.mark.asyncio
    async def test_fetch_vela_usa_ultima_no_penultima(self, provider, mock_klines_progreso):
        """Test: Verifica que usa la ÚLTIMA vela, no la penúltima."""
        mock_client = AsyncMock()
        mock_client.futures_klines.return_value = mock_klines_progreso
        provider.client = mock_client
        
        vela = await provider._fetch_latest_closed_candle()
        
        # La última vela tiene close=50100, la penúltima close=50050
        assert vela['close'] == 50100.0  # ÚLTIMA vela
        assert vela['open'] == 50050.0  # ÚLTIMA vela
    
    @pytest.mark.asyncio
    async def test_fetch_vela_verifica_con_penultima(self, provider, mock_klines_progreso):
        """Test: Verifica progreso temporal usando la penúltima vela."""
        mock_client = AsyncMock()
        
        # Configurar timestamp de última vela procesada (hora anterior)
        penultima_timestamp = datetime.fromtimestamp(
            int(mock_klines_progreso[0][6]) / 1000
        )
        provider.ultima_vela_timestamp = penultima_timestamp - timedelta(hours=1)
        
        mock_client.futures_klines.return_value = mock_klines_progreso
        provider.client = mock_client
        
        vela = await provider._fetch_latest_closed_candle()
        
        # Debe aceptar la vela porque la penúltima es más reciente
        assert vela is not None
        assert vela['close'] == 50100.0


class TestDataProviderPollingBufferAdaptativo:
    """Tests del buffer adaptativo según intervalo."""
    
    @pytest.fixture
    def production_config_1h(self, config_metadata_dict, fitted_scaler):
        """Config para intervalo 1h."""
        config_dict = config_metadata_dict.copy()
        config_dict["intervalo"] = "1h"
        config = ProductionConfig(
            **config_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def production_config_5m(self, config_metadata_dict, fitted_scaler):
        """Config para intervalo 5m."""
        config_dict = config_metadata_dict.copy()
        config_dict["intervalo"] = "5m"
        config = ProductionConfig(
            **config_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.mark.asyncio
    async def test_buffer_10s_para_1h(self, production_config_1h, fitted_scaler):
        """Test: Buffer de 10s para intervalos >= 1h."""
        provider = DataProviderPolling(production_config_1h, fitted_scaler)
        
        # Mock time_sync
        mock_time_sync = Mock()
        now = datetime(2025, 10, 8, 12, 30, 0)
        mock_time_sync.get_binance_time.return_value = now
        provider.time_sync = mock_time_sync
        
        mock_sleep = AsyncMock()
        
        with patch('asyncio.sleep', mock_sleep):
            await provider._wait_until_next_candle_close()
        
        # Debe esperar hasta las 13:00:00 + 10s buffer
        # From 12:30:00 to 13:00:00 = 1800s
        # + 10s buffer = 1810s
        sleep_time = mock_sleep.call_args[0][0]
        assert sleep_time == pytest.approx(1810, abs=1)
    
    @pytest.mark.asyncio
    async def test_buffer_5s_para_5m(self, production_config_5m, fitted_scaler):
        """Test: Buffer de 5s para intervalos < 1h."""
        provider = DataProviderPolling(production_config_5m, fitted_scaler)
        
        # Mock time_sync
        mock_time_sync = Mock()
        now = datetime(2025, 10, 8, 12, 32, 0)
        mock_time_sync.get_binance_time.return_value = now
        provider.time_sync = mock_time_sync
        
        mock_sleep = AsyncMock()
        
        with patch('asyncio.sleep', mock_sleep):
            await provider._wait_until_next_candle_close()
        
        # Debe esperar hasta las 12:35:00 + 5s buffer
        # From 12:32:00 to 12:35:00 = 180s
        # + 5s buffer = 185s
        sleep_time = mock_sleep.call_args[0][0]
        assert sleep_time == pytest.approx(185, abs=1)


class TestDataProviderPollingIntegracion:
    """Tests de integración del flujo completo."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración."""
        config_dict = config_metadata_dict.copy()
        config_dict["intervalo"] = "1h"
        config = ProductionConfig(
            **config_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def provider(self, production_config, fitted_scaler):
        """Fixture del provider."""
        return DataProviderPolling(production_config, fitted_scaler)
    
    @pytest.mark.asyncio
    async def test_stream_velas_error_critico_para_sistema(self, provider):
        """Test: stream_velas para el sistema si hay error crítico."""
        mock_client = AsyncMock()
        mock_client.futures_klines.return_value = []  # Siempre falla
        
        provider.client = mock_client
        provider.inicializado = True
        
        # Mock time_sync y wait
        mock_time_sync = Mock()
        mock_time_sync.get_binance_time.return_value = datetime.now()
        mock_time_sync.should_resync.return_value = False
        provider.time_sync = mock_time_sync
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="CRÍTICO"):
                async for _ in provider.stream_velas():
                    pass
    
    @pytest.mark.asyncio
    async def test_stream_velas_recupera_despues_reintentos(self, provider, mock_klines_progreso):
        """Test: stream_velas recupera después de algunos reintentos."""
        mock_client = AsyncMock()
        
        # Primer ciclo: falla 2 veces y luego éxito
        mock_client.futures_klines.side_effect = [
            [],  # Falla 1
            [],  # Falla 2
            mock_klines_progreso,  # Éxito
        ]
        
        provider.client = mock_client
        provider.inicializado = True
        provider.df_ventana = pd.DataFrame({
            'open': [50000], 'high': [50100], 'low': [49900],
            'close': [50000], 'volume': [100]
        })
        
        # Mock time_sync
        mock_time_sync = Mock()
        mock_time_sync.get_binance_time.return_value = datetime.now()
        mock_time_sync.should_resync.return_value = False
        provider.time_sync = mock_time_sync
        
        vela_count = 0
        with patch('asyncio.sleep', new_callable=AsyncMock):
            async for vela in provider.stream_velas():
                assert vela is not None
                assert vela['is_closed'] is True
                vela_count += 1
                if vela_count >= 1:
                    break
        
        # Debe haber obtenido la vela después de reintentos
        assert vela_count == 1
        assert mock_client.futures_klines.call_count == 3


class TestDataProviderPollingEdgeCases:
    """Tests de casos extremos."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración."""
        config_dict = config_metadata_dict.copy()
        config_dict["intervalo"] = "1h"
        config = ProductionConfig(
            **config_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def provider(self, production_config, fitted_scaler):
        """Fixture del provider."""
        return DataProviderPolling(production_config, fitted_scaler)
    
    @pytest.mark.asyncio
    async def test_binance_api_exception_reintenta(self, provider):
        """Test: Maneja BinanceAPIException y reintenta."""
        from binance.exceptions import BinanceAPIException
        
        mock_client = AsyncMock()
        
        # Primeros 2 intentos: excepción, tercero: éxito
        now_ms = int(datetime.now().timestamp() * 1000)
        mock_klines = [
            [now_ms - 3600000, "50000", "50100", "49900", "50050", "100",
             now_ms - 3600000 + 3599999, "5000000", 500, "50", "2500000", "ignore"],
            [now_ms, "50050", "50150", "49950", "50100", "105",
             now_ms + 3599999, "5250000", 520, "52", "2625000", "ignore"]
        ]
        
        # Crear una excepción BinanceAPIException válida con un response mock
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "Error temporal"}'
        api_exception = BinanceAPIException(mock_response, -1001, mock_response.text)
        
        mock_client.futures_klines.side_effect = [
            api_exception,
            api_exception,
            mock_klines,
        ]
        
        provider.client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            vela = await provider._fetch_latest_closed_candle()
        
        assert vela is not None
        assert mock_client.futures_klines.call_count == 3
    
    @pytest.mark.asyncio
    async def test_exception_generica_reintenta(self, provider, mock_klines_progreso):
        """Test: Maneja excepciones genéricas y reintenta."""
        mock_client = AsyncMock()
        
        # Primeros 2 intentos: excepción genérica, tercero: éxito
        mock_client.futures_klines.side_effect = [
            Exception("Error de red"),
            Exception("Timeout"),
            mock_klines_progreso,
        ]
        
        provider.client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            vela = await provider._fetch_latest_closed_candle()
        
        assert vela is not None
        assert mock_client.futures_klines.call_count == 3
    
    def test_intervalo_segundos_correctos(self):
        """Test: Verifica mapeo correcto de intervalos a segundos."""
        assert DataProviderPolling.INTERVAL_TO_SECONDS['1m'] == 60
        assert DataProviderPolling.INTERVAL_TO_SECONDS['5m'] == 300
        assert DataProviderPolling.INTERVAL_TO_SECONDS['15m'] == 900
        assert DataProviderPolling.INTERVAL_TO_SECONDS['1h'] == 3600
        assert DataProviderPolling.INTERVAL_TO_SECONDS['4h'] == 14400
        assert DataProviderPolling.INTERVAL_TO_SECONDS['1d'] == 86400


# Conftest local fixtures si no están en conftest.py global
@pytest.fixture
def mock_klines_progreso():
    """Mock de klines globales."""
    now_ms = int(datetime.now().timestamp() * 1000)
    return [
        [
            now_ms - 3600000,
            "50000", "50100", "49900", "50050",
            "100",
            now_ms - 3600000 + 3599999,
            "5000000", 500, "50", "2500000", "ignore"
        ],
        [
            now_ms,
            "50050", "50150", "49950", "50100",
            "105",
            now_ms + 3599999,
            "5250000", 520, "52", "2625000", "ignore"
        ]
    ]
