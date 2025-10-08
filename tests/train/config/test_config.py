"""Tests para el módulo de configuración del entrenamiento."""

import pytest
import tempfile
import yaml
from pathlib import Path
from argparse import Namespace
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.train.config.config import (
    IndicadoresConfig,
    PreprocesamientoConfig,
    DataDownloaderConfig,
    PortafolioConfig,
    EntornoConfig,
    NetArchConfig,
    PolicyKwargsConfig,
    SACModelConfig,
    DatasetConfig,
    OutputConfig,
    UnifiedConfig
)


class TestIndicadoresConfig:
    """Tests para la clase IndicadoresConfig."""

    def test_valid_indicadores_config(self):
        """Test que verifica la creación de configuración válida de indicadores."""
        config = IndicadoresConfig(
            SMA_short=10,
            SMA_long=50,
            RSI_length=14,
            MACD_fast=12,
            MACD_slow=26,
            MACD_signal=9,
            BB_length=20,
            BB_std=2.0
        )
        
        assert config.SMA_short == 10
        assert config.SMA_long == 50
        assert config.RSI_length == 14
        assert config.BB_std == 2.0

    def test_invalid_negative_values(self):
        """Test que verifica error con valores negativos."""
        with pytest.raises(ValidationError):
            IndicadoresConfig(
                SMA_short=-10,
                SMA_long=50,
                RSI_length=14,
                MACD_fast=12,
                MACD_slow=26,
                MACD_signal=9,
                BB_length=20,
                BB_std=2.0
            )

    def test_invalid_zero_values(self):
        """Test que verifica error con valores cero."""
        with pytest.raises(ValidationError):
            IndicadoresConfig(
                SMA_short=10,
                SMA_long=0,
                RSI_length=14,
                MACD_fast=12,
                MACD_slow=26,
                MACD_signal=9,
                BB_length=20,
                BB_std=2.0
            )


class TestPreprocesamientoConfig:
    """Tests para la clase PreprocesamientoConfig."""

    def test_valid_preprocesamiento_config(self):
        """Test que verifica la creación de configuración válida de preprocesamiento."""
        indicadores = IndicadoresConfig(
            SMA_short=10, SMA_long=50, RSI_length=14,
            MACD_fast=12, MACD_slow=26, MACD_signal=9,
            BB_length=20, BB_std=2.0
        )
        
        config = PreprocesamientoConfig(
            interpol_method="linear",
            indicadores=indicadores
        )
        
        assert config.interpol_method == "linear"
        assert config.indicadores.SMA_short == 10

    def test_valid_interpolation_methods(self):
        """Test que verifica diferentes métodos de interpolación válidos."""
        indicadores = IndicadoresConfig(
            SMA_short=10, SMA_long=50, RSI_length=14,
            MACD_fast=12, MACD_slow=26, MACD_signal=9,
            BB_length=20, BB_std=2.0
        )
        
        valid_methods = ["linear", "cubic", "nearest", "quadratic"]
        
        for method in valid_methods:
            config = PreprocesamientoConfig(
                interpol_method=method,
                indicadores=indicadores
            )
            assert config.interpol_method == method

    def test_invalid_interpolation_method(self):
        """Test que verifica error con método de interpolación inválido."""
        indicadores = IndicadoresConfig(
            SMA_short=10, SMA_long=50, RSI_length=14,
            MACD_fast=12, MACD_slow=26, MACD_signal=9,
            BB_length=20, BB_std=2.0
        )
        
        with pytest.raises(ValidationError):
            PreprocesamientoConfig(
                interpol_method="invalid_method",
                indicadores=indicadores
            )


class TestDataDownloaderConfig:
    """Tests para la clase DataDownloaderConfig."""

    def test_valid_data_downloader_config(self):
        """Test que verifica la creación de configuración válida de descarga de datos."""
        config = DataDownloaderConfig(
            symbol="BTCUSDT",
            interval="1h",
            start_date="2023-01-01",
            end_date="2023-12-31",
            limit=1000
        )
        
        assert config.symbol == "BTCUSDT"
        assert config.interval == "1h"
        assert config.start_date == "2023-01-01"
        assert config.limit == 1000

    def test_invalid_date_format(self):
        """Test que verifica error con formato de fecha inválido."""
        with pytest.raises(ValidationError):
            DataDownloaderConfig(
                symbol="BTCUSDT",
                interval="1h",
                start_date="01-01-2023",
                end_date="2023-12-31",
                limit=1000
            )

    def test_invalid_limit_too_high(self):
        """Test que verifica error con límite mayor a 1500."""
        with pytest.raises(ValidationError):
            DataDownloaderConfig(
                symbol="BTCUSDT",
                interval="1h",
                start_date="2023-01-01",
                end_date="2023-12-31",
                limit=2000
            )

    def test_invalid_limit_zero(self):
        """Test que verifica error con límite cero."""
        with pytest.raises(ValidationError):
            DataDownloaderConfig(
                symbol="BTCUSDT",
                interval="1h",
                start_date="2023-01-01",
                end_date="2023-12-31",
                limit=0
            )


