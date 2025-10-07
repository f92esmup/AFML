"""Definición de rangos de búsqueda para optimización de hiperparámetros.

Este módulo define los espacios de búsqueda para diferentes categorías de parámetros:
- Modelo SAC (learning rate, batch size, etc.)
- Entorno de trading (window size, pesos de recompensa, etc.)
- Arquitectura de red neuronal
- Portafolio (apalancamiento, comisiones, etc.)
"""

import optuna
from typing import Dict, Any, List
import logging

log = logging.getLogger("AFML.optimization.ranges")


def suggest_sac_params(trial: optuna.Trial) -> Dict[str, Any]:
    """Define el espacio de búsqueda para hiperparámetros del modelo SAC.
    
    Args:
        trial: Objeto trial de Optuna
        
    Returns:
        Diccionario con parámetros sugeridos para SAC
    """
    params = {
        # Learning rate (log scale es mejor para este parámetro)
        'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True),
        
        # Batch size (potencias de 2 típicamente)
        'batch_size': trial.suggest_categorical('batch_size', [64, 128, 256, 512]),
        
        # Gamma (factor de descuento) - valores típicos para trading
        'gamma': trial.suggest_float('gamma', 0.95, 0.999),
        
        # Tau (soft update de target networks)
        'tau': trial.suggest_float('tau', 0.001, 0.02),
        
        # Entropy coefficient (auto_ con diferentes targets)
        'ent_coef_target': trial.suggest_float('ent_coef_target', 0.05, 0.3),
        
        # Learning starts (cuándo empezar a entrenar)
        'learning_starts': trial.suggest_int('learning_starts', 1000, 10000, step=1000),
        
        # Gradient steps (-1 = same as env steps, >0 = fixed)
        'gradient_steps': trial.suggest_categorical('gradient_steps', [-1, 1, 2]),
        
        # Buffer size
        'buffer_size': trial.suggest_categorical('buffer_size', [100000, 500000, 1000000]),
    }
    
    return params


def suggest_env_params(trial: optuna.Trial) -> Dict[str, Any]:
    """Define el espacio de búsqueda para parámetros del entorno de trading.
    
    Args:
        trial: Objeto trial de Optuna
        
    Returns:
        Diccionario con parámetros sugeridos para el entorno
    """
    params = {
        # Window size (tamaño de la ventana de observación)
        'window_size': trial.suggest_categorical('window_size', [20, 30, 50, 100]),
        
        # Factor de aversión al riesgo
        'factor_aversion_riesgo': trial.suggest_float('factor_aversion_riesgo', 1.0, 5.0),
        
        # Max drawdown permitido (10% a 25% - rango más conservador)
        'max_drawdown_permitido': trial.suggest_float('max_drawdown_permitido', 0.10, 0.25),
        
        # Factor de escala de recompensa
        'factor_escala_recompensa': trial.suggest_float('factor_escala_recompensa', 50.0, 200.0),
        
        # Pesos de componentes de recompensa
        'peso_retorno_base': trial.suggest_float('peso_retorno_base', 0.5, 2.0),
        'peso_temporal': trial.suggest_float('peso_temporal', 0.1, 0.5),
        'peso_gestion': trial.suggest_float('peso_gestion', 0.05, 0.4),
        'peso_drawdown': trial.suggest_float('peso_drawdown', 0.05, 0.3),
        
        # Umbrales
        'umbral_perdida_pct': trial.suggest_float('umbral_perdida_pct', 0.001, 0.01),
        'umbral_ganancia_pct': trial.suggest_float('umbral_ganancia_pct', 0.001, 0.01),
        
        # Penalización de inacción
        'penalizacion_no_operar': trial.suggest_float('penalizacion_no_operar', 0.0, 0.2),
    }
    
    return params


def suggest_network_architecture(trial: optuna.Trial) -> Dict[str, Any]:
    """Define el espacio de búsqueda para la arquitectura de red neuronal.
    
    Args:
        trial: Objeto trial de Optuna
        
    Returns:
        Diccionario con arquitectura sugerida
    """
    # Número de capas (2 a 10 para máxima flexibilidad)
    # NOTA: Puedes ajustar el rango según necesites (ej: 2-5 para redes más simples)
    n_layers = trial.suggest_int('n_layers', 2, 10)
    
    # Tamaño de capas (potencias de 2)
    layer_sizes = []
    for i in range(n_layers):
        # Cada capa tiene su propio tamaño independiente
        size = trial.suggest_categorical(f'layer_{i}_size', [128, 256, 512])
        layer_sizes.append(size)
    
    params = {
        'n_layers': n_layers,
        'layer_sizes': layer_sizes,
        'pi_layers': layer_sizes.copy(),  # Policy network
        'qf_layers': layer_sizes.copy(),  # Q-function network
        
        # Log std init (importante para exploración)
        'log_std_init': trial.suggest_float('log_std_init', -4.0, -2.0),
        
        # Número de críticos (Q-networks)
        'n_critics': trial.suggest_categorical('n_critics', [2, 3]),
    }
    
    return params


