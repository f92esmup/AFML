"""Motor de optimización de hiperparámetros con Optuna.

Este módulo implementa la lógica principal de optimización usando Optuna
para búsqueda bayesiana de hiperparámetros del sistema de trading.
"""

import os
import sys
import logging
import gc
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
import yaml
import copy

# Importar componentes del sistema
from src.train.config import UnifiedConfig
from src.train.AdquisicionDatos.adquisicion import DataDownloader
from src.train.AdquisicionDatos.preprocesamiento import Preprocesamiento
from src.train.Entrenamiento.entorno import TradingEnv, Portafolio
from src.train.Entrenamiento.agente import AgenteSac
from src.utils.logger import setup_logger
from binance.client import Client

# Importar funciones del módulo de optimización
from .metrics import calculate_metrics, log_metrics
from .ranges import get_search_space, get_default_fixed_params

log = logging.getLogger("AFML.optimization.tuner")


class HyperparameterTuner:
    """Optimizador de hiperparámetros usando Optuna."""
    
    def __init__(
        self,
        base_config: UnifiedConfig,
        train_start: str,
        train_end: str,
        eval_start: str,
        eval_end: str,
        n_trials: int = 50,
        timesteps_per_trial: int = 5000,
        n_eval_episodes: int = 1,
        study_name: Optional[str] = None,
        storage: Optional[str] = None,
        optimize_sac: bool = True,
        optimize_env: bool = True,
        optimize_network: bool = True,
        optimize_portfolio: bool = False,
    ):
        """Inicializa el optimizador de hiperparámetros.
        
        Args:
            base_config: Configuración base a partir de la cual optimizar
            train_start: Fecha inicio de entrenamiento (YYYY-MM-DD)
            train_end: Fecha fin de entrenamiento (YYYY-MM-DD)
            eval_start: Fecha inicio de evaluación (YYYY-MM-DD)
            eval_end: Fecha fin de evaluación (YYYY-MM-DD)
            n_trials: Número de trials a ejecutar
            timesteps_per_trial: Timesteps de entrenamiento por trial (reducido para rapidez)
            n_eval_episodes: Episodios de evaluación por trial
            study_name: Nombre del estudio (para logging/storage)
            storage: URL de storage de Optuna (None = en memoria)
            optimize_sac: Si True, optimiza parámetros de SAC
            optimize_env: Si True, optimiza parámetros del entorno
            optimize_network: Si True, optimiza arquitectura de red
            optimize_portfolio: Si True, optimiza parámetros del portafolio
        """
        log.info("Inicializando optimizador de hiperparámetros...")
        
        self.base_config = base_config
        self.train_start = train_start
        self.train_end = train_end
        self.eval_start = eval_start
        self.eval_end = eval_end
        self.n_trials = n_trials
        self.timesteps_per_trial = timesteps_per_trial
        self.n_eval_episodes = n_eval_episodes
        
        # Configuración de optimización
        self.optimize_sac = optimize_sac
        self.optimize_env = optimize_env
        self.optimize_network = optimize_network
        self.optimize_portfolio = optimize_portfolio
        
        # Cliente de Binance
        self.client = Client()
        
        # Datos (se cargarán una sola vez)
        self.train_data: Optional[pd.DataFrame] = None
        self.eval_data: Optional[pd.DataFrame] = None
        self.train_scaler = None
        
        # Estudio de Optuna
        self.study_name = study_name or f"trading_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.storage = storage
        self.study: Optional[optuna.Study] = None
        
        # Resultados
        self.best_params: Dict[str, Any] = {}
        self.best_metrics: Dict[str, float] = {}
        
        log.info(f"Optimizador inicializado: {self.n_trials} trials, {self.timesteps_per_trial} timesteps/trial")
        log.info(f"Período de entrenamiento: {self.train_start} a {self.train_end}")
        log.info(f"Período de evaluación: {self.eval_start} a {self.eval_end}")
    
    def _load_data(self) -> None:
        """Carga los datos de entrenamiento y evaluación una sola vez."""
        log.info("Cargando datos de entrenamiento y evaluación...")
        
        try:
            # Cargar datos de entrenamiento
            log.info("Descargando datos de entrenamiento...")
            self.base_config.data_downloader.start_date = self.train_start
            self.base_config.data_downloader.end_date = self.train_end
            
            downloader_train = DataDownloader(self.client, self.base_config)
            train_raw = downloader_train.run()
            
            preprocesador_train = Preprocesamiento(self.base_config)
            self.train_data, self.train_scaler = preprocesador_train.run(train_raw)
            
            log.info(f"Datos de entrenamiento cargados: {len(self.train_data)} registros")
            
            # Cargar datos de evaluación
            log.info("Descargando datos de evaluación...")
            self.base_config.data_downloader.start_date = self.eval_start
            self.base_config.data_downloader.end_date = self.eval_end
            
            downloader_eval = DataDownloader(self.client, self.base_config)
            eval_raw = downloader_eval.run()
            
            preprocesador_eval = Preprocesamiento(self.base_config)
            # Usar train_scaler para consistencia
            self.eval_data, _ = preprocesador_eval.run(eval_raw)
            
            log.info(f"Datos de evaluación cargados: {len(self.eval_data)} registros")
            
            # Liberar memoria de datos raw
            del train_raw, eval_raw
            gc.collect()
            
        except Exception as e:
            log.error(f"Error al cargar datos: {e}")
            raise
    
    def _create_trial_config(self, trial: optuna.Trial) -> UnifiedConfig:
        """Crea una configuración modificada para un trial específico.
        
        Args:
            trial: Trial de Optuna
            
        Returns:
            UnifiedConfig modificada con parámetros sugeridos
        """
        # Copiar configuración base
        trial_config = copy.deepcopy(self.base_config)
        
        # Obtener parámetros sugeridos
        suggested_params = get_search_space(
            trial,
            optimize_sac=self.optimize_sac,
            optimize_env=self.optimize_env,
            optimize_network=self.optimize_network,
            optimize_portfolio=self.optimize_portfolio,
        )
        
        # Aplicar parámetros de SAC
        if 'SACmodel' in suggested_params:
            sac_params = suggested_params['SACmodel']
            
            trial_config.SACmodel.learning_rate = sac_params['learning_rate']
            trial_config.SACmodel.batch_size = sac_params['batch_size']
            trial_config.SACmodel.gamma = sac_params['gamma']
            trial_config.SACmodel.tau = sac_params['tau']
            trial_config.SACmodel.learning_starts = sac_params['learning_starts']
            trial_config.SACmodel.gradient_steps = sac_params['gradient_steps']
            trial_config.SACmodel.buffer_size = sac_params['buffer_size']
            
            # Entropy coefficient con target específico
            ent_target = sac_params['ent_coef_target']
            trial_config.SACmodel.ent_coef = f"auto_{ent_target}"
            
            # Silenciar output durante optimización
            trial_config.SACmodel.verbose = 0
        
        # Aplicar parámetros del entorno
        if 'entorno' in suggested_params:
            env_params = suggested_params['entorno']
            
            trial_config.entorno.window_size = env_params['window_size']
            trial_config.entorno.factor_aversion_riesgo = env_params['factor_aversion_riesgo']
            trial_config.entorno.max_drawdown_permitido = env_params['max_drawdown_permitido']
            trial_config.entorno.factor_escala_recompensa = env_params['factor_escala_recompensa']
            trial_config.entorno.peso_retorno_base = env_params['peso_retorno_base']
            trial_config.entorno.peso_temporal = env_params['peso_temporal']
            trial_config.entorno.peso_gestion = env_params['peso_gestion']
            trial_config.entorno.peso_drawdown = env_params['peso_drawdown']
            trial_config.entorno.umbral_perdida_pct = env_params['umbral_perdida_pct']
            trial_config.entorno.umbral_ganancia_pct = env_params['umbral_ganancia_pct']
            trial_config.entorno.penalizacion_no_operar = env_params['penalizacion_no_operar']
        
        # Aplicar arquitectura de red
        if 'network' in suggested_params:
            net_params = suggested_params['network']
            
            trial_config.policy_kwargs.net_arch.pi = net_params['pi_layers']
            trial_config.policy_kwargs.net_arch.qf = net_params['qf_layers']
            trial_config.policy_kwargs.log_std_init = net_params['log_std_init']
            trial_config.policy_kwargs.n_critics = net_params['n_critics']
        
        # Aplicar parámetros del portafolio
        if 'portafolio' in suggested_params:
            port_params = suggested_params['portafolio']
            trial_config.portafolio.apalancamiento = port_params['apalancamiento']
        
        # Ajustar timesteps para el trial
        trial_config.entorno.total_timesteps = self.timesteps_per_trial
        
        return trial_config
    
    def _objective(self, trial: optuna.Trial) -> float:
        """Función objetivo para Optuna (maximizar Sortino Ratio).
        
        Args:
            trial: Trial de Optuna
            
        Returns:
            Sortino Ratio (métrica a maximizar)
        """
        trial_num = trial.number
        log.info("=" * 80)
        log.info(f"INICIANDO TRIAL {trial_num + 1}/{self.n_trials}")
        log.info("=" * 80)
        
        try:
            # 1. Crear configuración para este trial
            trial_config = self._create_trial_config(trial)
            
            # 2. Crear portafolio
            portafolio = Portafolio(trial_config)
            
            # 3. Crear entorno de entrenamiento
            log.info("Creando entorno de entrenamiento...")
            train_env = TradingEnv(
                trial_config,
                self.train_data,
                portafolio,
                scaler=self.train_scaler
            )
            
            # 4. Crear y entrenar agente
            log.info(f"Entrenando agente con {self.timesteps_per_trial} timesteps...")
            agente = AgenteSac(trial_config, self.timesteps_per_trial)
            agente.CrearModelo(train_env)
            agente.train()
            
            # Liberar memoria del entrenamiento
            del train_env
            gc.collect()
            
            # 5. Evaluar en datos de evaluación
            log.info("Evaluando agente en datos de evaluación...")
            portafolio.reset()
            
            eval_env = TradingEnv(
                trial_config,
                self.eval_data,
                portafolio,
                scaler=self.train_scaler  # Usar train_scaler
            )
            
            max_steps = len(self.eval_data) - trial_config.entorno.window_size
            
            # Evaluar y obtener DataFrames
            eval_results = agente.EvaluarEnv(
                env=eval_env,
                n_episodes=self.n_eval_episodes,
                max_steps_per_episode=max_steps,
                save_dir=None  # No guardar CSVs durante optimización
            )
            
            # 6. Calcular métricas
            df_portafolio = eval_results['portafolio']
            df_operacion = eval_results.get('operacion', None)  # Extraer historial de operaciones
            
            if len(df_portafolio) == 0:
                log.warning("No se generaron datos de evaluación")
                return -999.0  # Penalizar fuertemente
            
            # Extraer curva de equity
            equity_curve = df_portafolio['equity'].values
            initial_equity = trial_config.portafolio.capital_inicial
            
            # Calcular todas las métricas
            metrics = calculate_metrics(
                equity_curve=equity_curve,
                initial_equity=initial_equity,
                trades_df=df_operacion,  # ✅ FIX: Pasar historial de operaciones
                risk_free_rate=0.0,
                periods_per_year=8760  # Para 1h candles
            )
            
            sortino = metrics['sortino_ratio']
            
            # Log métricas del trial
            log_metrics(metrics, prefix=f"  [Trial {trial_num}] ")
            
            # Guardar métricas adicionales en el trial
            trial.set_user_attr('sharpe_ratio', metrics['sharpe_ratio'])
            trial.set_user_attr('total_return', metrics['total_return'])
            trial.set_user_attr('max_drawdown', metrics['max_drawdown'])
            trial.set_user_attr('final_equity', metrics['final_equity'])
            trial.set_user_attr('win_rate', metrics['win_rate'])
            trial.set_user_attr('profit_factor', metrics['profit_factor'])
            trial.set_user_attr('num_trades', metrics['num_trades'])
            
            # Liberar memoria
            del eval_env, agente, portafolio, df_portafolio, df_operacion
            gc.collect()
            
            log.info(f"Trial {trial_num} completado. Sortino Ratio: {sortino:.3f}")
            
            return sortino
            
        except Exception as e:
            log.error(f"Error en trial {trial_num}: {e}")
            log.error("Detalles:", exc_info=True)
            
            # Liberar memoria en caso de error
            gc.collect()
            
            # Retornar valor muy bajo (no fallar el estudio completo)
            return -999.0
    
    def optimize(self) -> optuna.Study:
        """Ejecuta la optimización de hiperparámetros.
        
        Returns:
            Estudio de Optuna con resultados
        """
        log.info("=" * 80)
        log.info("INICIANDO OPTIMIZACIÓN DE HIPERPARÁMETROS")
        log.info("=" * 80)
        
        try:
            # 1. Cargar datos una sola vez
            if self.train_data is None or self.eval_data is None:
                self._load_data()
            
            # 2. Crear estudio de Optuna
            log.info(f"Creando estudio de Optuna: {self.study_name}")
            
            # Sampler: TPE (Tree-structured Parzen Estimator) - búsqueda bayesiana
            sampler = TPESampler(seed=42, n_startup_trials=10)
            
            # Pruner: MedianPruner - detiene trials poco prometedores
            pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=1000)
            
            self.study = optuna.create_study(
                study_name=self.study_name,
                direction='maximize',  # Maximizar Sortino Ratio
                sampler=sampler,
                pruner=pruner,
                storage=self.storage,
                load_if_exists=True,  # Continuar estudio si existe
            )
            
            # 3. Ejecutar optimización
            log.info(f"Iniciando {self.n_trials} trials de optimización...")
            log.info("Métrica objetivo: Sortino Ratio (mayor es mejor)")
            
            self.study.optimize(
                self._objective,
                n_trials=self.n_trials,
                show_progress_bar=True,
                gc_after_trial=True,  # Liberar memoria después de cada trial
            )
            
            # 4. Extraer mejores resultados
            log.info("=" * 80)
            log.info("OPTIMIZACIÓN COMPLETADA")
            log.info("=" * 80)
            
            self.best_params = self.study.best_params
            self.best_metrics = {
                'sortino_ratio': self.study.best_value,
                'sharpe_ratio': self.study.best_trial.user_attrs.get('sharpe_ratio', 0.0),
                'total_return': self.study.best_trial.user_attrs.get('total_return', 0.0),
                'max_drawdown': self.study.best_trial.user_attrs.get('max_drawdown', 0.0),
                'final_equity': self.study.best_trial.user_attrs.get('final_equity', 0.0),
            }
            
            log.info(f"Mejor trial: {self.study.best_trial.number}")
            log.info(f"Mejor Sortino Ratio: {self.study.best_value:.3f}")
            log_metrics(self.best_metrics, prefix="  [BEST] ")
            
            return self.study
            
        except KeyboardInterrupt:
            log.warning("Optimización interrumpida por el usuario")
            if self.study is not None:
                log.info("Guardando resultados parciales...")
                return self.study
            raise
            
        except Exception as e:
            log.error(f"Error durante la optimización: {e}")
            log.error("Detalles:", exc_info=True)
            raise
    
    def save_results(self, output_path: str) -> None:
        """Guarda los mejores parámetros y resultados en un archivo YAML.
        
        Args:
            output_path: Ruta del archivo YAML de salida
        """
        log.info(f"Guardando resultados de optimización en: {output_path}")
        
        try:
            if self.study is None:
                raise RuntimeError("No hay estudio para guardar. Ejecute optimize() primero.")
            
            # Preparar estructura completa
            results = {
                'optimization_metadata': {
                    'study_name': self.study_name,
                    'n_trials': len(self.study.trials),
                    'best_trial': self.study.best_trial.number,
                    'optimization_date': datetime.now().isoformat(),
                    'train_period': f"{self.train_start} to {self.train_end}",
                    'eval_period': f"{self.eval_start} to {self.eval_end}",
                    'timesteps_per_trial': self.timesteps_per_trial,
                },
                'best_metrics': self.best_metrics,
                'best_params': self.best_params,
                'all_trials_summary': {
                    'total': len(self.study.trials),
                    'completed': len([t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
                    'pruned': len([t for t in self.study.trials if t.state == optuna.trial.TrialState.PRUNED]),
                    'failed': len([t for t in self.study.trials if t.state == optuna.trial.TrialState.FAIL]),
                },
            }
            
            # Guardar en YAML
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(results, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
            
            log.info(f"✅ Resultados guardados exitosamente en: {output_path}")
            
            # También guardar estudio completo (opcional, para análisis detallado)
            study_pickle_path = output_path.replace('.yaml', '_study.pkl')
            import joblib
            joblib.dump(self.study, study_pickle_path)
            log.info(f"✅ Estudio completo guardado en: {study_pickle_path}")
            
        except Exception as e:
            log.error(f"Error al guardar resultados: {e}")
            raise
    
    def generate_visualizations(self, output_dir: str) -> None:
        """Genera visualizaciones del proceso de optimización.
        
        Args:
            output_dir: Directorio donde guardar las visualizaciones
        """
        log.info(f"Generando visualizaciones en: {output_dir}")
        
        try:
            if self.study is None:
                raise RuntimeError("No hay estudio para visualizar. Ejecute optimize() primero.")
            
            os.makedirs(output_dir, exist_ok=True)
            
            from optuna.visualization import (
                plot_optimization_history,
                plot_param_importances,
                plot_slice,
                plot_parallel_coordinate,
            )
            
            # 1. Historia de optimización
            fig = plot_optimization_history(self.study)
            fig.write_html(os.path.join(output_dir, 'optimization_history.html'))
            log.info("✅ Gráfico de historia de optimización guardado")
            
            # 2. Importancia de parámetros
            fig = plot_param_importances(self.study)
            fig.write_html(os.path.join(output_dir, 'param_importances.html'))
            log.info("✅ Gráfico de importancia de parámetros guardado")
            
            # 3. Slice plot (efecto individual de cada parámetro)
            fig = plot_slice(self.study)
            fig.write_html(os.path.join(output_dir, 'slice_plot.html'))
            log.info("✅ Slice plot guardado")
            
            # 4. Coordenadas paralelas
            fig = plot_parallel_coordinate(self.study)
            fig.write_html(os.path.join(output_dir, 'parallel_coordinate.html'))
            log.info("✅ Gráfico de coordenadas paralelas guardado")
            
            log.info(f"✅ Todas las visualizaciones guardadas en: {output_dir}")
            
        except ImportError:
            log.warning("No se puede generar visualizaciones. Instale: pip install plotly kaleido")
        except Exception as e:
            log.error(f"Error al generar visualizaciones: {e}")
            log.error("Detalles:", exc_info=True)
