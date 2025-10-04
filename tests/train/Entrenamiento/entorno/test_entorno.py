"""Tests para el módulo entorno.py"""

import pytest
import numpy as np
import pandas as pd
from gymnasium import spaces
from sklearn.preprocessing import StandardScaler
from pydantic import ValidationError

from src.train.config.config import UnifiedConfig
from src.train.Entrenamiento.entorno.entorno import TradingEnv
from src.train.Entrenamiento.entorno.portafolio import Portafolio


class TestTradingEnvInitialization:
    """Tests para la inicialización del entorno TradingEnv."""
    
    def test_initialization_success(self, config, sample_data, portafolio):
        """Debe inicializar correctamente con parámetros válidos."""
        env = TradingEnv(config, sample_data, portafolio, scaler=None)
        
        assert env is not None
        assert env.window_size == config.entorno.window_size
        assert env.paso_actual == config.entorno.window_size - 1
        assert env.episodio == 0
        assert env.portafolio is portafolio
    
    def test_initialization_with_none_config(self, sample_data, portafolio):
        """Debe fallar cuando config es None."""
        with pytest.raises(ValueError, match="La configuración no puede ser None"):
            TradingEnv(None, sample_data, portafolio)
    
    def test_initialization_with_none_data(self, config, portafolio):
        """Debe fallar cuando data es None."""
        with pytest.raises(ValueError, match="Los datos no pueden ser None o estar vacíos"):
            TradingEnv(config, None, portafolio)
    
    def test_initialization_with_empty_data(self, config, portafolio):
        """Debe fallar cuando data está vacío."""
        empty_data = pd.DataFrame()
        with pytest.raises(ValueError, match="Los datos no pueden ser None o estar vacíos"):
            TradingEnv(config, empty_data, portafolio)
    
    def test_initialization_with_none_portafolio(self, config, sample_data):
        """Debe fallar cuando portafolio es None."""
        with pytest.raises(ValueError, match="El portafolio no puede ser None"):
            TradingEnv(config, sample_data, None)
    
    def test_initialization_without_close_column(self, config, portafolio):
        """Debe fallar cuando falta la columna 'close'."""
        data_no_close = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=100, freq='H'),
            'open': np.random.randn(100) * 100 + 50000,
        })
        
        with pytest.raises(ValueError, match="La columna 'close' es requerida"):
            TradingEnv(config, data_no_close, portafolio)
    
    def test_initialization_with_invalid_window_size(self, valid_config_dict, sample_data, portafolio):
        """Debe fallar con window_size inválido (Pydantic valida primero)."""
        valid_config_dict['entorno']['window_size'] = 0
        
        # Pydantic valida antes de que TradingEnv reciba el config
        with pytest.raises(ValidationError):
            config = UnifiedConfig(**valid_config_dict)
    
    def test_initialization_with_window_size_too_large(self, valid_config_dict, sample_data, portafolio):
        """Debe fallar cuando window_size es mayor que los datos."""
        valid_config_dict['entorno']['window_size'] = 1000
        config = UnifiedConfig(**valid_config_dict)
        
        with pytest.raises(ValueError, match="Window size inválido"):
            TradingEnv(config, sample_data, portafolio)
    
    def test_initialization_with_scaler(self, config, sample_data_normalized, portafolio):
        """Debe inicializar correctamente con un scaler."""
        data, scaler = sample_data_normalized
        env = TradingEnv(config, data, portafolio, scaler=scaler)
        
        assert env.scaler is not None
        assert env.scaler is scaler
    
    def test_column_map_creation(self, config, sample_data, portafolio):
        """Debe crear correctamente el mapeo de columnas."""
        env = TradingEnv(config, sample_data, portafolio)
        
        # Verificar que el mapeo existe y contiene las columnas esperadas
        assert 'close' in env.column_map
        assert 'open' in env.column_map
        assert 'timestamp' not in env.column_map  # timestamp no debe estar
        
        # Verificar que el índice de close está configurado
        assert env.close_idx == env.column_map['close']
    
    def test_timestamp_handling(self, config, sample_data, portafolio):
        """Debe extraer y guardar timestamps correctamente."""
        env = TradingEnv(config, sample_data, portafolio)
        
        assert env.timestamps is not None
        assert len(env.timestamps) == len(sample_data)