class TestPortafolioConfig:
    """Tests para la clase PortafolioConfig."""

    def test_valid_portafolio_config(self):
        """Test que verifica la creación de configuración válida de portafolio."""
        config = PortafolioConfig(
            capital_inicial=10000.0,
            apalancamiento=1.0,
            comision=0.001,
            slippage=0.0005
        )
        
        assert config.capital_inicial == 10000.0
        assert config.apalancamiento == 1.0
        assert config.comision == 0.001
        assert config.slippage == 0.0005

    def test_invalid_negative_capital(self):
        """Test que verifica error con capital inicial negativo."""
        with pytest.raises(ValidationError):
            PortafolioConfig(
                capital_inicial=-10000.0,
                apalancamiento=1.0,
                comision=0.001,
                slippage=0.0005
            )

    def test_invalid_comision_too_high(self):
        """Test que verifica error con comisión mayor a 0.1."""
        with pytest.raises(ValidationError):
            PortafolioConfig(
                capital_inicial=10000.0,
                apalancamiento=1.0,
                comision=0.15,
                slippage=0.0005
            )


class TestEntornoConfig:
    """Tests para la clase EntornoConfig."""

    def test_valid_entorno_config(self):
        """Test que verifica la creación de configuración válida de entorno."""
        config = EntornoConfig(
            window_size=30,
            max_drawdown_permitido=0.2,
            factor_aversion_riesgo=2.0,
            umbral_mantener_posicion=0.1,
            penalizacion_no_operar=0.0001,
            total_timesteps=10000,
            normalizar_portfolio=True,
            normalizar_recompensa=True,
            penalizacion_pct=0.00001
        )
        
        assert config.window_size == 30
        assert config.max_drawdown_permitido == 0.2
        assert config.total_timesteps == 10000
        assert config.normalizar_portfolio is True

    def test_invalid_window_size_zero(self):
        """Test que verifica error con window_size cero."""
        with pytest.raises(ValidationError):
            EntornoConfig(
                window_size=0,
                max_drawdown_permitido=0.2,
                factor_aversion_riesgo=2.0,
                umbral_mantener_posicion=0.1,
                penalizacion_no_operar=0.0001,
                total_timesteps=10000
            )

    def test_invalid_max_drawdown_greater_than_one(self):
        """Test que verifica error con max_drawdown mayor a 1."""
        with pytest.raises(ValidationError):
            EntornoConfig(
                window_size=30,
                max_drawdown_permitido=1.5,
                factor_aversion_riesgo=2.0,
                umbral_mantener_posicion=0.1,
                penalizacion_no_operar=0.0001,
                total_timesteps=10000
            )


class TestSACModelConfig:
    """Tests para la clase SACModelConfig."""

    def test_valid_sac_model_config(self):
        """Test que verifica la creación de configuración válida de modelo SAC."""
        config = SACModelConfig(
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
        )
        
        assert config.policy == "MlpPolicy"
        assert config.learning_rate == 0.0003
        assert config.batch_size == 256
        assert config.gamma == 0.99

    def test_invalid_negative_learning_rate(self):
        """Test que verifica error con learning_rate negativo."""
        with pytest.raises(ValidationError):
            SACModelConfig(
                policy="MlpPolicy",
                learning_rate=-0.0003,
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
            )

    def test_invalid_gamma_greater_than_one(self):
        """Test que verifica error con gamma mayor a 1."""
        with pytest.raises(ValidationError):
            SACModelConfig(
                policy="MlpPolicy",
                learning_rate=0.0003,
                buffer_size=100000,
                learning_starts=1000,
                batch_size=256,
                tau=0.005,
                gamma=1.5,
                ent_coef="auto",
                train_freq=(1, "step"),
                gradient_steps=1,
                verbose=1,
                seed=42
            )


