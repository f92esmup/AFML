#!/usr/bin/env python3
"""
Script de prueba rápida del sistema de optimización de hiperparámetros.

Este script ejecuta una optimización de prueba con configuración mínima
para validar que todo funciona correctamente.

Uso:
    python3 test_optimization.py [--fast | --medium | --full]
"""

import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def run_test(mode: str = "fast") -> bool:
    """Ejecuta una prueba del sistema de optimización.
    
    Args:
        mode: Nivel de prueba ("fast", "medium", "full")
        
    Returns:
        True si la prueba fue exitosa, False en caso contrario
    """
    # Configuraciones según el modo
    configs = {
        "fast": {
            "n_trials": 2,
            "timesteps": 1000,
            "train_days": 30,  # 1 mes
            "eval_days": 15,   # 15 días
            "description": "Prueba ultra rápida (2-5 minutos)"
        },
        "medium": {
            "n_trials": 5,
            "timesteps": 3000,
            "train_days": 60,  # 2 meses
            "eval_days": 30,   # 1 mes
            "description": "Prueba media (10-20 minutos)"
        },
        "full": {
            "n_trials": 10,
            "timesteps": 5000,
            "train_days": 90,  # 3 meses
            "eval_days": 30,   # 1 mes
            "description": "Prueba completa (30-60 minutos)"
        }
    }
    
    if mode not in configs:
        log.error(f"Modo '{mode}' no válido. Usa: fast, medium, o full")
        return False
    
    config = configs[mode]
    
    log.info("=" * 80)
    log.info(f"🧪 PRUEBA DE OPTIMIZACIÓN - MODO: {mode.upper()}")
    log.info("=" * 80)
    log.info(f"Descripción: {config['description']}")
    log.info(f"Trials: {config['n_trials']}")
    log.info(f"Timesteps por trial: {config['timesteps']}")
    log.info(f"Período entrenamiento: {config['train_days']} días")
    log.info(f"Período evaluación: {config['eval_days']} días")
    log.info("=" * 80)
    
    # Calcular fechas
    from datetime import timedelta
    base_date = datetime(2024, 1, 1)
    
    train_start = base_date
    train_end = base_date + timedelta(days=config['train_days'])
    eval_start = train_end + timedelta(days=1)
    eval_end = eval_start + timedelta(days=config['eval_days'])
    
    # Formatear fechas
    train_start_str = train_start.strftime('%Y-%m-%d')
    train_end_str = train_end.strftime('%Y-%m-%d')
    eval_start_str = eval_start.strftime('%Y-%m-%d')
    eval_end_str = eval_end.strftime('%Y-%m-%d')
    
    log.info(f"📅 Train: {train_start_str} a {train_end_str}")
    log.info(f"📅 Eval:  {eval_start_str} a {eval_end_str}")
    log.info("")
    
    # Construir comando
    cmd = [
        "python3", "hyperparameter_tuning.py",
        "--symbol", "BTCUSDT",
        "--interval", "1h",
        "--train-start-date", train_start_str,
        "--train-end-date", train_end_str,
        "--eval-start-date", eval_start_str,
        "--eval-end-date", eval_end_str,
        "--n-trials", str(config['n_trials']),
        "--timesteps-per-trial", str(config['timesteps']),
    ]
    
    log.info("🚀 Ejecutando optimización...")
    log.info(f"Comando: {' '.join(cmd)}")
    log.info("")
    
    # Ejecutar
    import subprocess
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Mostrar salida en tiempo real
            text=True
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        log.info("")
        log.info("=" * 80)
        log.info("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        log.info("=" * 80)
        log.info(f"⏱️  Duración: {duration:.1f} segundos ({duration/60:.1f} minutos)")
        log.info("")
        
        # Buscar directorio de resultados
        optim_dir = Path("optimizaciones")
        if optim_dir.exists():
            latest_optim = sorted(optim_dir.glob("optimization_*"))[-1]
            log.info(f"📁 Resultados guardados en: {latest_optim}")
            
            best_params_file = latest_optim / "best_params.yaml"
            if best_params_file.exists():
                log.info(f"📊 Mejores parámetros: {best_params_file}")
                
                # Mostrar resumen de resultados
                import yaml
                with open(best_params_file, 'r') as f:
                    data = yaml.safe_load(f)
                
                metrics = data.get('best_metrics', {})
                log.info("")
                log.info("📈 MÉTRICAS DEL MEJOR TRIAL:")
                log.info(f"   Sortino Ratio:  {metrics.get('sortino_ratio', 'N/A'):.4f}")
                log.info(f"   Sharpe Ratio:   {metrics.get('sharpe_ratio', 'N/A'):.4f}")
                log.info(f"   Total Return:   {metrics.get('total_return', 'N/A'):.4f} ({metrics.get('total_return', 0)*100:.2f}%)")
                log.info(f"   Max Drawdown:   {metrics.get('max_drawdown', 'N/A'):.4f} ({metrics.get('max_drawdown', 0)*100:.2f}%)")
                log.info(f"   Final Equity:   ${metrics.get('final_equity', 'N/A'):.2f}")
        
        log.info("")
        log.info("🎉 El sistema de optimización funciona correctamente!")
        log.info("")
        
        return True
        
    except subprocess.CalledProcessError as e:
        log.error("")
        log.error("=" * 80)
        log.error("❌ ERROR EN LA PRUEBA")
        log.error("=" * 80)
        log.error(f"Código de salida: {e.returncode}")
        log.error("El sistema de optimización tiene problemas.")
        log.error("")
        return False
        
    except KeyboardInterrupt:
        log.warning("")
        log.warning("⚠️  Prueba interrumpida por el usuario (Ctrl+C)")
        log.warning("")
        return False
        
    except Exception as e:
        log.error("")
        log.error("=" * 80)
        log.error("❌ ERROR INESPERADO")
        log.error("=" * 80)
        log.error(f"Error: {e}", exc_info=True)
        log.error("")
        return False


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Prueba rápida del sistema de optimización de hiperparámetros",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos de prueba:
  fast    - Prueba ultra rápida (2 trials, 1000 timesteps, ~2-5 minutos)
  medium  - Prueba media (5 trials, 3000 timesteps, ~10-20 minutos)
  full    - Prueba completa (10 trials, 5000 timesteps, ~30-60 minutos)

Ejemplos:
  python3 test_optimization.py --fast
  python3 test_optimization.py --medium
  python3 test_optimization.py --full
        """
    )
    
    # Crear grupo mutuamente exclusivo
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--fast',
        action='store_true',
        help='Prueba ultra rápida (2-5 minutos)'
    )
    mode_group.add_argument(
        '--medium',
        action='store_true',
        help='Prueba media (10-20 minutos)'
    )
    mode_group.add_argument(
        '--full',
        action='store_true',
        help='Prueba completa (30-60 minutos)'
    )
    
    args = parser.parse_args()
    
    # Determinar modo
    if args.fast:
        mode = "fast"
    elif args.medium:
        mode = "medium"
    elif args.full:
        mode = "full"
    else:
        # Default: fast
        log.info("No se especificó modo, usando --fast por defecto")
        log.info("Usa --help para ver todas las opciones")
        log.info("")
        mode = "fast"
    
    # Ejecutar prueba
    success = run_test(mode)
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
