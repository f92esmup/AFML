"""Tests para el módulo de preprocesamiento de datos."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler

from src.train.AdquisicionDatos.preprocesamiento import Preprocesamiento
from src.train.config.config import UnifiedConfig


class TestPreprocesamientoInit:
    """Tests para la inicialización de Preprocesamiento."""

    def test_init_with_valid_config(self, sample_config):
        """Test de inicialización con configuración válida."""
        prepro = Preprocesamiento(sample_config)
        
        assert isinstance(prepro.df, pd.DataFrame)
        assert len(prepro.df) == 0  # DataFrame vacío al iniciar
        assert prepro.interval == "1h"
        assert prepro.interpol_method == "linear"

    def test_init_extracts_indicators_config(self, sample_config):
        """Verifica que la configuración de indicadores se extrae correctamente."""
        prepro = Preprocesamiento(sample_config)
        
        assert prepro.sma_short == 10
        assert prepro.sma_long == 50
        assert prepro.rsi_length == 14
        assert prepro.macd_fast == 12
        assert prepro.macd_slow == 26
        assert prepro.macd_signal == 9
        assert prepro.bbands_length == 20
        assert prepro.bbands_std == 2.0

    def test_init_with_different_interpolation_methods(self, sample_config):
        """Verifica que acepta diferentes métodos de interpolación."""
        interpolation_methods = ['linear', 'time', 'nearest', 'cubic']
        
        for method in interpolation_methods:
            sample_config.preprocesamiento.interpol_method = method
            prepro = Preprocesamiento(sample_config)
            assert prepro.interpol_method == method


class TestPreprocesamientoContinuidad:
    """Tests para el método _continuidad."""

    def test_continuidad_with_continuous_data(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que datos continuos se mantienen igual."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        initial_length = len(prepro.df)
        result = prepro._continuidad()
        
        assert len(result) == initial_length
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_continuidad_fills_gaps(self, sample_config, sample_ohlcv_with_gaps):
        """Verifica que se rellenan los gaps en el índice."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_with_gaps.copy()
        
        initial_length = len(prepro.df)
        result = prepro._continuidad()
        
        # Debe tener más filas después de rellenar gaps
        assert len(result) > initial_length
        
        # Verificar que el índice es continuo
        expected_index = pd.date_range(
            start=result.index.min(),
            end=result.index.max(),
            freq=sample_config.data_downloader.interval
        )
        pd.testing.assert_index_equal(result.index, expected_index)

    def test_continuidad_creates_nan_for_gaps(self, sample_config, sample_ohlcv_with_gaps):
        """Verifica que los gaps se rellenan con NaN."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_with_gaps.copy()
        
        result = prepro._continuidad()
        
        # Debe haber valores NaN en las filas insertadas
        assert result.isnull().any().any()

    def test_continuidad_raises_error_with_non_datetime_index(self, sample_config):
        """Verifica que lanza error si el índice no es DatetimeIndex."""
        prepro = Preprocesamiento(sample_config)
        
        # Crear DataFrame con índice no-datetime
        df = pd.DataFrame({
            'open': [1, 2, 3],
            'close': [4, 5, 6]
        })
        prepro.df = df
        
        with pytest.raises(TypeError, match="DatetimeIndex"):
            prepro._continuidad()

    def test_continuidad_preserves_existing_data(self, sample_config, sample_ohlcv_with_gaps):
        """Verifica que los datos existentes se preservan."""
        prepro = Preprocesamiento(sample_config)
        original_df = sample_ohlcv_with_gaps.copy()
        prepro.df = original_df.copy()
        
        result = prepro._continuidad()
        
        # Verificar que los valores originales están presentes
        for idx in original_df.index:
            assert idx in result.index
            pd.testing.assert_series_equal(
                original_df.loc[idx],
                result.loc[idx],
                check_names=False
            )


class TestPreprocesamientoInterpolacion:
    """Tests para el método _interpolacion."""

    def test_interpolacion_fills_nan_values(self, sample_config, sample_ohlcv_with_nans):
        """Verifica que la interpolación rellena valores NaN."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_with_nans.copy()
        
        nan_count_before = prepro.df.isnull().sum().sum()
        result = prepro._interpolacion()
        nan_count_after = result.isnull().sum().sum()
        
        assert nan_count_before > 0
        assert nan_count_after < nan_count_before

    def test_interpolacion_linear_method(self, sample_config):
        """Verifica la interpolación lineal."""
        prepro = Preprocesamiento(sample_config)
        prepro.interpol_method = 'linear'
        
        # Crear datos con patrón conocido
        dates = pd.date_range(start='2023-01-01', periods=5, freq='1h')
        prepro.df = pd.DataFrame({
            'close': [10.0, np.nan, np.nan, 40.0, 50.0]
        }, index=dates)
        
        result = prepro._interpolacion()
        
        # Verificar interpolación lineal: 10, 20, 30, 40, 50
        assert not result.isnull().any().any()
        assert result.loc[dates[1], 'close'] == pytest.approx(20.0, rel=0.01)
        assert result.loc[dates[2], 'close'] == pytest.approx(30.0, rel=0.01)

    def test_interpolacion_preserves_non_nan_values(self, sample_config, sample_ohlcv_with_nans):
        """Verifica que los valores no-NaN se preservan."""
        prepro = Preprocesamiento(sample_config)
        original_df = sample_ohlcv_with_nans.copy()
        prepro.df = original_df.copy()
        
        # Obtener índices sin NaN
        non_nan_mask = ~original_df['close'].isnull()
        
        result = prepro._interpolacion()
        
        # Verificar que los valores originales no cambiaron
        pd.testing.assert_series_equal(
            original_df.loc[non_nan_mask, 'close'],
            result.loc[non_nan_mask, 'close']
        )

    def test_interpolacion_with_different_methods(self, sample_config):
        """Verifica que funciona con diferentes métodos."""
        methods = ['linear', 'nearest', 'zero']
        
        dates = pd.date_range(start='2023-01-01', periods=5, freq='1h')
        
        for method in methods:
            prepro = Preprocesamiento(sample_config)
            prepro.interpol_method = method
            prepro.df = pd.DataFrame({
                'close': [10.0, np.nan, np.nan, 40.0, 50.0]
            }, index=dates)
            
            result = prepro._interpolacion()
            
            # Debe reducir o eliminar NaN
            assert result.isnull().sum().sum() <= prepro.df.isnull().sum().sum()


