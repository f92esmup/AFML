"""Tests para el módulo CLI de configuración del entrenamiento."""

import pytest
import sys
from argparse import Namespace
from unittest.mock import patch
from src.train.config.cli import parse_args_training


class TestParseArgsTraining:
    """Tests para la función parse_args_training."""

    def test_parse_args_valid_arguments(self, valid_cli_args: list):
        """Test que verifica el parseo exitoso de argumentos válidos."""
        with patch.object(sys, 'argv', ['prog'] + valid_cli_args):
            args = parse_args_training()
            
            assert args.symbol == "BTCUSDT"
            assert args.interval == "1h"
            assert args.train_start_date == "2023-01-01"
            assert args.train_end_date == "2023-06-30"
            assert args.eval_start_date == "2023-07-01"
            assert args.eval_end_date == "2023-12-31"
            assert args.episodios == 10
            assert args.episodios_eval == 5
            assert args.config == "src/train/config/config.yaml"

    def test_parse_args_default_values(self):
        """Test que verifica los valores por defecto de argumentos opcionales."""
        minimal_args = [
            "--symbol", "ETHUSDT",
            "--interval", "4h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + minimal_args):
            args = parse_args_training()
            
            assert args.episodios == 1  # Valor por defecto
            assert args.episodios_eval == 1  # Valor por defecto
            assert args.config == "src/train/config/config.yaml"  # Valor por defecto

    def test_parse_args_missing_required_symbol(self):
        """Test que verifica error cuando falta el argumento --symbol."""
        args_without_symbol = [
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_without_symbol):
            with pytest.raises(SystemExit):
                parse_args_training()

    def test_parse_args_missing_required_interval(self):
        """Test que verifica error cuando falta el argumento --interval."""
        args_without_interval = [
            "--symbol", "BTCUSDT",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_without_interval):
            with pytest.raises(SystemExit):
                parse_args_training()

    def test_parse_args_missing_train_dates(self):
        """Test que verifica error cuando faltan fechas de entrenamiento."""
        args_without_train_dates = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_without_train_dates):
            with pytest.raises(SystemExit):
                parse_args_training()

    def test_parse_args_missing_eval_dates(self):
        """Test que verifica error cuando faltan fechas de evaluación."""
        args_without_eval_dates = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_without_eval_dates):
            with pytest.raises(SystemExit):
                parse_args_training()

    def test_parse_args_empty_symbol(self):
        """Test que verifica validación de symbol vacío."""
        args_with_empty_symbol = [
            "--symbol", "",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_empty_symbol):
            with pytest.raises(ValueError, match="El argumento --symbol no puede estar vacío"):
                parse_args_training()

    def test_parse_args_empty_interval(self):
        """Test que verifica validación de interval vacío."""
        args_with_empty_interval = [
            "--symbol", "BTCUSDT",
            "--interval", "   ",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_empty_interval):
            with pytest.raises(ValueError, match="El argumento --interval no puede estar vacío"):
                parse_args_training()

    def test_parse_args_invalid_episodios_zero(self):
        """Test que verifica validación de episodios = 0."""
        args_with_zero_episodes = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31",
            "--episodios", "0"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_zero_episodes):
            with pytest.raises(ValueError, match="El número de episodios debe ser mayor que 0"):
                parse_args_training()

    def test_parse_args_invalid_episodios_negative(self):
        """Test que verifica validación de episodios negativos."""
        args_with_negative_episodes = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31",
            "--episodios", "-5"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_negative_episodes):
            with pytest.raises(ValueError, match="El número de episodios debe ser mayor que 0"):
                parse_args_training()

    def test_parse_args_invalid_episodios_eval_zero(self):
        """Test que verifica validación de episodios_eval = 0."""
        args_with_zero_eval_episodes = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31",
            "--episodios-eval", "0"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_zero_eval_episodes):
            with pytest.raises(ValueError, match="El número de episodios de evaluación debe ser mayor que 0"):
                parse_args_training()

    @pytest.mark.parametrize("invalid_date,arg_name", [
        ("2023/01/01", "train-start-date"),
        ("01-01-2023", "train-end-date"),
        ("2023-1-1", "eval-start-date"),
        ("23-01-01", "eval-end-date"),
        ("invalid", "train-start-date"),
    ])
    def test_parse_args_invalid_date_format(self, invalid_date: str, arg_name: str):
        """Test que verifica validación de formatos de fecha inválidos."""
        args_with_invalid_date = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        # Reemplazar la fecha específica con el valor inválido
        for i, arg in enumerate(args_with_invalid_date):
            if arg == f"--{arg_name}":
                args_with_invalid_date[i + 1] = invalid_date
                break
        
        with patch.object(sys, 'argv', ['prog'] + args_with_invalid_date):
            with pytest.raises(ValueError, match="debe estar en formato 'YYYY-MM-DD'"):
                parse_args_training()

    def test_parse_args_train_end_before_start(self):
        """Test que verifica error cuando fecha fin es anterior a fecha inicio (entrenamiento)."""
        args_with_reversed_dates = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-06-30",
            "--train-end-date", "2023-01-01",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_reversed_dates):
            with pytest.raises(ValueError, match="La fecha de fin de entrenamiento debe ser posterior"):
                parse_args_training()

    def test_parse_args_eval_end_before_start(self):
        """Test que verifica error cuando fecha fin es anterior a fecha inicio (evaluación)."""
        args_with_reversed_dates = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-12-31",
            "--eval-end-date", "2023-07-01"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_reversed_dates):
            with pytest.raises(ValueError, match="La fecha de fin de evaluación debe ser posterior"):
                parse_args_training()

    def test_parse_args_eval_not_after_train(self):
        """Test que verifica validación de walk-forward (eval debe ser posterior a train)."""
        args_with_overlapping_dates = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-12-31",
            "--eval-start-date", "2023-06-01",
            "--eval-end-date", "2023-12-31"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args_with_overlapping_dates):
            with pytest.raises(ValueError, match="Las fechas de evaluación deben ser posteriores"):
                parse_args_training()

    def test_parse_args_different_symbols_intervals(self):
        """Test que verifica el parseo de diferentes símbolos e intervalos."""
        test_cases = [
            ("ETHUSDT", "5m"),
            ("BNBUSDT", "15m"),
            ("ADAUSDT", "1d"),
            ("SOLUSDT", "4h")
        ]
        
        for symbol, interval in test_cases:
            args = [
                "--symbol", symbol,
                "--interval", interval,
                "--train-start-date", "2023-01-01",
                "--train-end-date", "2023-06-30",
                "--eval-start-date", "2023-07-01",
                "--eval-end-date", "2023-12-31"
            ]
            
            with patch.object(sys, 'argv', ['prog'] + args):
                parsed = parse_args_training()
                assert parsed.symbol == symbol
                assert parsed.interval == interval

    def test_parse_args_custom_config_path(self):
        """Test que verifica el parseo de ruta de configuración personalizada."""
        args = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31",
            "--config", "custom/path/to/config.yaml"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args):
            parsed = parse_args_training()
            assert parsed.config == "custom/path/to/config.yaml"

    def test_parse_args_large_episodios(self):
        """Test que verifica el parseo de un número grande de episodios."""
        args = [
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--train-start-date", "2023-01-01",
            "--train-end-date", "2023-06-30",
            "--eval-start-date", "2023-07-01",
            "--eval-end-date", "2023-12-31",
            "--episodios", "10000",
            "--episodios-eval", "1000"
        ]
        
        with patch.object(sys, 'argv', ['prog'] + args):
            parsed = parse_args_training()
            assert parsed.episodios == 10000
            assert parsed.episodios_eval == 1000
