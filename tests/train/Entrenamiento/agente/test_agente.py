"""Tests para el módulo AgenteSac."""

import pytest
import numpy as np
import pandas as pd
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, Mock
import gymnasium as gym
from stable_baselines3 import SAC

from src.train.Entrenamiento.agente.agente import AgenteSac


class TestAgenteSacInit:
    """Tests para el constructor de AgenteSac."""
    
    def test_init_success(self, mock_config):
        """Test de inicialización exitosa del agente."""
        total_timesteps = 10000
        agente = AgenteSac(config=mock_config, total_timesteps=total_timesteps)
        
        assert agente.model is None  # El modelo aún no se ha creado
        assert agente.config == mock_config
        assert agente.total_timesteps == total_timesteps
        assert agente.model_path == mock_config.Output.model_path
        assert agente.tensorboard_log == mock_config.Output.tensorboard_log
    
    def test_init_invalid_timesteps(self, mock_config):
        """Test con timesteps inválidos (<=0)."""
        with pytest.raises(ValueError, match="total_timesteps debe ser mayor que 0"):
            AgenteSac(config=mock_config, total_timesteps=0)
        
        with pytest.raises(ValueError, match="total_timesteps debe ser mayor que 0"):
            AgenteSac(config=mock_config, total_timesteps=-100)
    
    def test_init_config_attributes(self, mock_config):
        """Test de que la configuración se asigna correctamente."""
        agente = AgenteSac(config=mock_config, total_timesteps=5000)
        
        assert hasattr(agente, 'config')
        assert hasattr(agente, 'model_path')
        assert hasattr(agente, 'tensorboard_log')
        assert agente.config.SACmodel.learning_rate == 0.0003
        assert agente.config.SACmodel.batch_size == 256


class TestAgenteSacCrearModelo:
    """Tests para el método CrearModelo."""
    
    def test_crear_modelo_success(self, mock_config, simple_gym_env):
        """Test de creación exitosa del modelo SAC."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        assert agente.model is not None
        assert isinstance(agente.model, SAC)
        assert agente.model.learning_rate == mock_config.SACmodel.learning_rate
        assert agente.model.batch_size == mock_config.SACmodel.batch_size
    
    def test_crear_modelo_env_none(self, mock_config):
        """Test con entorno None."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(ValueError, match="El entorno no puede ser None"):
            agente.CrearModelo(env=None)
    
    def test_crear_modelo_invalid_env(self, mock_config):
        """Test con entorno inválido (sin observation_space)."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        invalid_env = MagicMock()
        del invalid_env.observation_space  # Eliminar el atributo
        
        with pytest.raises(ValueError, match="observation_space y action_space"):
            agente.CrearModelo(env=invalid_env)
    
    def test_crear_modelo_policy_kwargs(self, mock_config, simple_gym_env):
        """Test de que policy_kwargs se configura correctamente."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        # Verificar que la red tiene la arquitectura correcta
        assert agente.model.policy_kwargs is not None
        assert 'net_arch' in agente.model.policy_kwargs
    
    def test_crear_modelo_invalid_buffer_size(self, mock_config, simple_gym_env):
        """Test con buffer_size inválido."""
        # Modificar la configuración para tener buffer_size inválido
        mock_config.SACmodel.buffer_size = 0
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(ValueError, match="buffer_size debe ser mayor que 0"):
            agente.CrearModelo(env=simple_gym_env)
    
    def test_crear_modelo_invalid_batch_size(self, mock_config, simple_gym_env):
        """Test con batch_size inválido."""
        mock_config.SACmodel.batch_size = -10
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(ValueError, match="batch_size debe ser mayor que 0"):
            agente.CrearModelo(env=simple_gym_env)
    
    def test_crear_modelo_invalid_learning_rate(self, mock_config, simple_gym_env):
        """Test con learning_rate inválido."""
        mock_config.SACmodel.learning_rate = 0
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(ValueError, match="learning_rate debe ser mayor que 0"):
            agente.CrearModelo(env=simple_gym_env)


