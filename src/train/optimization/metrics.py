"""Cálculo de métricas de rendimiento para evaluación de estrategias de trading.

Este módulo proporciona funciones para calcular métricas financieras estándar
como Sortino Ratio, Sharpe Ratio, Max Drawdown, Win Rate, etc.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
import logging

log = logging.getLogger("AFML.optimization.metrics")


def calculate_returns(equity_curve: np.ndarray | pd.Series) -> np.ndarray:
    """Calcula los retornos porcentuales de una curva de equity.
    
    Args:
        equity_curve: Serie temporal de valores de equity
        
    Returns:
        Array de retornos porcentuales
    """
    if isinstance(equity_curve, pd.Series):
        equity_curve = equity_curve.values
    
    if len(equity_curve) < 2:
        return np.array([])
    
    returns = np.diff(equity_curve) / equity_curve[:-1]
    return returns


def calculate_sortino_ratio(
    equity_curve: np.ndarray | pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 8760  # Horas en un año (para 1h candles)
) -> float:
    """Calcula el Sortino Ratio (retorno ajustado por downside risk).
    
    El Sortino Ratio es superior al Sharpe para trading porque solo penaliza
    la volatilidad negativa, no las ganancias volátiles.
    
    Formula:
        Sortino = (Retorno promedio - Risk free rate) / Downside deviation
    
    Args:
        equity_curve: Curva de equity del portafolio
        risk_free_rate: Tasa libre de riesgo anualizada (default: 0.0)
        periods_per_year: Número de períodos por año para anualización
        
    Returns:
        Sortino Ratio (mayor es mejor). Retorna 0.0 si no hay datos suficientes.
    """
    returns = calculate_returns(equity_curve)
    
    if len(returns) == 0:
        log.warning("No hay suficientes datos para calcular Sortino Ratio")
        return 0.0
    
    # Retorno promedio
    mean_return = np.mean(returns)
    
    # Calcular downside deviation (solo retornos negativos)
    downside_returns = returns[returns < 0]
    
    if len(downside_returns) == 0:
        # No hay retornos negativos - estrategia perfecta
        log.info("No hay retornos negativos - Sortino Ratio infinito, retornando valor alto")
        return 100.0  # Valor arbitrariamente alto
    
    downside_std = np.std(downside_returns, ddof=1)
    
    if downside_std == 0:
        log.warning("Downside deviation es 0, retornando 0.0")
        return 0.0
    
    # Anualizar
    annualized_return = mean_return * periods_per_year
    annualized_downside_std = downside_std * np.sqrt(periods_per_year)
    
    # Calcular Sortino
    sortino = (annualized_return - risk_free_rate) / annualized_downside_std
    
    return float(sortino)


def calculate_sharpe_ratio(
    equity_curve: np.ndarray | pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 8760
) -> float:
    """Calcula el Sharpe Ratio (retorno ajustado por volatilidad total).
    
    Formula:
        Sharpe = (Retorno promedio - Risk free rate) / Desviación estándar
    
    Args:
        equity_curve: Curva de equity del portafolio
        risk_free_rate: Tasa libre de riesgo anualizada (default: 0.0)
        periods_per_year: Número de períodos por año para anualización
        
    Returns:
        Sharpe Ratio (mayor es mejor). Retorna 0.0 si no hay datos suficientes.
    """
    returns = calculate_returns(equity_curve)
    
    if len(returns) == 0:
        log.warning("No hay suficientes datos para calcular Sharpe Ratio")
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    if std_return == 0:
        log.warning("Desviación estándar es 0, retornando 0.0")
        return 0.0
    
    # Anualizar
    annualized_return = mean_return * periods_per_year
    annualized_std = std_return * np.sqrt(periods_per_year)
    
    # Calcular Sharpe
    sharpe = (annualized_return - risk_free_rate) / annualized_std
    
    return float(sharpe)


def calculate_max_drawdown(equity_curve: np.ndarray | pd.Series) -> float:
    """Calcula el máximo drawdown (mayor caída desde un pico).
    
    Args:
        equity_curve: Curva de equity del portafolio
        
    Returns:
        Max drawdown como valor positivo entre 0 y 1 (ej: 0.15 = 15% drawdown)
    """
    if isinstance(equity_curve, pd.Series):
        equity_curve = equity_curve.values
    
    if len(equity_curve) < 2:
        return 0.0
    
    # Calcular peak acumulado
    cummax = np.maximum.accumulate(equity_curve)
    
    # Calcular drawdown en cada punto
    drawdown = (cummax - equity_curve) / cummax
    
    # Máximo drawdown
    max_dd = np.max(drawdown)
    
    return float(max_dd)


def calculate_total_return(
    initial_equity: float,
    final_equity: float
) -> float:
    """Calcula el retorno total porcentual.
    
    Args:
        initial_equity: Capital inicial
        final_equity: Capital final
        
    Returns:
        Retorno total como decimal (ej: 0.25 = 25% ganancia)
    """
    if initial_equity <= 0:
        log.warning("Capital inicial <= 0, retornando 0.0")
        return 0.0
    
    total_return = (final_equity - initial_equity) / initial_equity
    return float(total_return)


def calculate_win_rate(trades_df: pd.DataFrame) -> float:
    """Calcula el win rate (porcentaje de operaciones ganadoras).
    
    Args:
        trades_df: DataFrame con columna 'pnl_realizado' o 'profit'
        
    Returns:
        Win rate entre 0 y 1 (ej: 0.6 = 60% operaciones ganadoras)
    """
    if trades_df is None or len(trades_df) == 0:
        return 0.0
    
    # Intentar encontrar columna de PnL
    pnl_col = None
    for col in ['pnl_realizado', 'profit', 'pnl', 'return']:
        if col in trades_df.columns:
            pnl_col = col
            break
    
    if pnl_col is None:
        log.warning("No se encontró columna de PnL en trades_df")
        return 0.0
    
    winning_trades = (trades_df[pnl_col] > 0).sum()
    total_trades = len(trades_df)
    
    if total_trades == 0:
        return 0.0
    
    win_rate = winning_trades / total_trades
    return float(win_rate)


def calculate_profit_factor(trades_df: pd.DataFrame) -> float:
    """Calcula el profit factor (ganancia bruta / pérdida bruta).
    
    Args:
        trades_df: DataFrame con columna 'pnl_realizado' o 'profit'
        
    Returns:
        Profit factor (>1 es ganador, >2 es excelente)
    """
    if trades_df is None or len(trades_df) == 0:
        return 0.0
    
    # Intentar encontrar columna de PnL
    pnl_col = None
    for col in ['pnl_realizado', 'profit', 'pnl', 'return']:
        if col in trades_df.columns:
            pnl_col = col
            break
    
    if pnl_col is None:
        return 0.0
    
    gross_profit = trades_df[trades_df[pnl_col] > 0][pnl_col].sum()
    gross_loss = abs(trades_df[trades_df[pnl_col] < 0][pnl_col].sum())
    
    if gross_loss == 0:
        if gross_profit > 0:
            return 999.0  # Valor alto (no hay pérdidas)
        return 0.0
    
    profit_factor = gross_profit / gross_loss
    return float(profit_factor)


def calculate_metrics(
    equity_curve: np.ndarray | pd.Series,
    initial_equity: float,
    trades_df: Optional[pd.DataFrame] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 8760
) -> Dict[str, float]:
    """Calcula un conjunto completo de métricas de rendimiento.
    
    Args:
        equity_curve: Curva de equity del portafolio
        initial_equity: Capital inicial
        trades_df: DataFrame con historial de trades (opcional)
        risk_free_rate: Tasa libre de riesgo anualizada
        periods_per_year: Períodos por año para anualización
        
    Returns:
        Diccionario con todas las métricas calculadas
    """
    if isinstance(equity_curve, pd.Series):
        final_equity = equity_curve.iloc[-1] if len(equity_curve) > 0 else initial_equity
    else:
        final_equity = equity_curve[-1] if len(equity_curve) > 0 else initial_equity
    
    metrics = {
        # Métricas principales de riesgo-retorno
        'sortino_ratio': calculate_sortino_ratio(
            equity_curve, risk_free_rate, periods_per_year
        ),
        'sharpe_ratio': calculate_sharpe_ratio(
            equity_curve, risk_free_rate, periods_per_year
        ),
        
        # Métricas de retorno
        'total_return': calculate_total_return(initial_equity, final_equity),
        'final_equity': float(final_equity),
        
        # Métricas de riesgo
        'max_drawdown': calculate_max_drawdown(equity_curve),
        
        # Métricas de trading (si hay datos)
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'num_trades': 0,
    }
    
    if trades_df is not None and len(trades_df) > 0:
        metrics['win_rate'] = calculate_win_rate(trades_df)
        metrics['profit_factor'] = calculate_profit_factor(trades_df)
        metrics['num_trades'] = len(trades_df)
    
    return metrics


def log_metrics(metrics: Dict[str, Any], prefix: str = "") -> None:
    """Imprime las métricas de forma legible en el log.
    
    Args:
        metrics: Diccionario con métricas
        prefix: Prefijo para los mensajes de log
    """
    log.info(f"{prefix}{'=' * 60}")
    log.info(f"{prefix}MÉTRICAS DE RENDIMIENTO")
    log.info(f"{prefix}{'=' * 60}")
    log.info(f"{prefix}Sortino Ratio:    {metrics.get('sortino_ratio', 0.0):>8.3f}")
    log.info(f"{prefix}Sharpe Ratio:     {metrics.get('sharpe_ratio', 0.0):>8.3f}")
    log.info(f"{prefix}Total Return:     {metrics.get('total_return', 0.0):>8.2%}")
    log.info(f"{prefix}Max Drawdown:     {metrics.get('max_drawdown', 0.0):>8.2%}")
    log.info(f"{prefix}Final Equity:     ${metrics.get('final_equity', 0.0):>8.2f}")
    log.info(f"{prefix}Win Rate:         {metrics.get('win_rate', 0.0):>8.2%}")
    log.info(f"{prefix}Profit Factor:    {metrics.get('profit_factor', 0.0):>8.2f}")
    log.info(f"{prefix}Num Trades:       {metrics.get('num_trades', 0):>8}")
    log.info(f"{prefix}{'=' * 60}")