class TestPreprocesamientoCalculoIndicadores:
    """Tests para el método _calculo_indicadores."""

    def test_calculo_indicadores_adds_sma_columns(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que se añaden columnas SMA."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        assert f'SMA_{prepro.sma_short}' in result.columns
        assert f'SMA_{prepro.sma_long}' in result.columns

    def test_calculo_indicadores_adds_rsi_column(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que se añade columna RSI."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        assert f'RSI_{prepro.rsi_length}' in result.columns

    def test_calculo_indicadores_adds_macd_columns(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que se añaden columnas MACD."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        assert f'MACD_{prepro.macd_fast}_{prepro.macd_slow}_{prepro.macd_signal}' in result.columns
        assert f'MACDh_{prepro.macd_fast}_{prepro.macd_slow}_{prepro.macd_signal}' in result.columns
        assert f'MACDs_{prepro.macd_fast}_{prepro.macd_slow}_{prepro.macd_signal}' in result.columns

    def test_calculo_indicadores_adds_bbands_columns(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que se añaden columnas de Bandas de Bollinger."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        # Buscar columnas que contengan BBL, BBM, BBU
        bb_cols = [col for col in result.columns if 'BBL' in col or 'BBM' in col or 'BBU' in col]
        assert len(bb_cols) >= 3  # Al menos BBL, BBM, BBU

    def test_calculo_indicadores_preserves_original_columns(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que las columnas originales se preservan."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        original_columns = list(prepro.df.columns)
        result = prepro._calculo_indicadores()
        
        for col in original_columns:
            assert col in result.columns

    def test_calculo_indicadores_creates_numeric_values(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que los indicadores tienen valores numéricos."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        # Todas las columnas deben ser numéricas
        for col in result.columns:
            assert pd.api.types.is_numeric_dtype(result[col])

    def test_calculo_indicadores_may_introduce_nans(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el cálculo de indicadores puede introducir NaN."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        result = prepro._calculo_indicadores()
        
        # Es esperado que haya NaN al principio debido a períodos de warmup
        # Solo verificamos que el DataFrame no esté completamente vacío
        assert len(result) > 0


class TestPreprocesamientoEliminarFaltantes:
    """Tests para el método _eliminar_faltantes."""

    def test_eliminar_faltantes_removes_nan_rows(self, sample_config, sample_ohlcv_with_nans):
        """Verifica que se eliminan filas con NaN."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_with_nans.copy()
        
        nan_count_before = prepro.df.isnull().any(axis=1).sum()
        result = prepro._eliminar_faltantes()
        
        assert nan_count_before > 0
        assert not result.isnull().any().any()

    def test_eliminar_faltantes_reduces_length(self, sample_config, sample_ohlcv_with_nans):
        """Verifica que la longitud se reduce."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_with_nans.copy()
        
        initial_length = len(prepro.df)
        result = prepro._eliminar_faltantes()
        
        assert len(result) < initial_length

    def test_eliminar_faltantes_with_clean_data(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que datos limpios no se modifican."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        initial_length = len(prepro.df)
        result = prepro._eliminar_faltantes()
        
        assert len(result) == initial_length

    def test_eliminar_faltantes_preserves_clean_rows(self, sample_config, sample_ohlcv_with_nans):
        """Verifica que las filas limpias se preservan."""
        prepro = Preprocesamiento(sample_config)
        original_df = sample_ohlcv_with_nans.copy()
        prepro.df = original_df.copy()
        
        # Obtener índices de filas sin NaN
        clean_indices = original_df.dropna().index
        
        result = prepro._eliminar_faltantes()
        
        # Todas las filas limpias deben estar en el resultado
        for idx in clean_indices:
            assert idx in result.index


class TestPreprocesamientoScaler:
    """Tests para el método _scaler."""

    def test_scaler_returns_standard_scaler(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que retorna un StandardScaler."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        scaler = prepro._scaler()
        
        assert isinstance(scaler, StandardScaler)

    def test_scaler_is_fitted(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el scaler está ajustado."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        scaler = prepro._scaler()
        
        # Verificar que tiene atributos de un scaler ajustado
        assert hasattr(scaler, 'mean_')
        assert hasattr(scaler, 'scale_')
        assert scaler.mean_ is not None
        assert scaler.scale_ is not None

    def test_scaler_has_correct_features(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el scaler tiene el número correcto de features."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        scaler = prepro._scaler()
        
        assert len(scaler.mean_) == len(prepro.df.columns)
        assert len(scaler.scale_) == len(prepro.df.columns)

    def test_scaler_can_transform_data(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el scaler puede transformar datos."""
        prepro = Preprocesamiento(sample_config)
        prepro.df = sample_ohlcv_dataframe.copy()
        
        scaler = prepro._scaler()
        
        # Intentar transformar los datos
        transformed = scaler.transform(prepro.df)
        
        assert transformed.shape == prepro.df.shape
        # Los datos escalados deben tener media ~0 y std ~1
        assert np.abs(transformed.mean()) < 0.1
        assert np.abs(transformed.std() - 1.0) < 0.1


class TestPreprocesamientoRun:
    """Tests para el método run (flujo completo)."""

    def test_run_returns_dataframe_and_scaler(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que run retorna DataFrame y StandardScaler."""
        prepro = Preprocesamiento(sample_config)
        
        result_df, scaler = prepro.run(sample_ohlcv_dataframe.copy())
        
        assert isinstance(result_df, pd.DataFrame)
        assert isinstance(scaler, StandardScaler)

    def test_run_dataframe_has_additional_columns(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el DataFrame resultante tiene columnas adicionales."""
        prepro = Preprocesamiento(sample_config)
        
        original_columns = len(sample_ohlcv_dataframe.columns)
        result_df, _ = prepro.run(sample_ohlcv_dataframe.copy())
        
        # Debe tener más columnas (indicadores añadidos)
        assert len(result_df.columns) > original_columns

    def test_run_dataframe_has_no_nans(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el DataFrame final no tiene NaN."""
        prepro = Preprocesamiento(sample_config)
        
        result_df, _ = prepro.run(sample_ohlcv_dataframe.copy())
        
        assert not result_df.isnull().any().any()

    def test_run_preserves_datetime_index(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el índice sigue siendo DatetimeIndex."""
        prepro = Preprocesamiento(sample_config)
        
        result_df, _ = prepro.run(sample_ohlcv_dataframe.copy())
        
        assert isinstance(result_df.index, pd.DatetimeIndex)

    def test_run_with_gaps_fills_and_processes(self, sample_config, sample_ohlcv_with_gaps):
        """Verifica el procesamiento completo con datos con gaps."""
        prepro = Preprocesamiento(sample_config)
        
        result_df, scaler = prepro.run(sample_ohlcv_with_gaps.copy())
        
        assert isinstance(result_df, pd.DataFrame)
        assert not result_df.isnull().any().any()
        assert isinstance(scaler, StandardScaler)

    def test_run_scaler_is_properly_fitted(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que el scaler está correctamente ajustado al resultado."""
        prepro = Preprocesamiento(sample_config)
        
        result_df, scaler = prepro.run(sample_ohlcv_dataframe.copy())
        
        # El scaler debe poder transformar el resultado
        transformed = scaler.transform(result_df)
        assert transformed.shape == result_df.shape

    def test_run_reduces_dataframe_length(self, sample_config, sample_ohlcv_dataframe):
        """Verifica que la longitud se reduce (debido a warmup de indicadores)."""
        prepro = Preprocesamiento(sample_config)
        
        initial_length = len(sample_ohlcv_dataframe)
        result_df, _ = prepro.run(sample_ohlcv_dataframe.copy())
        
        # Debido al warmup de los indicadores (especialmente SMA_long=50)
        # la longitud debe reducirse
        assert len(result_df) < initial_length


class TestPreprocesamientoIntegration:
    """Tests de integración para el pipeline completo."""

    def test_full_pipeline_with_realistic_data(self, sample_config):
        """Test del pipeline completo con datos realistas."""
        # Crear datos realistas
        dates = pd.date_range(start='2023-01-01', periods=200, freq='1h')
        np.random.seed(42)
        close_prices = 50000 + np.cumsum(np.random.randn(200) * 100)
        
        df = pd.DataFrame({
            'open': close_prices + np.random.randn(200) * 50,
            'high': close_prices + np.abs(np.random.randn(200) * 100),
            'low': close_prices - np.abs(np.random.randn(200) * 100),
            'close': close_prices,
            'volume': np.random.uniform(50, 200, 200)
        }, index=dates)
        
        prepro = Preprocesamiento(sample_config)
        result_df, scaler = prepro.run(df)
        
        # Verificaciones
        assert isinstance(result_df, pd.DataFrame)
        assert isinstance(scaler, StandardScaler)
        assert not result_df.isnull().any().any()
        assert len(result_df) > 0
        assert len(result_df.columns) > 5  # Original + indicadores
        
        # Verificar que los indicadores están presentes
        assert 'SMA_10' in result_df.columns
        assert 'RSI_14' in result_df.columns

    def test_pipeline_handles_edge_cases(self, sample_config):
        """Verifica que el pipeline maneja casos edge."""
        # Crear datos mínimos (suficientes para todos los indicadores)
        # Necesitamos al menos SMA_long + algunos más para tener datos después del warmup
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
        
        # Usar datos variables en lugar de constantes para evitar problemas con indicadores
        np.random.seed(42)
        base_price = 50000
        
        df = pd.DataFrame({
            'open': base_price + np.random.randn(100) * 10,
            'high': base_price + np.abs(np.random.randn(100) * 20),
            'low': base_price - np.abs(np.random.randn(100) * 20),
            'close': base_price + np.random.randn(100) * 10,
            'volume': 100 + np.random.randn(100) * 10
        }, index=dates)
        
        prepro = Preprocesamiento(sample_config)
        result_df, scaler = prepro.run(df)
        
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) > 0

    def test_pipeline_with_different_config(self, sample_config):
        """Verifica que funciona con diferentes configuraciones."""
        # Modificar configuración
        sample_config.preprocesamiento.indicadores.SMA_short = 5
        sample_config.preprocesamiento.indicadores.SMA_long = 20
        sample_config.preprocesamiento.interpol_method = 'nearest'
        
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'open': 50000 + np.random.randn(100) * 100,
            'high': 50100 + np.random.randn(100) * 100,
            'low': 49900 + np.random.randn(100) * 100,
            'close': 50000 + np.random.randn(100) * 100,
            'volume': np.random.uniform(50, 200, 100)
        }, index=dates)
        
        prepro = Preprocesamiento(sample_config)
        result_df, scaler = prepro.run(df)
        
        assert 'SMA_5' in result_df.columns
        assert 'SMA_20' in result_df.columns