class TestAgenteSacTrain:
    """Tests para el método train."""
    
    def test_train_success(self, mock_config, simple_gym_env):
        """Test de entrenamiento exitoso (con timesteps pequeños)."""
        agente = AgenteSac(config=mock_config, total_timesteps=100)
        agente.CrearModelo(env=simple_gym_env)
        
        # Entrenar con pocos pasos para que sea rápido
        agente.train()
        
        # Verificar que el modelo se entrenó
        assert agente.model is not None
    
    def test_train_model_not_created(self, mock_config):
        """Test de entrenamiento sin crear el modelo primero."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(RuntimeError, match="El modelo no ha sido creado"):
            agente.train()
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_train_calls_learn(self, mock_sac_class, mock_config, simple_gym_env):
        """Test de que train() llama a model.learn() con los parámetros correctos."""
        # Configurar el mock
        mock_model_instance = MagicMock()
        mock_sac_class.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=5000)
        agente.CrearModelo(env=simple_gym_env)
        agente.train()
        
        # Verificar que learn fue llamado con total_timesteps
        mock_model_instance.learn.assert_called_once_with(total_timesteps=5000)


class TestAgenteSacGuardarModelo:
    """Tests para el método GuardarModelo."""
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_guardar_modelo_success(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de guardado exitoso del modelo."""
        # Configurar el mock
        mock_model_instance = MagicMock()
        mock_sac_class.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        agente.GuardarModelo()
        
        # Verificar que se llamó a save()
        mock_model_instance.save.assert_called_once_with(mock_config.Output.model_path)
    
    def test_guardar_modelo_sin_modelo(self, mock_config):
        """Test de guardado sin modelo creado."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(RuntimeError, match="No hay modelo para guardar"):
            agente.GuardarModelo()
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_guardar_modelo_crea_directorios(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de que GuardarModelo crea los directorios necesarios."""
        mock_model_instance = MagicMock()
        mock_sac_class.return_value = mock_model_instance
        
        # Asegurar que los directorios no existen
        modelos_dir = os.path.join(temp_output_dir, "modelos")
        tensorboard_dir = os.path.join(temp_output_dir, "tensorboard")
        
        if os.path.exists(modelos_dir):
            shutil.rmtree(modelos_dir)
        if os.path.exists(tensorboard_dir):
            shutil.rmtree(tensorboard_dir)
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        agente.GuardarModelo()
        
        # Verificar que los directorios fueron creados
        assert os.path.exists(modelos_dir)
        assert os.path.exists(tensorboard_dir)


