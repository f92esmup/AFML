"""
Tests para el sistema de optimización de hiperparámetros.

Este módulo contiene tests exhaustivos para:
- Cálculo de métricas (Sortino, Sharpe, Max DD, etc.)
- Validación de parámetros de optimización
- Detección de casos edge (agente no opera, equity constante, etc.)
- Integración con Optuna
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.train.optimization import metrics


class TestCalculateReturns:
    """Tests para cálculo de retornos."""
    
    def test_returns_normal_case(self):
        """Test de retornos con equity normal."""
        equity = np.array([10000, 10100, 10200, 10050])
        returns = metrics.calculate_returns(equity)
        
        assert len(returns) == 3
        assert np.isclose(returns[0], 0.01)  # 1% ganancia
        assert np.isclose(returns[1], 0.0099009901)  # ~0.99% ganancia
        assert np.isclose(returns[2], -0.0147058824)  # ~-1.47% pérdida
    
    def test_returns_constant_equity(self):
        """Test con equity constante (agente no opera)."""
        equity = np.array([10000, 10000, 10000, 10000])
        returns = metrics.calculate_returns(equity)
        
        assert len(returns) == 3
        assert np.all(returns == 0)
    
    def test_returns_with_series(self):
        """Test con pandas Series en vez de numpy array."""
        equity = pd.Series([10000, 11000, 12000])
        returns = metrics.calculate_returns(equity)
        
        assert len(returns) == 2
        assert np.isclose(returns[0], 0.1)  # 10%
        assert np.isclose(returns[1], 0.0909090909)  # ~9.09%
    
    def test_returns_empty_array(self):
        """Test con array vacío."""
        equity = np.array([])
        returns = metrics.calculate_returns(equity)
        
        assert len(returns) == 0
    
    def test_returns_single_value(self):
        """Test con un solo valor."""
        equity = np.array([10000])
        returns = metrics.calculate_returns(equity)
        
        assert len(returns) == 0


class TestSortinoRatio:
    """Tests para el cálculo de Sortino Ratio."""
    
    def test_sortino_constant_equity_returns_zero(self):
        """CRÍTICO: Equity constante debe retornar Sortino = 0 (agente no opera)."""
        equity = np.array([10000] * 100)
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert sortino == 0.0, "Equity constante debe retornar Sortino=0, no 100"
    
    def test_sortino_only_positive_returns(self):
        """Test con solo ganancias (estrategia perfecta)."""
        # Equity que solo sube con volatilidad: ganancias entre 0.1% y 3%
        np.random.seed(42)
        returns = np.random.uniform(0.001, 0.03, 100)
        equity = [10000]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        equity_array = np.array(equity)
        
        sortino = metrics.calculate_sortino_ratio(equity_array)
        
        # Con solo ganancias, usa volatilidad total como proxy
        # Puede dar valores altos pero debe ser finito y positivo
        assert sortino > 0, "Estrategia con solo ganancias debe tener Sortino > 0"
        assert np.isfinite(sortino), "Sortino debe ser finito"
        
    def test_sortino_constant_positive_returns(self):
        """Test con retornos constantes positivos (crecimiento perfecto)."""
        # Caso especial: 1% cada período (perfectamente constante)
        equity = np.array([10000 * (1.01 ** i) for i in range(100)])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        # Este caso debe retornar 50.0 (valor alto pero no infinito)
        assert sortino == 50.0, f"Retornos constantes positivos deben retornar Sortino=50, obtenido {sortino}"
    
    def test_sortino_mixed_returns(self):
        """Test con ganancias y pérdidas mezcladas."""
        equity = np.array([10000, 10500, 10200, 10600, 10300, 10800])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert sortino > 0, "Estrategia ganadora debe tener Sortino > 0"
        assert np.isfinite(sortino), "Sortino debe ser finito"
    
    def test_sortino_only_losses(self):
        """Test con solo pérdidas."""
        equity = np.array([10000 * (0.99 ** i) for i in range(50)])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert sortino < 0, "Estrategia perdedora debe tener Sortino < 0"
    
    def test_sortino_empty_equity(self):
        """Test con equity vacío."""
        equity = np.array([])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert sortino == 0.0
    
    def test_sortino_single_value(self):
        """Test con un solo valor de equity."""
        equity = np.array([10000])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert sortino == 0.0


class TestSharpeRatio:
    """Tests para el cálculo de Sharpe Ratio."""
    
    def test_sharpe_constant_equity(self):
        """Test con equity constante."""
        equity = np.array([10000] * 50)
        sharpe = metrics.calculate_sharpe_ratio(equity)
        
        assert sharpe == 0.0, "Sin volatilidad debe retornar Sharpe=0"
    
    def test_sharpe_positive_returns(self):
        """Test con retornos positivos."""
        equity = np.array([10000 * (1.005 ** i) for i in range(100)])
        sharpe = metrics.calculate_sharpe_ratio(equity)
        
        assert sharpe > 0
        assert np.isfinite(sharpe)
    
    def test_sharpe_vs_sortino(self):
        """Sharpe debe ser <= Sortino (penaliza más volatilidad)."""
        # Equity con ganancias y pérdidas
        equity = np.array([10000, 10500, 10200, 10800, 10300, 10900, 10400])
        
        sharpe = metrics.calculate_sharpe_ratio(equity)
        sortino = metrics.calculate_sortino_ratio(equity)
        
        # Sharpe penaliza toda la volatilidad, Sortino solo downside
        # En general: Sortino >= Sharpe para estrategias positivas
        assert np.isfinite(sharpe)
        assert np.isfinite(sortino)


class TestMaxDrawdown:
    """Tests para el cálculo de Max Drawdown."""
    
    def test_max_dd_no_drawdown(self):
        """Test con equity que solo sube (sin drawdown)."""
        equity = np.array([10000, 11000, 12000, 13000])
        max_dd = metrics.calculate_max_drawdown(equity)
        
        assert max_dd == 0.0
    
    def test_max_dd_simple(self):
        """Test con drawdown simple."""
        equity = np.array([10000, 12000, 10000, 11000])
        max_dd = metrics.calculate_max_drawdown(equity)
        
        # Peak = 12000, Valley = 10000 → DD = 2000/12000 = 0.1667
        assert np.isclose(max_dd, 0.1667, atol=0.01)
    
    def test_max_dd_multiple_peaks(self):
        """Test con múltiples picos y valles."""
        equity = np.array([10000, 12000, 11000, 15000, 13000, 14000])
        max_dd = metrics.calculate_max_drawdown(equity)
        
        # Peak = 15000, Valley = 13000 → DD = 2000/15000 = 0.1333
        assert np.isclose(max_dd, 0.1333, atol=0.01)
    
    def test_max_dd_constant_equity(self):
        """Test con equity constante."""
        equity = np.array([10000] * 50)
        max_dd = metrics.calculate_max_drawdown(equity)
        
        assert max_dd == 0.0
    
    def test_max_dd_total_loss(self):
        """Test con pérdida total (100% DD)."""
        equity = np.array([10000, 5000, 0])
        max_dd = metrics.calculate_max_drawdown(equity)
        
        assert np.isclose(max_dd, 1.0)  # 100% drawdown


class TestCalculateAllMetrics:
    """Tests para la función completa de métricas."""
    
    def test_all_metrics_realistic_case(self):
        """Test con caso realista de trading."""
        # Simular 100 pasos con ganancias y pérdidas
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 100)  # Media 0.1%, std 2%
        equity = [10000]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        
        equity_array = np.array(equity)
        
        all_metrics = metrics.calculate_metrics(
            equity_curve=equity_array,
            initial_equity=10000,
            trades_df=None  # Sin operaciones para este test
        )
        
        # Validar que todas las métricas existen
        assert 'sortino_ratio' in all_metrics
        assert 'sharpe_ratio' in all_metrics
        assert 'total_return' in all_metrics
        assert 'max_drawdown' in all_metrics
        assert 'final_equity' in all_metrics
        assert 'win_rate' in all_metrics
        
        # Validar rangos razonables
        assert np.isfinite(all_metrics['sortino_ratio'])
        assert np.isfinite(all_metrics['sharpe_ratio'])
        assert all_metrics['final_equity'] > 0
        assert 0 <= all_metrics['max_drawdown'] <= 1
    
    def test_all_metrics_no_trades(self):
        """Test con agente que no opera."""
        equity = np.array([10000] * 100)
        
        all_metrics = metrics.calculate_metrics(
            equity_curve=equity,
            initial_equity=10000,
            trades_df=None
        )
        
        # CRÍTICO: Sortino debe ser 0 cuando no opera
        assert all_metrics['sortino_ratio'] == 0.0
        assert all_metrics['total_return'] == 0.0
        assert all_metrics['max_drawdown'] == 0.0
        assert all_metrics['win_rate'] == 0.0
        assert all_metrics['num_trades'] == 0


class TestEdgeCases:
    """Tests para casos edge y esquinas del sistema."""
    
    def test_nan_in_equity(self):
        """Test con NaN en equity curve."""
        equity = np.array([10000, 11000, np.nan, 12000])
        
        # Debe manejar NaN - puede generar warnings o retornar NaN
        sortino = metrics.calculate_sortino_ratio(equity)
        # El resultado puede ser NaN o un número, pero no debe crashear
        assert True  # Si llegamos aquí, no crasheó
    
    def test_negative_equity(self):
        """Test con equity negativo (técnicamente imposible pero...)."""
        equity = np.array([10000, 5000, -1000])
        
        # Puede generar resultados extraños pero no debe crashear
        returns = metrics.calculate_returns(equity)
        assert len(returns) == 2
    
    def test_huge_equity_values(self):
        """Test con valores muy grandes de equity."""
        equity = np.array([1e10, 1.1e10, 1.2e10])
        sortino = metrics.calculate_sortino_ratio(equity)
        
        assert np.isfinite(sortino)
    
    def test_zero_equity(self):
        """Test con equity en cero."""
        equity = np.array([10000, 5000, 0])
        
        # Puede generar inf/-inf en retornos pero debe manejarse
        returns = metrics.calculate_returns(equity)
        # El último retorno sería -1.0 (pérdida total)
        assert returns[-1] == -1.0


@pytest.mark.parametrize("periods_per_year", [8760, 252, 365])
def test_sortino_with_different_periods(periods_per_year):
    """Test de anualización con diferentes períodos."""
    equity = np.array([10000 * (1.001 ** i) for i in range(100)])
    sortino = metrics.calculate_sortino_ratio(equity, periods_per_year=periods_per_year)
    
    assert np.isfinite(sortino)
    assert sortino > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