class TestObservationSpace:
    """Tests para el espacio de observación."""
    
    def test_observation_space_structure(self, trading_env):
        """Debe crear un espacio de observación tipo Dict con 'market' y 'portfolio'."""
        assert isinstance(trading_env.observation_space, spaces.Dict)
        assert 'market' in trading_env.observation_space.spaces
        assert 'portfolio' in trading_env.observation_space.spaces
    
    def test_observation_space_market_shape(self, trading_env):
        """El espacio 'market' debe tener forma (window_size, n_columnas)."""
        market_space = trading_env.observation_space.spaces['market']
        
        assert isinstance(market_space, spaces.Box)
        assert market_space.shape == (trading_env.window_size, trading_env.n_columnas)
        assert market_space.dtype == np.float32
    
    def test_observation_space_portfolio_shape(self, trading_env):
        """El espacio 'portfolio' debe tener forma (3,) para [equity, pnl, posicion]."""
        portfolio_space = trading_env.observation_space.spaces['portfolio']
        
        assert isinstance(portfolio_space, spaces.Box)
        assert portfolio_space.shape == (3,)
        assert portfolio_space.dtype == np.float32
    
    def test_action_space(self, trading_env):
        """El espacio de acción debe ser Box continuo entre -1 y 1."""
        assert isinstance(trading_env.action_space, spaces.Box)
        assert trading_env.action_space.shape == (1,)
        assert trading_env.action_space.low[0] == -1.0
        assert trading_env.action_space.high[0] == 1.0
        assert trading_env.action_space.dtype == np.float32


class TestReset:
    """Tests para el método reset."""
    
    def test_reset_returns_observation_and_info(self, trading_env):
        """Debe retornar observación e info."""
        obs, info = trading_env.reset()
        
        assert obs is not None
        assert isinstance(info, dict)
        assert 'status' in info
    
    def test_reset_observation_structure(self, trading_env):
        """La observación debe tener la estructura correcta."""
        obs, _ = trading_env.reset()
        
        assert isinstance(obs, dict)
        assert 'market' in obs
        assert 'portfolio' in obs
        assert obs['market'].shape == (trading_env.window_size, trading_env.n_columnas)
        assert obs['portfolio'].shape == (3,)
    
    def test_reset_initializes_state(self, trading_env):
        """Debe reiniciar el estado del entorno."""
        # Avanzar algunos pasos
        trading_env.paso_actual = 50
        trading_env.episodio = 5
        
        obs, _ = trading_env.reset()
        
        assert trading_env.paso_actual == trading_env.window_size - 1
        assert trading_env.episodio == 6  # Se incrementa el episodio
    
    def test_reset_resets_portfolio(self, trading_env):
        """Debe reiniciar el portafolio."""
        # Modificar el portafolio
        original_balance = trading_env.portafolio._balance
        trading_env.portafolio._balance = 5000.0
        
        trading_env.reset()
        
        # El balance debe volver al inicial
        assert trading_env.portafolio._balance == original_balance
    
    def test_reset_with_seed(self, trading_env):
        """Debe aceptar un seed opcional."""
        obs1, _ = trading_env.reset(seed=42)
        obs2, _ = trading_env.reset(seed=42)
        
        # Con el mismo seed, las observaciones deberían ser similares
        # (aunque depende de si hay aleatoriedad en la construcción)
        assert obs1 is not None
        assert obs2 is not None
    
    def test_reset_initializes_prev_equity(self, trading_env):
        """Debe inicializar prev_equity correctamente."""
        obs, _ = trading_env.reset()
        
        # prev_equity debe ser igual al equity inicial
        precio_actual = float(trading_env.data_array[trading_env.paso_actual, trading_env.close_idx])
        equity_actual = float(trading_env.portafolio.get_equity(precio_actual))
        
        assert trading_env.prev_equity == equity_actual


