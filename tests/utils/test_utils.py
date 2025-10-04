"""Tests para el módulo utils.py."""

import pytest
from src.utils.utils import calcular_steps


class TestCalcularSteps:
    """Tests para la función calcular_steps."""

    def test_calcular_steps_valores_normales(self):
        """Verifica que el cálculo es correcto con valores normales."""
        result = calcular_steps(num_episodios=100, max_steps_per_episode=1000)
        assert result == 100_000
        
    def test_calcular_steps_valores_pequenos(self):
        """Verifica que funciona con valores pequeños."""
        result = calcular_steps(num_episodios=1, max_steps_per_episode=1)
        assert result == 1
        
    def test_calcular_steps_valores_grandes(self):
        """Verifica que funciona con valores grandes."""
        result = calcular_steps(num_episodios=10_000, max_steps_per_episode=50_000)
        assert result == 500_000_000
        
    def test_calcular_steps_episodios_cero_raise_error(self):
        """Verifica que lanza ValueError cuando num_episodios es 0."""
        with pytest.raises(ValueError, match="num_episodios y max_steps_per_episode deben ser mayores que 0"):
            calcular_steps(num_episodios=0, max_steps_per_episode=1000)
            
    def test_calcular_steps_episodios_negativo_raise_error(self):
        """Verifica que lanza ValueError cuando num_episodios es negativo."""
        with pytest.raises(ValueError, match="num_episodios y max_steps_per_episode deben ser mayores que 0"):
            calcular_steps(num_episodios=-10, max_steps_per_episode=1000)
            
    def test_calcular_steps_max_steps_cero_raise_error(self):
        """Verifica que lanza ValueError cuando max_steps_per_episode es 0."""
        with pytest.raises(ValueError, match="num_episodios y max_steps_per_episode deben ser mayores que 0"):
            calcular_steps(num_episodios=100, max_steps_per_episode=0)
            
    def test_calcular_steps_max_steps_negativo_raise_error(self):
        """Verifica que lanza ValueError cuando max_steps_per_episode es negativo."""
        with pytest.raises(ValueError, match="num_episodios y max_steps_per_episode deben ser mayores que 0"):
            calcular_steps(num_episodios=100, max_steps_per_episode=-500)
            
    def test_calcular_steps_ambos_negativos_raise_error(self):
        """Verifica que lanza ValueError cuando ambos valores son negativos."""
        with pytest.raises(ValueError, match="num_episodios y max_steps_per_episode deben ser mayores que 0"):
            calcular_steps(num_episodios=-10, max_steps_per_episode=-500)
            
    def test_calcular_steps_tipo_retorno_es_int(self):
        """Verifica que el valor retornado es de tipo int."""
        result = calcular_steps(num_episodios=10, max_steps_per_episode=100)
        assert isinstance(result, int)
        
    @pytest.mark.parametrize("episodios,steps,expected", [
        (1, 1, 1),
        (10, 10, 100),
        (100, 100, 10_000),
        (50, 200, 10_000),
        (200, 50, 10_000),
        (1000, 5000, 5_000_000),
    ])
    def test_calcular_steps_multiples_casos(self, episodios, steps, expected):
        """Verifica múltiples casos de cálculo usando parametrize."""
        result = calcular_steps(num_episodios=episodios, max_steps_per_episode=steps)
        assert result == expected
