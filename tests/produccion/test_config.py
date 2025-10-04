"""Tests para el módulo de configuración de producción."""

import pytest
import os
import yaml
import argparse
from pathlib import Path
from unittest.mock import patch, Mock

from src.produccion.config.config import ProductionConfig
from src.produccion.config.cli import parse_args


class TestProductionConfig:
    """Tests para la clase ProductionConfig."""
    
    def test_load_config_success(self, temp_training_dir, monkeypatch):
        """Test de carga exitosa de configuración."""
        # Cambiar al directorio temporal
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        # Crear args mock
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = False
        
        # Cargar configuración
        config = ProductionConfig.load_config(args)
        
        # Verificar atributos
        assert config.simbolo == "BTCUSDT"
        assert config.intervalo == "1h"
        assert config.apalancamiento == 2.0
        assert config.window_size == 30
        assert config.is_live is False
        assert config.scaler is not None
        
    def test_load_config_live_mode(self, temp_training_dir, monkeypatch):
        """Test de carga de configuración en modo LIVE."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = True
        
        config = ProductionConfig.load_config(args)
        
        assert config.is_live is True
        
    def test_load_config_file_not_found(self, temp_training_dir, monkeypatch):
        """Test de error cuando no se encuentra el archivo de configuración."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        args = Mock()
        args.train_id = "train_id_inexistente"
        args.live = False
        
        with pytest.raises(FileNotFoundError):
            ProductionConfig.load_config(args)
            
    def test_load_config_invalid_yaml(self, temp_training_dir, monkeypatch):
        """Test de error con YAML inválido."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        # Crear archivo YAML inválido
        config_path = Path(temp_training_dir["train_dir"]) / "config_metadata.yaml"
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content: [")
        
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = False
        
        with pytest.raises(ValueError, match="Error al analizar el archivo YAML"):
            ProductionConfig.load_config(args)
            
    def test_load_config_missing_scaler(self, temp_training_dir, monkeypatch):
        """Test de error cuando no existe el scaler."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        # Eliminar scaler
        scaler_path = Path(temp_training_dir["scaler_path"])
        scaler_path.unlink()
        
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = False
        
        # Ahora lanza FileNotFoundError en lugar de RuntimeError
        with pytest.raises(FileNotFoundError, match="Scaler no encontrado"):
            ProductionConfig.load_config(args)
            
    def test_scaler_excluded_from_dict(self, temp_training_dir, monkeypatch):
        """Test que el scaler no se incluye en dict()."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = False
        
        config = ProductionConfig.load_config(args)
        config_dict = config.dict()
        
        # El scaler debe estar en el objeto pero no en dict()
        assert config.scaler is not None
        assert "scaler" not in config_dict


class TestCLI:
    """Tests para el parser de argumentos CLI."""
    
    def test_parse_args_train_id_only(self):
        """Test de parseo con solo train-id."""
        test_args = ["--train-id", "test_train_id"]
        
        with patch("sys.argv", ["live.py"] + test_args):
            args = parse_args()
            
        assert args.train_id == "test_train_id"
        assert args.live is False
        
    def test_parse_args_with_live_flag(self):
        """Test de parseo con flag --live."""
        test_args = ["--train-id", "test_train_id", "--live"]
        
        with patch("sys.argv", ["live.py"] + test_args):
            args = parse_args()
            
        assert args.train_id == "test_train_id"
        assert args.live is True
        
    def test_parse_args_missing_train_id(self):
        """Test de error cuando falta --train-id."""
        test_args = ["--live"]
        
        with patch("sys.argv", ["live.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()
                
    def test_parse_args_help(self):
        """Test de ayuda."""
        test_args = ["--help"]
        
        with patch("sys.argv", ["live.py"] + test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()
                
        assert exc_info.value.code == 0


class TestProductionConfigValidation:
    """Tests de validación de configuración."""
    
    def test_apalancamiento_must_be_gte_1(self):
        """Test que el apalancamiento debe ser >= 1."""
        with pytest.raises(ValueError):
            ProductionConfig(
                apalancamiento=0.5,  # Inválido
                intervalo="1h",
                simbolo="BTCUSDT",
                train_id="test",
                model_path="/path/to/model",
                scaler_path="/path/to/scaler",
                is_live=False,
                window_size=30,
                max_drawdown_permitido=0.2,
                umbral_mantener_posicion=0.1,
                normalizar_portfolio=True,
                capital_inicial=10000.0,
                comision=0.001,
                slippage=0.0005,
                sma_short=10,
                sma_long=200,
                rsi_length=14,
                macd_fast=12,
                macd_slow=26,
                macd_signal=9,
                bbands_length=20,
                bbands_std=2.0,
            )
            
    def test_all_required_fields_present(self, temp_training_dir, monkeypatch):
        """Test que todos los campos requeridos están presentes."""
        monkeypatch.chdir(temp_training_dir["base_path"])
        
        args = Mock()
        args.train_id = temp_training_dir["train_id"]
        args.live = False
        
        config = ProductionConfig.load_config(args)
        
        # Verificar campos críticos
        required_fields = [
            "apalancamiento", "intervalo", "simbolo", "window_size",
            "max_drawdown_permitido", "umbral_mantener_posicion",
            "capital_inicial", "comision", "slippage",
            "sma_short", "sma_long", "rsi_length",
            "macd_fast", "macd_slow", "macd_signal",
            "bbands_length", "bbands_std"
        ]
        
        for field in required_fields:
            assert hasattr(config, field)
            assert getattr(config, field) is not None