class TestOutputConfig:
    """Tests para la clase OutputConfig."""

    def test_valid_output_config(self):
        """Test que verifica la creación de configuración válida de output."""
        config = OutputConfig(
            base_dir="entrenamientos/test_run",
            model_path="entrenamientos/test_run/modelos/modelo",
            tensorboard_log="entrenamientos/test_run/tensorboard/",
            scaler_train_path="entrenamientos/test_run/scaler_train.pkl",
            scaler_eval_path="entrenamientos/test_run/scaler_eval.pkl"
        )
        
        assert config.base_dir == "entrenamientos/test_run"
        assert config.model_path == "entrenamientos/test_run/modelos/modelo"
        assert config.metadata_filename == "config_metadata.yaml"

    def test_output_config_without_eval_scaler(self):
        """Test que verifica configuración sin scaler de evaluación."""
        config = OutputConfig(
            base_dir="entrenamientos/test_run",
            model_path="entrenamientos/test_run/modelos/modelo",
            tensorboard_log="entrenamientos/test_run/tensorboard/",
            scaler_train_path="entrenamientos/test_run/scaler_train.pkl"
        )
        
        assert config.scaler_eval_path is None


class TestUnifiedConfig:
    """Tests para la clase UnifiedConfig."""

    def test_valid_unified_config(self, valid_config_yaml: Dict[str, Any]):
        """Test que verifica la creación de configuración unificada válida."""
        config = UnifiedConfig(**valid_config_yaml)
        
        assert config.data_downloader.symbol == "BTCUSDT"
        assert config.entorno.window_size == 30
        assert config.SACmodel.learning_rate == 0.0003
        assert config.portafolio.capital_inicial == 10000.0

    def test_unified_config_missing_section(self, valid_config_yaml: Dict[str, Any]):
        """Test que verifica error cuando falta una sección requerida."""
        invalid_config = valid_config_yaml.copy()
        del invalid_config["portafolio"]
        
        with pytest.raises(ValidationError):
            UnifiedConfig(**invalid_config)

    def test_generate_train_id(self, valid_config_yaml: Dict[str, Any]):
        """Test que verifica la generación correcta del train_id."""
        with patch('src.train.config.config.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 4, 10, 35, 37)
            mock_datetime.strftime = datetime.strftime
            
            train_id = UnifiedConfig._generate_train_id(
                symbol="BTCUSDT",
                train_start="2023-01-01",
                train_end="2023-12-31",
                yaml_config=valid_config_yaml
            )
            
            expected_pattern = "train_BTCUSDT_20230101_20231231_lr0.0003_bs256_ws30_"
            assert train_id.startswith(expected_pattern)

    def test_generate_train_id_missing_config_section(self):
        """Test que verifica error al generar train_id sin configuración completa."""
        incomplete_config = {"SACmodel": {}}
        
        with pytest.raises(ValueError, match="Falta la sección 'entorno'"):
            UnifiedConfig._generate_train_id(
                symbol="BTCUSDT",
                train_start="2023-01-01",
                train_end="2023-12-31",
                yaml_config=incomplete_config
            )

    def test_add_cli_args_unified(self, valid_config_yaml: Dict[str, Any], mock_args_namespace: Namespace):
        """Test que verifica la integración de argumentos CLI."""
        updated_config = UnifiedConfig._add_cli_args_unified(
            args=mock_args_namespace,
            yaml_config=valid_config_yaml
        )
        
        assert updated_config["data_downloader"]["symbol"] == "BTCUSDT"
        assert updated_config["data_downloader"]["interval"] == "1h"
        assert updated_config["data_downloader"]["start_date"] == "2023-01-01"
        assert updated_config["data_downloader"]["end_date"] == "2023-06-30"
        assert updated_config["entorno"]["total_timesteps"] == 10000

    def test_add_cli_args_unified_missing_entorno(self, valid_config_yaml: Dict[str, Any], mock_args_namespace: Namespace):
        """Test que verifica error cuando falta sección 'entorno'."""
        invalid_config = valid_config_yaml.copy()
        del invalid_config["entorno"]
        
        with pytest.raises(KeyError, match="Falta la sección 'entorno'"):
            UnifiedConfig._add_cli_args_unified(
                args=mock_args_namespace,
                yaml_config=invalid_config
            )

    def test_add_output_paths_unified(self, valid_config_yaml: Dict[str, Any], mock_args_namespace: Namespace):
        """Test que verifica la adición de rutas de output."""
        with patch('src.train.config.config.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 4, 10, 35, 37)
            mock_datetime.strftime = datetime.strftime
            
            updated_config = UnifiedConfig._add_output_paths_unified(
                args=mock_args_namespace,
                yaml_config=valid_config_yaml
            )
            
            assert "Output" in updated_config
            assert "base_dir" in updated_config["Output"]
            assert updated_config["Output"]["base_dir"].startswith("entrenamientos/train_BTCUSDT")
            assert "model_path" in updated_config["Output"]
            assert "tensorboard_log" in updated_config["Output"]

    def test_load_for_unified_training(self, temp_config_file: Path, mock_args_namespace: Namespace):
        """Test que verifica la carga completa de configuración para entrenamiento unificado."""
        # Actualizar el namespace con la ruta del archivo temporal
        mock_args_namespace.config = str(temp_config_file)
        
        with patch('src.train.config.config.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 4, 10, 35, 37)
            mock_datetime.strftime = datetime.strftime
            
            config = UnifiedConfig.load_for_unified_training(args=mock_args_namespace)
            
            assert isinstance(config, UnifiedConfig)
            assert config.data_downloader.symbol == "BTCUSDT"
            assert config.entorno.total_timesteps == 10000
            assert config.Output is not None
            assert config.Output.base_dir.startswith("entrenamientos/train_BTCUSDT")

    def test_load_for_unified_training_missing_args(self):
        """Test que verifica error cuando args es None."""
        with pytest.raises(ValueError, match="Los argumentos no pueden ser None"):
            UnifiedConfig.load_for_unified_training(args=None)

    def test_load_for_unified_training_missing_config_path(self):
        """Test que verifica error cuando falta la ruta del archivo de configuración."""
        args = Namespace(config=None)
        
        with pytest.raises(ValueError, match="Falta la ruta del archivo de configuración"):
            UnifiedConfig.load_for_unified_training(args=args)

    def test_load_for_unified_training_file_not_found(self, mock_args_namespace: Namespace):
        """Test que verifica error cuando el archivo de configuración no existe."""
        mock_args_namespace.config = "/path/to/nonexistent/config.yaml"
        
        with pytest.raises(ValueError, match="Error al cargar el archivo de configuración"):
            UnifiedConfig.load_for_unified_training(args=mock_args_namespace)

    def test_load_for_unified_training_empty_yaml(self, mock_args_namespace: Namespace):
        """Test que verifica error con archivo YAML vacío."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            mock_args_namespace.config = temp_path
            
            with pytest.raises(ValueError, match="El archivo de configuración está vacío"):
                UnifiedConfig.load_for_unified_training(args=mock_args_namespace)
        finally:
            Path(temp_path).unlink()

    def test_load_for_unified_training_invalid_yaml(self, mock_args_namespace: Namespace):
        """Test que verifica error con YAML inválido."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            mock_args_namespace.config = temp_path
            
            with pytest.raises(ValueError, match="Error al parsear el archivo YAML"):
                UnifiedConfig.load_for_unified_training(args=mock_args_namespace)
        finally:
            Path(temp_path).unlink()


class TestDatasetConfig:
    """Tests para la clase DatasetConfig."""

    def test_valid_dataset_config_minimal(self):
        """Test que verifica la creación de configuración mínima de dataset."""
        config = DatasetConfig(train="path/to/train.csv")
        
        assert config.train == "path/to/train.csv"
        assert config.eval is None
        assert config.symbol is None

    def test_valid_dataset_config_complete(self):
        """Test que verifica la creación de configuración completa de dataset."""
        config = DatasetConfig(
            train="path/to/train.csv",
            eval="path/to/eval.csv",
            symbol="BTCUSDT",
            intervalo="1h",
            symbol_eval="ETHUSDT",
            intervalo_eval="4h"
        )
        
        assert config.train == "path/to/train.csv"
        assert config.eval == "path/to/eval.csv"
        assert config.symbol == "BTCUSDT"
        assert config.intervalo == "1h"
        assert config.symbol_eval == "ETHUSDT"
        assert config.intervalo_eval == "4h"


class TestNetArchConfig:
    """Tests para la clase NetArchConfig."""

    def test_valid_net_arch_config(self):
        """Test que verifica la creación de configuración válida de arquitectura de red."""
        config = NetArchConfig(
            pi=[256, 256],
            qf=[256, 256]
        )
        
        assert config.pi == [256, 256]
        assert config.qf == [256, 256]

    def test_different_architectures(self):
        """Test que verifica diferentes configuraciones de arquitectura."""
        config = NetArchConfig(
            pi=[128, 128, 64],
            qf=[512, 256]
        )
        
        assert len(config.pi) == 3
        assert len(config.qf) == 2


class TestPolicyKwargsConfig:
    """Tests para la clase PolicyKwargsConfig."""

    def test_valid_policy_kwargs_config(self):
        """Test que verifica la creación de configuración válida de policy_kwargs."""
        net_arch = NetArchConfig(pi=[256, 256], qf=[256, 256])
        config = PolicyKwargsConfig(
            net_arch=net_arch,
            log_std_init=-3,
            n_critics=2
        )
        
        assert config.net_arch.pi == [256, 256]
        assert config.log_std_init == -3
        assert config.n_critics == 2