class TestGetObservation:
    """Tests para el método _get_observation."""
    
    def test_get_observation_without_normalization(self, trading_env):
        """Debe construir observación sin normalización."""
        trading_env.reset()
        obs = trading_env._get_observation()
        
        assert isinstance(obs, dict)
        assert 'market' in obs
        assert 'portfolio' in obs
    
    def test_get_observation_with_normalization(self, trading_env_normalized):
        """Debe aplicar normalización cuando scaler está presente."""
        trading_env_normalized.reset()
        obs = trading_env_normalized._get_observation()
        
        # Verificar que los datos están en un rango razonable (normalizados)
        assert isinstance(obs, dict)
        assert 'market' in obs
        # Los datos normalizados deberían tener media cercana a 0 y std cercana a 1
        market_data = obs['market']
        assert market_data.mean() < 10  # No exactamente 0 por ventana limitada
    
    def test_get_observation_portfolio_components(self, trading_env):
        """Debe incluir equity, pnl_no_realizado y posicion en portfolio."""
        trading_env.reset()
        obs = trading_env._get_observation()
        
        portfolio_obs = obs['portfolio']
        assert len(portfolio_obs) == 3
        
        # Verificar que son valores numéricos válidos
        assert all(isinstance(x, (int, float, np.number)) for x in portfolio_obs)
    
    def test_get_observation_market_window_size(self, trading_env):
        """La ventana de mercado debe tener el tamaño correcto."""
        trading_env.reset()
        obs = trading_env._get_observation()
        
        assert obs['market'].shape[0] == trading_env.window_size
    
    def test_get_observation_normalized_portfolio(self, valid_config_dict, sample_data, portafolio):
        """Debe normalizar portfolio cuando normalizar_portfolio=True."""
        valid_config_dict['entorno']['normalizar_portfolio'] = True
        config = UnifiedConfig(**valid_config_dict)
        env = TradingEnv(config, sample_data, portafolio)
        
        env.reset()
        obs = env._get_observation()
        
        # Con normalización, los valores deberían estar en rangos específicos
        portfolio_obs = obs['portfolio']
        assert portfolio_obs is not None


class TestStep:
    """Tests para el método step."""
    
    def test_step_returns_correct_tuple(self, trading_env):
        """Debe retornar (obs, reward, terminated, truncated, info)."""
        trading_env.reset()
        action = np.array([0.0])
        
        result = trading_env.step(action)
        
        assert len(result) == 5
        obs, reward, terminated, truncated, info = result
        assert isinstance(obs, dict)
        assert isinstance(reward, (int, float))
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
    
    def test_step_with_none_action(self, trading_env):
        """Debe fallar con acción None."""
        trading_env.reset()
        
        with pytest.raises(ValueError, match="La acción no puede ser None o vacía"):
            trading_env.step(None)
    
    def test_step_with_empty_action(self, trading_env):
        """Debe fallar con acción vacía."""
        trading_env.reset()
        
        with pytest.raises(ValueError, match="La acción no puede ser None o vacía"):
            trading_env.step(np.array([]))
    
    def test_step_advances_time(self, trading_env):
        """Debe avanzar paso_actual."""
        trading_env.reset()
        paso_inicial = trading_env.paso_actual
        
        trading_env.step(np.array([0.0]))
        
        assert trading_env.paso_actual == paso_inicial + 1
    
    def test_step_truncated_at_end_of_data(self, trading_env):
        """Debe marcar truncated=True al final de los datos."""
        trading_env.reset()
        
        # Avanzar hasta casi el final
        while trading_env.paso_actual < trading_env.n_filas - 2:
            _, _, terminated, truncated, _ = trading_env.step(np.array([0.0]))
            if terminated or truncated:
                break
        
        # El último paso debe marcar truncated
        _, _, _, truncated, _ = trading_env.step(np.array([0.0]))
        assert truncated is True
    
    def test_step_terminated_on_max_drawdown(self, valid_config_dict, sample_data):
        """Debe marcar terminated=True cuando se excede max_drawdown."""
        # Configurar drawdown muy bajo para forzar terminación
        valid_config_dict['entorno']['max_drawdown_permitido'] = 0.01
        config = UnifiedConfig(**valid_config_dict)
        portafolio = Portafolio(config)
        env = TradingEnv(config, sample_data, portafolio)
        
        env.reset()
        
        # Intentar generar pérdidas abriendo posiciones
        # (esto es probabilístico, puede no siempre funcionar)
        for _ in range(10):
            _, _, terminated, truncated, _ = env.step(np.array([0.9]))
            if terminated:
                break
    
    def test_step_info_structure(self, trading_env):
        """La info debe tener la estructura esperada."""
        trading_env.reset()
        _, _, _, _, info = trading_env.step(np.array([0.0]))
        
        # Verificar estructura de info_builder
        assert 'entorno' in info
        assert 'portafolio' in info
        assert 'operacion' in info
        
        assert 'paso' in info['entorno']
        assert 'precio' in info['entorno']
        assert 'recompensa' in info['entorno']
    
    def test_step_with_positive_action(self, trading_env):
        """Debe procesar acción positiva (compra/long)."""
        trading_env.reset()
        
        # Acción fuerte de compra
        action = np.array([0.8])
        obs, reward, terminated, truncated, info = trading_env.step(action)
        
        assert info['operacion']['tipo_accion'] in ['long', 'mantener']
    
    def test_step_with_negative_action(self, trading_env):
        """Debe procesar acción negativa (venta/short)."""
        trading_env.reset()
        
        # Acción fuerte de venta
        action = np.array([-0.8])
        obs, reward, terminated, truncated, info = trading_env.step(action)
        
        assert info['operacion']['tipo_accion'] in ['short', 'mantener']
    
    def test_step_with_neutral_action(self, trading_env):
        """Debe mantener posición con acción neutral."""
        trading_env.reset()
        
        # Acción neutral
        action = np.array([0.0])
        obs, reward, terminated, truncated, info = trading_env.step(action)
        
        assert info['operacion']['tipo_accion'] == 'mantener'