def suggest_portfolio_params(trial: optuna.Trial) -> Dict[str, Any]:
    """Define el espacio de búsqueda para parámetros del portafolio.
    
    Args:
        trial: Objeto trial de Optuna
        
    Returns:
        Diccionario con parámetros sugeridos para el portafolio
    """
    params = {
        # Apalancamiento (debe ser entero: 1x, 5x, 10x, 15x, 20x)
        'apalancamiento': trial.suggest_int('apalancamiento', 5, 20),
        
        # Comisión (típicamente fija, pero se puede optimizar)
        # 'comision': trial.suggest_float('comision', 0.0005, 0.002),
        
        # Slippage
        # 'slippage': trial.suggest_float('slippage', 0.0005, 0.002),
    }
    
    return params


def get_search_space(
    trial: optuna.Trial,
    optimize_sac: bool = True,
    optimize_env: bool = True,
    optimize_network: bool = True,
    optimize_portfolio: bool = False
) -> Dict[str, Any]:
    """Obtiene el espacio de búsqueda completo combinando todas las categorías.
    
    Args:
        trial: Objeto trial de Optuna
        optimize_sac: Si True, optimiza parámetros de SAC
        optimize_env: Si True, optimiza parámetros del entorno
        optimize_network: Si True, optimiza arquitectura de red
        optimize_portfolio: Si True, optimiza parámetros del portafolio
        
    Returns:
        Diccionario con todos los parámetros sugeridos
    """
    search_space = {}
    
    if optimize_sac:
        log.debug("Agregando parámetros de SAC al espacio de búsqueda")
        search_space['SACmodel'] = suggest_sac_params(trial)
    
    if optimize_env:
        log.debug("Agregando parámetros del entorno al espacio de búsqueda")
        search_space['entorno'] = suggest_env_params(trial)
    
    if optimize_network:
        log.debug("Agregando arquitectura de red al espacio de búsqueda")
        search_space['network'] = suggest_network_architecture(trial)
    
    if optimize_portfolio:
        log.debug("Agregando parámetros del portafolio al espacio de búsqueda")
        search_space['portafolio'] = suggest_portfolio_params(trial)
    
    return search_space


def get_default_fixed_params() -> Dict[str, Any]:
    """Retorna parámetros fijos que no se optimizan.
    
    Returns:
        Diccionario con parámetros fijos
    """
    return {
        'SACmodel': {
            'policy': 'MultiInputPolicy',
            'verbose': 0,  # Silencioso durante optimización
            'seed': None,  # Diferente seed por trial para robustez
            'train_freq': (1, 'step'),
        },
        'portafolio': {
            'capital_inicial': 10000.0,
            'comision': 0.001,
            'slippage': 0.001,
        },
        'entorno': {
            'normalizar_portfolio': True,
            'normalizar_recompensa': True,
            'umbral_mantener_posicion': 0.05,
        },
    }


def get_recommended_ranges_info() -> str:
    """Retorna información sobre los rangos recomendados para cada parámetro.
    
    Returns:
        String formateado con información de rangos
    """
    info = """
    ════════════════════════════════════════════════════════════════
    RANGOS DE BÚSQUEDA PARA OPTIMIZACIÓN DE HIPERPARÁMETROS
    ════════════════════════════════════════════════════════════════
    
    📊 MODELO SAC:
    ─────────────────────────────────────────────────────────────────
    • learning_rate:      [1e-5, 1e-3]  (log scale)
    • batch_size:         [64, 128, 256, 512]
    • gamma:              [0.95, 0.999]
    • tau:                [0.001, 0.02]
    • ent_coef_target:    [0.05, 0.3]
    • learning_starts:    [1000, 10000]
    • gradient_steps:     [-1, 1, 2]
    • buffer_size:        [100k, 500k, 1M]
    
    🎯 ENTORNO DE TRADING:
    ─────────────────────────────────────────────────────────────────
    • window_size:                  [20, 30, 50, 100]
    • factor_aversion_riesgo:       [1.0, 5.0]
    • max_drawdown_permitido:       [0.10, 0.25]  (10%-25%, conservador)
    • factor_escala_recompensa:     [50.0, 200.0]
    • peso_retorno_base:            [0.5, 2.0]
    • peso_temporal:                [0.1, 0.5]
    • peso_gestion:                 [0.05, 0.4]
    • peso_drawdown:                [0.05, 0.3]
    • umbral_perdida_pct:           [0.001, 0.01]
    • umbral_ganancia_pct:          [0.001, 0.01]
    • penalizacion_no_operar:       [0.0, 0.2]
    
    🧠 ARQUITECTURA DE RED:
    ─────────────────────────────────────────────────────────────────
    • n_layers:           [2, 10]  (2 a 10 capas ocultas)
    • layer_size:         [128, 256, 512]
    • log_std_init:       [-4.0, -2.0]
    • n_critics:          [2, 3]
    
    💼 PORTAFOLIO:
    ─────────────────────────────────────────────────────────────────
    • apalancamiento:     [5.0, 20.0]
    
    ════════════════════════════════════════════════════════════════
    """
    return info
