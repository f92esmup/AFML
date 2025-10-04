"""Fixtures compartidas para los tests del agente SAC."""

import pytest
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Tuple
from unittest.mock import MagicMock, Mock
import tempfile
import os
import shutil

from src.train.config.config import (
    UnifiedConfig,
    DataDownloaderConfig,
    PreprocesamientoConfig,
    IndicadoresConfig,
    PortafolioConfig,
    EntornoConfig,
    SACModelConfig,
    PolicyKwargsConfig,
    NetArchConfig,
    OutputConfig,
)


@pytest.fixture
def temp_output_dir():
    """Crea un directorio temporal para outputs de prueba."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Limpieza después del test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_output_dir):
    """Configuración mock completa para pruebas del agente."""
    config_data = {
        "data_downloader": DataDownloaderConfig(
            symbol="BTCUSDT",
            interval="1h",
            start_date="2024-01-01",
            end_date="2024-01-31",
            limit=1000
        ),
        "preprocesamiento": PreprocesamientoConfig(
            interpol_method="linear",
            indicadores=IndicadoresConfig(
                SMA_short=10,
                SMA_long=50,
                RSI_length=14,
                MACD_fast=12,
                MACD_slow=26,
                MACD_signal=9,
                BB_length=20,
                BB_std=2.0
            )
        ),
        "portafolio": PortafolioConfig(
            capital_inicial=10000.0,
            apalancamiento=1.0,
            comision=0.001,
            slippage=0.0005
        ),
        "entorno": EntornoConfig(
            window_size=50,
            max_drawdown_permitido=0.2,
            factor_aversion_riesgo=2.0,
            umbral_mantener_posicion=0.05,
            penalizacion_no_operar=0.01,
            episodios=10,
            normalizar_portfolio=True,
            normalizar_recompensa=True,
            penalizacion_pct=0.00001
        ),
        "SACmodel": SACModelConfig(
            policy="MlpPolicy",
            learning_rate=0.0003,
            buffer_size=100000,
            learning_starts=1000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            ent_coef="auto",
            train_freq=(1, "step"),
            gradient_steps=1,
            verbose=1,
            seed=42
        ),
        "policy_kwargs": PolicyKwargsConfig(
            net_arch=NetArchConfig(
                pi=[256, 256],
                qf=[256, 256]
            ),
            log_std_init=-3.0,
            n_critics=2
        ),
        "Output": OutputConfig(
            base_dir=temp_output_dir,
            model_path=os.path.join(temp_output_dir, "modelos", "sac_model.zip"),
            tensorboard_log=os.path.join(temp_output_dir, "tensorboard"),
            scaler_train_path=os.path.join(temp_output_dir, "scalers", "scaler_train.pkl"),
            scaler_eval_path=os.path.join(temp_output_dir, "scalers", "scaler_eval.pkl"),
            metadata_filename="config_metadata.yaml"
        )
    }
    
    return UnifiedConfig(**config_data)


@pytest.fixture
def simple_gym_env():
    """Crea un entorno Gym simple para pruebas."""
    
    class SimpleTestEnv(gym.Env):
        """Entorno simple para pruebas."""
        
        def __init__(self):
            super().__init__()
            # Espacio de observación: 10 características
            self.observation_space = spaces.Box(
                low=-np.inf, 
                high=np.inf, 
                shape=(10,), 
                dtype=np.float32
            )
            # Espacio de acción: 3 acciones continuas [-1, 1]
            self.action_space = spaces.Box(
                low=-1, 
                high=1, 
                shape=(3,), 
                dtype=np.float32
            )
            self.current_step = 0
            self.max_steps = 100
            
        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            self.current_step = 0
            obs = np.random.randn(10).astype(np.float32)
            return obs, {}
        
        def step(self, action):
            self.current_step += 1
            
            # Observación siguiente
            obs = np.random.randn(10).astype(np.float32)
            
            # Recompensa aleatoria
            reward = np.random.randn()
            
            # Terminación
            terminated = self.current_step >= self.max_steps
            truncated = False
            
            # Info básico
            # Manejar action como escalar o array
            posicion_value = action[0] if hasattr(action, '__len__') and len(action) > 0 else action
            
            info = {
                'entorno': {
                    'episodio': 0,
                    'paso': self.current_step,
                    'terminated': terminated,
                    'truncated': truncated
                },
                'portafolio': {
                    'equity': 10000 + np.random.randn() * 100,
                    'posicion': posicion_value
                },
                'operacion': {
                    'accion': 'hold',
                    'precio': 50000 + np.random.randn() * 100
                }
            }
            
            return obs, reward, terminated, truncated, info
    
    return SimpleTestEnv()


@pytest.fixture
def mock_sac_model():
    """Mock del modelo SAC para pruebas."""
    model = MagicMock()
    model.learn = MagicMock(return_value=model)
    model.save = MagicMock()
    model.predict = MagicMock(return_value=(np.array([0.0, 0.0, 0.0]), None))
    model.set_env = MagicMock()
    return model


@pytest.fixture
def sample_evaluation_data():
    """Datos de ejemplo para pruebas de evaluación."""
    n_steps = 50
    
    entorno_data = {
        'episodio': [0] * n_steps,
        'paso': list(range(n_steps)),
        'precio_actual': np.random.uniform(48000, 52000, n_steps),
        'terminated': [False] * (n_steps - 1) + [True],
        'truncated': [False] * n_steps
    }
    
    portafolio_data = {
        'episodio': [0] * n_steps,
        'paso': list(range(n_steps)),
        'equity': np.linspace(10000, 11000, n_steps),
        'posicion': np.random.uniform(-1, 1, n_steps),
        'drawdown': np.random.uniform(0, 0.1, n_steps)
    }
    
    operacion_data = {
        'episodio': [0] * n_steps,
        'paso': list(range(n_steps)),
        'accion': np.random.choice(['buy', 'sell', 'hold'], n_steps),
        'precio': np.random.uniform(48000, 52000, n_steps),
        'volumen': np.random.uniform(0, 1, n_steps)
    }
    
    return {
        'entorno': pd.DataFrame(entorno_data),
        'portafolio': pd.DataFrame(portafolio_data),
        'operacion': pd.DataFrame(operacion_data)
    }