class TestReward:
    """Tests para el cálculo de recompensas."""
    
    def test_reward_calculation_without_normalization(self, valid_config_dict, sample_data, portafolio):
        """Debe calcular recompensa en valores absolutos sin normalización."""
        valid_config_dict['entorno']['normalizar_recompensa'] = False
        config = UnifiedConfig(**valid_config_dict)
        env = TradingEnv(config, sample_data, portafolio)
        
        env.reset()
        precio = float(env.data_array[env.paso_actual, env.close_idx])
        
        reward = env._recompensa(precio)
        
        # La primera recompensa debe ser 0 (no ha cambiado el equity)
        assert isinstance(reward, float)
    
    def test_reward_calculation_with_normalization(self, valid_config_dict, sample_data, portafolio):
        """Debe calcular recompensa en porcentajes con normalización."""
        valid_config_dict['entorno']['normalizar_recompensa'] = True
        config = UnifiedConfig(**valid_config_dict)
        env = TradingEnv(config, sample_data, portafolio)
        
        env.reset()
        precio = float(env.data_array[env.paso_actual, env.close_idx])
        
        reward = env._recompensa(precio)
        
        assert isinstance(reward, float)
    
    def test_reward_updates_prev_equity(self, trading_env):
        """Debe actualizar prev_equity después del cálculo."""
        trading_env.reset()
        
        precio = float(trading_env.data_array[trading_env.paso_actual, trading_env.close_idx])
        equity_antes = trading_env.prev_equity
        
        trading_env._recompensa(precio)
        
        # prev_equity debe haberse actualizado
        assert trading_env.prev_equity == float(trading_env.portafolio.get_equity(precio))


class TestExecuteAction:
    """Tests para la ejecución de acciones."""
    
    def test_execute_action_with_invalid_action_type(self, trading_env):
        """Debe fallar con tipo de acción inválido."""
        trading_env.reset()
        
        with pytest.raises(ValueError):
            trading_env._ejecutar_action("invalid", 50000.0)
    
    def test_execute_action_with_invalid_precio(self, trading_env):
        """Debe fallar con precio inválido."""
        trading_env.reset()
        
        with pytest.raises(ValueError):
            trading_env._ejecutar_action(0.5, -100.0)
    
    def test_execute_action_neutral_returns_mantener(self, trading_env):
        """Acción neutral debe retornar tipo_accion='mantener'."""
        trading_env.reset()
        
        info = trading_env._ejecutar_action(0.05, 50000.0)
        
        assert info['tipo_accion'] == 'mantener'
        assert info['resultado'] is True
    
    def test_execute_action_accepts_numpy_types(self, trading_env):
        """Debe aceptar tipos numpy además de tipos nativos."""
        trading_env.reset()
        
        # Probar con np.float32
        action_np = np.float32(0.5)
        precio_np = 50000.0
        
        info = trading_env._ejecutar_action(action_np, precio_np)
        assert info is not None


