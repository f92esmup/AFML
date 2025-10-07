"""Configuración compartida para tests de optimización."""

import pytest
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def pytest_configure(config):
    """Configuración de markers personalizados."""
    config.addinivalue_line(
        "markers", "slow: marca tests que tardan más de 10 segundos"
    )
    config.addinivalue_line(
        "markers", "integration: tests de integración completa"
    )
