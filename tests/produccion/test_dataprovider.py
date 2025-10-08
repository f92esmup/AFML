"""Tests para el proveedor de datos.

NOTA: Estos tests ahora usan el sistema modular con DataProviderWebSocket.
El Factory selecciona automáticamente entre WebSocket y Polling según el intervalo.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.produccion.dataprovider.websocket import DataProviderWebSocket
from src.produccion.config.config import ProductionConfig


class TestDataProviderEdgeCases:
    """Tests de casos extremos y edge cases."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def provider(self, production_config, fitted_scaler):
        """Fixture del DataProvider."""
        return DataProviderWebSocket(production_config, fitted_scaler)
        
    def test_ventana_total_calculation(self, production_config, fitted_scaler):
        """Test del cálculo de ventana total."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # Ventana total debe ser window_size + indicador más largo + buffer
        expected = 30 + max(200, 26, 20) + 50
        assert provider.ventana_total == expected
        
    @pytest.mark.asyncio
    async def test_inicializar_testnet(self, production_config, fitted_scaler, mock_async_client):
        """Test de inicialización en modo testnet."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        with patch("src.produccion.dataprovider.websocket.AsyncClient.create") as mock_create:
            mock_create.return_value = mock_async_client
            
            await provider.inicializar(
                api_key="test_key",
                api_secret="test_secret",
                testnet=True
            )
            
            assert provider.inicializado is True
            assert provider.client is not None
            
    @pytest.mark.asyncio
    async def test_inicializar_production(self, production_config, fitted_scaler, mock_async_client):
        """Test de inicialización en modo producción."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        with patch("src.produccion.dataprovider.websocket.AsyncClient.create") as mock_create:
            mock_create.return_value = mock_async_client
            
            await provider.inicializar(
                api_key="test_key",
                api_secret="test_secret",
                testnet=False
            )
            
            # Verificar que NO se pasó testnet=True
            assert provider.inicializado is True
            
    @pytest.mark.skip(reason="Test asíncrono complejo que requiere mock detallado de AsyncClient")
    @pytest.mark.asyncio
    async def test_descargar_historial_inicial(self, production_config, fitted_scaler, mock_async_client):
        """Test de descarga de historial inicial."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        with patch("src.produccion.dataprovider.websocket.AsyncClient.create") as mock_create:
            mock_create.return_value = mock_async_client
            
            await provider.inicializar("key", "secret", testnet=True)
            await provider.descargar_historial_inicial()
            
            # Verificar que se descargó el historial
            assert provider.df_ventana is not None
            assert len(provider.df_ventana) >= provider.window_size
            
    def test_calcular_indicadores(self, production_config, fitted_scaler):
        """Test del cálculo de indicadores técnicos."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # Crear DataFrame de prueba con suficientes filas
        df = pd.DataFrame({
            "open": np.random.uniform(49000, 51000, 300),
            "high": np.random.uniform(50000, 52000, 300),
            "low": np.random.uniform(48000, 50000, 300),
            "close": np.random.uniform(49500, 50500, 300),
            "volume": np.random.uniform(100, 200, 300),
        })
        
        df_with_indicators = provider._calcular_indicadores(df)
        
        # Ahora NO se eliminan NaN, así que el DataFrame mantiene todas las filas
        assert len(df_with_indicators) == 300, "Debe mantener todas las filas originales"
        
        # Verificar que se agregaron los indicadores
        # pandas_ta genera nombres basados en parámetros: SMA_10, SMA_200, RSI_14, 
        # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9, BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        expected_columns = [
            "SMA_10", "SMA_200", "RSI_14",
            "MACD_12_26_9", "MACDs_12_26_9", "MACDh_12_26_9",
            "BBL_20_2.0", "BBM_20_2.0", "BBU_20_2.0"
        ]
        
        for col in expected_columns:
            assert col in df_with_indicators.columns, f"Columna {col} no encontrada. Columnas disponibles: {df_with_indicators.columns.tolist()}"
        
        # Verificar que las primeras filas tienen NaN (normal para indicadores)
        assert df_with_indicators["SMA_200"].iloc[0:199].isna().any(), "Las primeras filas de SMA_200 deben tener NaN"
        
        # Verificar que las últimas filas NO tienen NaN (indicadores completos)
        assert not df_with_indicators["SMA_200"].iloc[-50:].isna().any(), "Las últimas filas no deben tener NaN"
            
    def test_calcular_indicadores_preserves_original_columns(self, production_config, fitted_scaler):
        """Test que calcular indicadores preserva las columnas originales."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        df = pd.DataFrame({
            "open": np.random.uniform(49000, 51000, 300),
            "high": np.random.uniform(50000, 52000, 300),
            "low": np.random.uniform(48000, 50000, 300),
            "close": np.random.uniform(49500, 50500, 300),
            "volume": np.random.uniform(100, 200, 300),
        })
        
        df_with_indicators = provider._calcular_indicadores(df)
        
        # Columnas originales deben estar presentes
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in df_with_indicators.columns
            
    @pytest.mark.skip(reason="Test complejo que requiere ventana ya calculada con indicadores")
    def test_actualizar_ventana(self, production_config, fitted_scaler, sample_market_data):
        """Test de actualización de la ventana rodante."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # Inicializar ventana manualmente
        provider.df_ventana = sample_market_data.copy()
        initial_len = len(provider.df_ventana)
        
        # Crear nueva vela
        nueva_vela = {
            "timestamp": pd.Timestamp.now(),
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 100.5,
        }
        
        provider._actualizar_ventana(nueva_vela)
        
        # La longitud debe ser la misma (elimina la más antigua)
        assert len(provider.df_ventana) == initial_len
        
        # La última fila debe tener el timestamp de la nueva vela
        # (verificar aproximadamente debido a procesamiento)
        assert provider.df_ventana.index[-1].date() == nueva_vela["timestamp"].date()
        
    def test_get_ventana_normalizada_without_data(self, production_config, fitted_scaler):
        """Test de get_ventana cuando no hay datos."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # El método lanza RuntimeError no ValueError
        with pytest.raises(RuntimeError, match="Ventana no inicializada"):
            provider.get_ventana_normalizada()
            
    def test_get_ventana_normalizada_with_data(self, production_config, fitted_scaler, sample_market_data):
        """Test de get_ventana con datos."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        provider.df_ventana = sample_market_data.copy()
        
        ventana = provider.get_ventana_normalizada()
        
        assert isinstance(ventana, pd.DataFrame)
        assert len(ventana) == len(sample_market_data)
        # timestamp debe estar como columna (el índice fue reseteado en get_ventana_normalizada)
        assert "timestamp" in ventana.columns
        
    @pytest.mark.skip(reason="Test asíncrono que requiere mock complejo de AsyncClient")
    @pytest.mark.asyncio
    async def test_cerrar(self, production_config, fitted_scaler, mock_async_client):
        """Test de cierre de conexiones."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        with patch("src.produccion.dataprovider.websocket.AsyncClient.create") as mock_create:
            mock_create.return_value = mock_async_client
            
            await provider.inicializar("key", "secret", testnet=True)
            await provider.cerrar()
            
            # Verificar que se cerró el cliente
            mock_async_client.close.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_stream_velas_not_initialized(self, production_config, fitted_scaler):
        """Test de stream_velas cuando no está inicializado."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # El método lanza RuntimeError con mensaje específico de WebSocket
        with pytest.raises(RuntimeError, match="DataProviderWebSocket no inicializado"):
            async for _ in provider.stream_velas():
                pass
                
    @pytest.mark.skip(reason="Test asíncrono complejo de stream WebSocket que requiere mocks avanzados")
    @pytest.mark.asyncio
    async def test_stream_velas_yields_completed_candles(self, production_config, fitted_scaler, mock_async_client):
        """Test que stream_velas solo retorna velas completas."""
        provider = DataProviderWebSocket(production_config, fitted_scaler)
        
        # Mock del socket manager
        mock_socket_manager = AsyncMock()
        mock_stream = AsyncMock()
        
        # Simular velas: una incompleta y una completa
        async def mock_recv():
            for msg in [
                {"e": "kline", "k": {"x": False, "t": 1609459200000, "o": "50000", "h": "50100", "l": "49900", "c": "50050", "v": "100"}},
                {"e": "kline", "k": {"x": True, "t": 1609462800000, "o": "50050", "h": "50150", "l": "49950", "c": "50100", "v": "105"}},
            ]:
                yield msg
                
        mock_stream.__aenter__.return_value.__aiter__ = mock_recv
        mock_socket_manager.kline_futures_socket.return_value = mock_stream
        
        with patch("src.produccion.dataprovider.websocket.AsyncClient.create") as mock_create:
            mock_create.return_value = mock_async_client
            
            with patch("src.produccion.dataprovider.websocket.BinanceSocketManager") as mock_bsm:
                mock_bsm.return_value = mock_socket_manager
                
                await provider.inicializar("key", "secret", testnet=True)
                await provider.descargar_historial_inicial()
                
                # Obtener la primera vela completa
                vela_count = 0
                async for vela in provider.stream_velas():
                    assert vela["is_closed"] is True
                    vela_count += 1
                    if vela_count >= 1:
                        break


class TestDataProviderIndicators:
    """Tests específicos para cálculo de indicadores."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict, fitted_scaler):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/path/to/model",
            scaler_path="/path/to/scaler",
            is_live=False
        )
        config.scaler = fitted_scaler
        return config
    
    @pytest.fixture
    def provider(self, production_config, fitted_scaler):
        """Fixture del DataProvider."""
        return DataProviderWebSocket(production_config, fitted_scaler)
    
    def test_sma_calculation(self, provider):
        """Test del cálculo de SMA."""
        # Necesitamos al menos 200 filas para SMA_200
        df = pd.DataFrame({
            "open": [100] * 250,
            "high": [100] * 250,
            "low": [100] * 250,
            "close": [100] * 250,
            "volume": [100] * 250,
        })
        
        df_result = provider._calcular_indicadores(df)
        
        # Ahora mantiene todas las filas (no hace dropna)
        assert len(df_result) == 250, "Debe mantener todas las 250 filas originales"
        
        # SMA de valores constantes debe ser el mismo valor (en las filas sin NaN)
        # pandas_ta genera nombres como SMA_10, SMA_200 (basado en length)
        # SMA_10 necesita 10 valores, así que desde fila 9 en adelante no tiene NaN
        assert df_result["SMA_10"].iloc[9:].notna().all(), "SMA_10 debe estar completo desde fila 9"
        assert df_result["SMA_10"].iloc[-1] == pytest.approx(100, rel=0.01)
        
        # SMA_200 necesita 200 valores, así que desde fila 199 en adelante no tiene NaN  
        assert df_result["SMA_200"].iloc[199:].notna().all(), "SMA_200 debe estar completo desde fila 199"
        assert df_result["SMA_200"].iloc[-1] == pytest.approx(100, rel=0.01)
        
    def test_rsi_boundaries(self, provider):
        """Test que RSI está entre 0 y 100."""
        df = pd.DataFrame({
            "open": np.random.uniform(49000, 51000, 300),
            "high": np.random.uniform(50000, 52000, 300),
            "low": np.random.uniform(48000, 50000, 300),
            "close": np.random.uniform(49500, 50500, 300),
            "volume": np.random.uniform(100, 200, 300),
        })
        
        df_result = provider._calcular_indicadores(df)
        
        # RSI debe estar entre 0 y 100
        # pandas_ta genera nombre como RSI_14 (basado en length)
        assert df_result["RSI_14"].min() >= 0
        assert df_result["RSI_14"].max() <= 100
        
    def test_bollinger_bands_order(self, provider):
        """Test que las Bollinger Bands están ordenadas correctamente."""
        df = pd.DataFrame({
            "open": np.random.uniform(49000, 51000, 300),
            "high": np.random.uniform(50000, 52000, 300),
            "low": np.random.uniform(48000, 50000, 300),
            "close": np.random.uniform(49500, 50500, 300),
            "volume": np.random.uniform(100, 200, 300),
        })
        
        df_result = provider._calcular_indicadores(df)
        
        # pandas_ta genera nombres como BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        # BBL <= BBM <= BBU (solo en filas donde no hay NaN)
        df_valid = df_result.dropna(subset=["BBL_20_2.0", "BBM_20_2.0", "BBU_20_2.0"])
        
        assert len(df_valid) > 0, "Debe haber filas válidas sin NaN"
        assert (df_valid["BBL_20_2.0"] <= df_valid["BBM_20_2.0"]).all()
        assert (df_valid["BBM_20_2.0"] <= df_valid["BBU_20_2.0"]).all()