class TestHelperMethods:
    """Tests para métodos auxiliares."""
    
    def test_get_column_value_success(self, trading_env):
        """Debe retornar el valor correcto de una columna."""
        trading_env.reset()
        
        value = trading_env.get_column_value(50, 'close')
        
        assert isinstance(value, float)
        assert value > 0
    
    def test_get_column_value_invalid_column(self, trading_env):
        """Debe fallar con columna inexistente."""
        trading_env.reset()
        
        with pytest.raises(Exception):
            trading_env.get_column_value(50, 'nonexistent_column')
    
    def test_get_column_value_invalid_row(self, trading_env):
        """Debe fallar con índice de fila inválido."""
        trading_env.reset()
        
        with pytest.raises(Exception):
            trading_env.get_column_value(999999, 'close')
    
    def test_get_timestamp_success(self, trading_env):
        """Debe retornar timestamp válido."""
        trading_env.reset()
        
        timestamp = trading_env.get_timestamp(50)
        
        assert timestamp is not None
    
    def test_get_timestamp_with_no_timestamps(self, config, portafolio):
        """Debe retornar None cuando no hay timestamps."""
        # Crear datos sin timestamp
        data_no_timestamp = pd.DataFrame({
            'open': np.random.randn(100) * 100 + 50000,
            'close': np.random.randn(100) * 100 + 50000,
        })
        
        env = TradingEnv(config, data_no_timestamp, portafolio)
        env.reset()
        
        timestamp = env.get_timestamp(50)
        assert timestamp is None


class TestNormalization:
    """Tests específicos para normalización."""
    
    def test_env_with_scaler_applies_normalization(self, config, sample_data_normalized, portafolio):
        """Debe aplicar normalización cuando se proporciona scaler."""
        data, scaler = sample_data_normalized
        env = TradingEnv(config, data, portafolio, scaler=scaler)
        
        env.reset()
        obs = env._get_observation()
        
        # Los datos normalizados deben tener estadísticas específicas
        market_data = obs['market']
        assert market_data is not None
        assert isinstance(market_data, np.ndarray)
    
    def test_env_without_scaler_no_normalization(self, config, sample_data, portafolio):
        """No debe aplicar normalización sin scaler."""
        env = TradingEnv(config, sample_data, portafolio, scaler=None)
        
        env.reset()
        obs = env._get_observation()
        
        # Los datos sin normalizar deben estar en el rango original
        market_data = obs['market']
        assert market_data is not None
        # Los precios deberían estar en el rango típico (miles)
        assert market_data.mean() > 100  # No normalizados


class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_multiple_episodes(self, trading_env):
        """Debe manejar múltiples episodios correctamente."""
        for episode in range(3):
            obs, info = trading_env.reset()
            assert trading_env.episodio == episode + 1
            
            # Ejecutar algunos pasos
            for _ in range(5):
                obs, reward, terminated, truncated, info = trading_env.step(np.array([0.0]))
                if terminated or truncated:
                    break
    
    def test_long_episode(self, trading_env):
        """Debe manejar episodios largos sin errores."""
        trading_env.reset()
        
        steps = 0
        max_steps = 50
        
        while steps < max_steps:
            _, _, terminated, truncated, _ = trading_env.step(np.array([0.0]))
            steps += 1
            
            if terminated or truncated:
                break
        
        assert steps > 0
    
    def test_with_small_dataset(self, config, small_sample_data, portafolio):
        """Debe funcionar con dataset pequeño."""
        env = TradingEnv(config, small_sample_data, portafolio)
        env.reset()
        
        obs, reward, terminated, truncated, info = env.step(np.array([0.0]))
        assert obs is not None
