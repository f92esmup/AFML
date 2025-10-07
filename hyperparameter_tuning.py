"""Script principal para optimización de hiperparámetros del sistema de Trading.

Este script utiliza Optuna para búsqueda bayesiana de los mejores hiperparámetros
del modelo SAC y del entorno de trading, optimizando el Sortino Ratio.

Uso:
    python hyperparameter_tuning.py --symbol BTCUSDT --interval 1h \\
        --train-start-date 2024-01-01 --train-end-date 2024-02-01 \\
        --eval-start-date 2024-02-02 --eval-end-date 2024-03-01 \\
        --n-trials 50 --timesteps-per-trial 5000

Output:
    - optimizaciones/optimization_YYYYMMDD_HHMMSS/
        - best_params.yaml           # Mejores parámetros encontrados
        - optimization_study.pkl      # Estudio completo de Optuna
        - visualizations/            # Gráficos interactivos
            - optimization_history.html
            - param_importances.html
            - slice_plot.html
            - parallel_coordinate.html
"""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

from src.utils.logger import setup_logger, configure_file_logging
from src.train.config import UnifiedConfig
from src.train.optimization import HyperparameterTuner
from src.train.optimization.ranges import get_recommended_ranges_info

# Configurar logger
setup_logger()
log = logging.getLogger("AFML.hyperparameter_tuning")


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos para optimización."""
    parser = argparse.ArgumentParser(
        description="Optimización de hiperparámetros para sistema de Trading con RL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_recommended_ranges_info()
    )
    
    # Configuración base
    parser.add_argument(
        '--config',
        type=str,
        default='src/train/config/config.yaml',
        help='Ruta al archivo de configuración base (default: src/train/config/config.yaml)'
    )
    
    # Parámetros de datos
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Par de trading (ej: BTCUSDT)'
    )
    
    parser.add_argument(
        '--interval',
        type=str,
        required=True,
        help='Intervalo de velas (ej: 1h, 4h, 1d)'
    )
    
    # Períodos de datos
    parser.add_argument(
        '--train-start-date',
        type=str,
        required=True,
        help='Fecha inicio entrenamiento (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--train-end-date',
        type=str,
        required=True,
        help='Fecha fin entrenamiento (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--eval-start-date',
        type=str,
        required=True,
        help='Fecha inicio evaluación (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--eval-end-date',
        type=str,
        required=True,
        help='Fecha fin evaluación (YYYY-MM-DD)'
    )
    
    # Parámetros de optimización
    parser.add_argument(
        '--n-trials',
        type=int,
        default=50,
        help='Número de trials a ejecutar (default: 50)'
    )
    
    parser.add_argument(
        '--timesteps-per-trial',
        type=int,
        default=5000,
        help='Timesteps de entrenamiento por trial (default: 5000, más rápido que 10k)'
    )
    
    parser.add_argument(
        '--n-eval-episodes',
        type=int,
        default=1,
        help='Episodios de evaluación por trial (default: 1)'
    )
    
    parser.add_argument(
        '--n-jobs',
        type=int,
        default=5,
        help='Número de trials en paralelo (default: 5, use -1 para todos los cores)'
    )
    
    # Qué optimizar
    parser.add_argument(
        '--optimize-sac',
        action='store_true',
        default=True,
        help='Optimizar parámetros del modelo SAC (default: True)'
    )
    
    parser.add_argument(
        '--optimize-env',
        action='store_true',
        default=True,
        help='Optimizar parámetros del entorno (default: True)'
    )
    
    parser.add_argument(
        '--optimize-network',
        action='store_true',
        default=True,
        help='Optimizar arquitectura de red (default: True)'
    )
    
    parser.add_argument(
        '--optimize-portfolio',
        action='store_false',
        help='Optimizar parámetros del portafolio (default: False)'
    )
    
    # Output
    parser.add_argument(
        '--output-dir',
        type=str,
        default='optimizaciones',
        help='Directorio base para guardar resultados (default: optimizaciones/)'
    )
    
    parser.add_argument(
        '--study-name',
        type=str,
        default=None,
        help='Nombre del estudio (default: auto-generado)'
    )
    
    # Optuna storage (opcional, para estudios persistentes)
    parser.add_argument(
        '--storage',
        type=str,
        default='none', # Esto es de una implementación a medias que no está operativa.
        help='URL de storage de Optuna (default: auto=SQLite en output_dir, "none"=en memoria)'
    )
    
    return parser.parse_args()


def create_output_structure(base_dir: str) -> Path:
    """Crea la estructura de directorios para guardar resultados.
    
    Args:
        base_dir: Directorio base
        
    Returns:
        Path del directorio creado
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(base_dir) / f"optimization_{timestamp}"
    
    # Crear directorios
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "visualizations").mkdir(exist_ok=True)
    
    log.info(f"Directorio de salida creado: {output_path}")
    
    return output_path


