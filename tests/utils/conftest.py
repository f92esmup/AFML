"""Fixtures compartidas para los tests del módulo utils."""

import pytest
import os
import logging
import tempfile
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Generator[str, None, None]:
    """
    Crea un directorio temporal para archivos de log.
    
    Args:
        tmp_path: Directorio temporal proporcionado por pytest
        
    Yields:
        str: Ruta al directorio temporal
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)
    yield str(log_dir)


@pytest.fixture
def temp_log_file(temp_log_dir: str) -> Generator[str, None, None]:
    """
    Crea un archivo temporal para logs.
    
    Args:
        temp_log_dir: Directorio temporal de logs
        
    Yields:
        str: Ruta al archivo de log temporal
    """
    log_file = os.path.join(temp_log_dir, "test.log")
    yield log_file
    # Cleanup
    if os.path.exists(log_file):
        os.remove(log_file)


@pytest.fixture
def clean_logger():
    """
    Limpia los handlers del logger antes y después de cada test.
    
    Yields:
        logging.Logger: Logger limpio para testing
    """
    logger = logging.getLogger("AFML")
    # Limpiar handlers antes del test
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    
    yield logger
    
    # Limpiar handlers después del test
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


@pytest.fixture
def clean_sb3_logger():
    """
    Limpia los handlers del logger de stable-baselines3.
    
    Yields:
        logging.Logger: Logger de SB3 limpio para testing
    """
    logger = logging.getLogger("stable_baselines3")
    # Limpiar handlers antes del test
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    
    yield logger
    
    # Limpiar handlers después del test
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


@pytest.fixture
def training_base_dir(tmp_path: Path) -> Generator[str, None, None]:
    """
    Crea un directorio temporal que simula un directorio de entrenamiento.
    
    Args:
        tmp_path: Directorio temporal proporcionado por pytest
        
    Yields:
        str: Ruta al directorio de entrenamiento simulado
    """
    train_dir = tmp_path / "entrenamientos" / "train_BTCUSDT_20250104_120000"
    train_dir.mkdir(parents=True, exist_ok=True)
    yield str(train_dir)