class TestAgenteSacEvaluarEnv:
    """Tests para el método EvaluarEnv."""
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_evaluar_env_success(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de evaluación exitosa del entorno."""
        # Configurar el mock del modelo
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.return_value = mock_model_instance
        mock_sac_class.load.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        # Simular que el modelo fue guardado
        agente.model_path = os.path.join(temp_output_dir, "test_model.zip")
        
        # Evaluar con 1 episodio y pocos pasos
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=1,
            max_steps_per_episode=10,
            save_dir=temp_output_dir
        )
        
        # Verificar que retorna los tres DataFrames
        assert 'entorno' in result
        assert 'portafolio' in result
        assert 'operacion' in result
        assert isinstance(result['entorno'], pd.DataFrame)
        assert isinstance(result['portafolio'], pd.DataFrame)
        assert isinstance(result['operacion'], pd.DataFrame)
    
    def test_evaluar_env_none(self, mock_config):
        """Test con entorno None."""
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        
        with pytest.raises(ValueError, match="El entorno de evaluación no puede ser None"):
            agente.EvaluarEnv(env=None)
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_evaluar_env_sin_modelo_carga_desde_disco(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de que EvaluarEnv carga el modelo desde disco si no está en memoria."""
        # Crear un archivo temporal para simular el modelo guardado
        model_path = os.path.join(temp_output_dir, "modelos", "sac_model.zip")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Crear archivo vacío para simular modelo guardado
        with open(model_path, 'w') as f:
            f.write("mock model")
        
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.load.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        # No crear el modelo, solo evaluar
        
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=1,
            max_steps_per_episode=5,
            save_dir=temp_output_dir
        )
        
        # Verificar que SAC.load fue llamado
        mock_sac_class.load.assert_called()
        assert result is not None
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_evaluar_env_guarda_csvs(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de que EvaluarEnv guarda los CSVs correctamente."""
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.return_value = mock_model_instance
        mock_sac_class.load.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=1,
            max_steps_per_episode=5,
            save_dir=temp_output_dir
        )
        
        # Verificar que los archivos CSV fueron creados
        eval_dir = os.path.join(temp_output_dir, 'evaluacion')
        assert os.path.exists(os.path.join(eval_dir, 'entorno.csv'))
        assert os.path.exists(os.path.join(eval_dir, 'portafolio.csv'))
        assert os.path.exists(os.path.join(eval_dir, 'operacion.csv'))
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_evaluar_env_multiples_episodios(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de evaluación con múltiples episodios."""
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=3,
            max_steps_per_episode=5,
            save_dir=temp_output_dir
        )
        
        # Verificar que hay datos de múltiples episodios
        assert len(result['entorno']) > 0
        # El número de filas debería ser aproximadamente n_episodes * max_steps_per_episode
        assert len(result['entorno']) >= 10  # Al menos 2 episodios con algunos pasos
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_evaluar_env_dataframe_structure(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test de la estructura de los DataFrames retornados."""
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=1000)
        agente.CrearModelo(env=simple_gym_env)
        
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=1,
            max_steps_per_episode=10,
            save_dir=temp_output_dir
        )
        
        # Verificar columnas comunes
        assert 'episodio' in result['entorno'].columns
        assert 'paso' in result['entorno'].columns
        assert 'episodio' in result['portafolio'].columns
        assert 'paso' in result['portafolio'].columns
        assert 'episodio' in result['operacion'].columns
        assert 'paso' in result['operacion'].columns


class TestAgenteSacIntegration:
    """Tests de integración para el flujo completo del agente."""
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_flujo_completo_entrenamiento(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test del flujo completo: crear -> entrenar -> guardar."""
        mock_model_instance = MagicMock()
        mock_model_instance.learn.return_value = mock_model_instance
        mock_sac_class.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=100)
        agente.CrearModelo(env=simple_gym_env)
        agente.train()
        agente.GuardarModelo()
        
        # Verificar que todo el flujo se ejecutó
        mock_model_instance.learn.assert_called_once()
        mock_model_instance.save.assert_called_once()
    
    @patch('src.train.Entrenamiento.agente.agente.SAC')
    def test_flujo_completo_con_evaluacion(self, mock_sac_class, mock_config, simple_gym_env, temp_output_dir):
        """Test del flujo completo incluyendo evaluación."""
        mock_model_instance = MagicMock()
        mock_model_instance.learn.return_value = mock_model_instance
        mock_model_instance.predict.return_value = (np.array([0.0, 0.0, 0.0]), None)
        mock_sac_class.return_value = mock_model_instance
        mock_sac_class.load.return_value = mock_model_instance
        
        agente = AgenteSac(config=mock_config, total_timesteps=100)
        agente.CrearModelo(env=simple_gym_env)
        agente.train()
        agente.GuardarModelo()
        
        # Evaluar
        result = agente.EvaluarEnv(
            env=simple_gym_env,
            n_episodes=1,
            max_steps_per_episode=10,
            save_dir=temp_output_dir
        )
        
        assert result is not None
        assert all(key in result for key in ['entorno', 'portafolio', 'operacion'])