def main() -> None:
    """Función principal de optimización de hiperparámetros."""
    log.info("=" * 80)
    log.info("OPTIMIZACIÓN DE HIPERPARÁMETROS - SISTEMA DE TRADING RL")
    log.info("=" * 80)
    
    try:
        # 1. Parsear argumentos
        args = parse_args()
        
        log.info("Configuración de optimización:")
        log.info(f"  Config file: {args.config}")
        log.info(f"  Symbol: {args.symbol}")
        log.info(f"  Interval: {args.interval}")
        log.info(f"  Train period: {args.train_start_date} to {args.train_end_date}")
        log.info(f"  Eval period: {args.eval_start_date} to {args.eval_end_date}")
        log.info(f"  N trials: {args.n_trials}")
        log.info(f"  Timesteps per trial: {args.timesteps_per_trial}")
        log.info(f"  Optimize SAC: {args.optimize_sac}")
        log.info(f"  Optimize Env: {args.optimize_env}")
        log.info(f"  Optimize Network: {args.optimize_network}")
        log.info(f"  Optimize Portfolio: {args.optimize_portfolio}")
        log.info(f"  N jobs (parallel): {args.n_jobs}")
        
        # 2. Crear directorio de salida
        output_path = create_output_structure(args.output_dir)
        
        # Configurar logging a archivo
        log_file = output_path / "optimization.log"
        configure_file_logging(str(output_path))
        log.info(f"Logs guardados en: {log_file}")
        
        # 3. Cargar configuración base
        log.info("Cargando configuración base...")
        
        # Crear argumentos compatibles con UnifiedConfig
        from argparse import Namespace
        config_args = Namespace(
            config=args.config,  # ✅ Añadir ruta del archivo de configuración
            symbol=args.symbol,
            interval=args.interval,
            train_start_date=args.train_start_date,
            train_end_date=args.train_end_date,
            eval_start_date=args.eval_start_date,
            eval_end_date=args.eval_end_date,
            episodios_eval=args.n_eval_episodes,
            total_timesteps=args.timesteps_per_trial,
            learning_rate=None,  # Será optimizado
            batch_size=None,     # Será optimizado
            window_size=None,    # Será optimizado
        )
        
        base_config = UnifiedConfig.load_for_unified_training(config_args)
        log.info("Configuración base cargada exitosamente")
        
        # 4. Configurar storage
        storage_url = None
        if args.storage == 'auto':
            # Crear SQLite en el directorio de salida
            storage_url = f"sqlite:///{output_path}/optuna_study.db"
            log.info(f"Storage SQLite automático: {storage_url}")
        elif args.storage != 'none':
            storage_url = args.storage
            log.info(f"Storage configurado: {storage_url}")
        else:
            log.info("Storage en memoria (no persistente)")
        
        # 5. Crear optimizador
        log.info("Creando optimizador de hiperparámetros...")
        
        tuner = HyperparameterTuner(
            base_config=base_config,
            train_start=args.train_start_date,
            train_end=args.train_end_date,
            eval_start=args.eval_start_date,
            eval_end=args.eval_end_date,
            n_trials=args.n_trials,
            timesteps_per_trial=args.timesteps_per_trial,
            n_eval_episodes=args.n_eval_episodes,
            study_name=args.study_name,
            storage=storage_url,
            optimize_sac=args.optimize_sac,
            optimize_env=args.optimize_env,
            optimize_network=args.optimize_network,
            optimize_portfolio=args.optimize_portfolio,
        )
        
        # 6. Ejecutar optimización CON PARALELIZACIÓN
        log.info("Iniciando proceso de optimización...")
        log.info("Métrica objetivo: SORTINO RATIO (retorno ajustado por downside risk)")
        log.info(f"🚀 Paralelización: {args.n_jobs} trials en paralelo")
        log.info("=" * 80)
        
        study = tuner.optimize(
            n_jobs=args.n_jobs,
            show_progress_bar=True
        )
        
        # 7. Guardar resultados
        log.info("=" * 80)
        log.info("Guardando resultados...")
        
        results_file = output_path / "best_params.yaml"
        tuner.save_results(str(results_file))
        
        # 8. Generar visualizaciones
        log.info("Generando visualizaciones...")
        viz_dir = output_path / "visualizations"
        tuner.generate_visualizations(str(viz_dir))
        
        # 9. Resumen final
        log.info("=" * 80)
        log.info("✅ OPTIMIZACIÓN COMPLETADA EXITOSAMENTE")
        log.info("=" * 80)
        log.info(f"Mejor Sortino Ratio: {study.best_value:.3f}")
        log.info(f"Mejor trial: {study.best_trial.number}")
        log.info(f"Total de trials: {len(study.trials)}")
        log.info("")
        log.info(f"📁 Resultados guardados en: {output_path}")
        log.info(f"📄 Mejores parámetros: {results_file}")
        log.info(f"📊 Visualizaciones: {viz_dir}")
        log.info("")
        log.info("Próximos pasos:")
        log.info("  1. Revisar best_params.yaml para ver los mejores parámetros")
        log.info("  2. Abrir visualizations/*.html para análisis interactivo")
        log.info("  3. Usar los parámetros para entrenar modelo final con train.py")
        if storage_url and storage_url.startswith("sqlite"):
            log.info("")
            log.info("💡 Monitoreo en tiempo real (opcional):")
            log.info(f"   optuna-dashboard {storage_url}")
        log.info("=" * 80)
        
    except KeyboardInterrupt:
        log.warning("Optimización interrumpida por el usuario (Ctrl+C)")
        sys.exit(130)
        
    except Exception as e:
        log.error("!!! Error durante la optimización !!!")
        log.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
