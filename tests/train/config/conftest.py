"""Fixtures compartidas para los tests de configuración."""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def valid_config_yaml() -> Dict[str, Any]:
    """Retorna un diccionario con configuración válida para tests."""
    return {
        "data_downloader": {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "limit": 1000
        },
        "preprocesamiento": {
            "interpol_method": "linear",
            "indicadores": {
                "SMA_short": 10,
                "SMA_long": 50,
                "RSI_length": 14,
                "MACD_fast": 12,
                "MACD_slow": 26,
                "MACD_signal": 9,
                "BB_length": 20,
                "BB_std": 2.0
            }
        },
        "portafolio": {
            "capital_inicial": 10000.0,
            "apalancamiento": 1.0,
            "comision": 0.001,
            "slippage": 0.0005
        },
        "entorno": {
            "window_size": 30,
            "max_drawdown_permitido": 0.2,
            "factor_aversion_riesgo": 2.0,
            "umbral_mantener_posicion": 0.1,
            "penalizacion_no_operar": 0.0001,
            "episodios": 10,
            "normalizar_portfolio": True,
            "normalizar_recompensa": True,
            "penalizacion_pct": 0.00001
        },
        "SACmodel": {
            "policy": "MlpPolicy",
            "learning_rate": 0.0003,
            "buffer_size": 100000,
            "learning_starts": 1000,
            "batch_size": 256,
            "tau": 0.005,
            "gamma": 0.99,
            "ent_coef": "auto",
            "train_freq": [1, "step"],
            "gradient_steps": 1,
            "verbose": 1,
            "seed": 42
        },
        "policy_kwargs": {
            "net_arch": {
                "pi": [256, 256],
                "qf": [256, 256]
            },
            "log_std_init": -3,
            "n_critics": 2
        }
    }


@pytest.fixture
def temp_config_file(valid_config_yaml: Dict[str, Any]) -> Path:
    """Crea un archivo temporal de configuración YAML para tests."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(valid_config_yaml, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def valid_cli_args() -> list:
    """Retorna una lista de argumentos CLI válidos para tests."""
    return [
        "--symbol", "BTCUSDT",
        "--interval", "1h",
        "--train-start-date", "2023-01-01",
        "--train-end-date", "2023-06-30",
        "--eval-start-date", "2023-07-01",
        "--eval-end-date", "2023-12-31",
        "--episodios", "10",
        "--episodios-eval", "5",
        "--config", "src/train/config/config.yaml"
    ]


@pytest.fixture
def mock_args_namespace():
    """Retorna un namespace de argumentos mock para tests."""
    from argparse import Namespace
    return Namespace(
        symbol="BTCUSDT",
        interval="1h",
        train_start_date="2023-01-01",
        train_end_date="2023-06-30",
        eval_start_date="2023-07-01",
        eval_end_date="2023-12-31",
        episodios=10,
        episodios_eval=5,
        config="src/train/config/config.yaml"
    )
