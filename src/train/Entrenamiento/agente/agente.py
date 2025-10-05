""" Agente de aprendizaje por refuerzo. """
import os
import logging
from typing import Optional, TYPE_CHECKING
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv
import torch as th
import pandas as pd
import json
from typing import List, Dict, Any, cast
import numpy as np

if TYPE_CHECKING:
    from src.train.config.config import UnifiedConfig

from src.utils.device import get_device

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.agente")

class AgenteSac:
    """ Agente de aprendizaje por refuerzo. """
    def __init__(self, config: 'UnifiedConfig', total_timesteps: int) -> None:
        """ Inicializa los parámetros del agente SAC. """
        log.info("Inicializando agente SAC...")
        
        try:
            self.model: Optional[SAC] = None
            self.config: 'UnifiedConfig' = config
            
            # Validar parámetros de entrada
            if total_timesteps <= 0:
                raise ValueError(f"total_timesteps debe ser mayor que 0, recibido: {total_timesteps}")
            
            self.model_path: str = config.Output.model_path
            self.tensorboard_log: str = config.Output.tensorboard_log
            self.total_timesteps: int = total_timesteps
            
            # Detectar dispositivo óptimo (GPU si está disponible, CPU como fallback)
            self.device: str = get_device()
            
            log.info(f"Agente SAC inicializado correctamente con {total_timesteps} timesteps totales")
            log.info(f"Dispositivo seleccionado para entrenamiento: {self.device.upper()}")
            log.debug(f"Ruta del modelo: {self.model_path}")
            log.debug(f"Ruta de tensorboard: {self.tensorboard_log}")
            
        except Exception as e:
            log.error(f"Error durante la inicialización del agente SAC: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def CrearModelo(self, env: gym.Env) -> None:
        """ Crea el modelo del agente SAC con vectorización simple. """
        log.info("Creando modelo SAC...")
        
        try:
            # Validar el entorno
            if env is None:
                raise ValueError("El entorno no puede ser None")
            
            log.debug("Validando espacio de observaciones y acciones del entorno...")
            if not hasattr(env, 'observation_space') or not hasattr(env, 'action_space'):
                raise ValueError("El entorno debe tener observation_space y action_space definidos")
            
            log.debug(f"Espacio de observaciones: {env.observation_space}")
            log.debug(f"Espacio de acciones: {env.action_space}")
            
            # 1) Vectorizar el entorno (mantenemos DummyVecEnv para compatibilidad con SB3)
            log.debug("Vectorizando entorno...")
            venv: DummyVecEnv = DummyVecEnv([lambda: env])
            log.debug("Entorno vectorizado exitosamente.")

            # Extraer configuración de policy_kwargs
            log.debug("Configurando arquitectura de la política...")
            policy_config = self.config.policy_kwargs
            policy_kwargs: dict = dict(
                net_arch=dict(
                    pi=policy_config.net_arch.pi,
                    qf=policy_config.net_arch.qf,
                ),
                activation_fn=th.nn.ReLU,
                log_std_init=policy_config.log_std_init,
                n_critics=policy_config.n_critics,
            )
            log.debug(f"Arquitectura de red configurada: {policy_kwargs}")

            # Parámetros clave para el ajuste del modelo SAC
            log.debug("Configurando parámetros del modelo SAC...")
            sac_config = self.config.SACmodel
            
            # Validar parámetros críticos
            if sac_config.buffer_size <= 0:
                raise ValueError(f"buffer_size debe ser mayor que 0, recibido: {sac_config.buffer_size}")
            if sac_config.batch_size <= 0:
                raise ValueError(f"batch_size debe ser mayor que 0, recibido: {sac_config.batch_size}")
            if sac_config.learning_rate <= 0:
                raise ValueError(f"learning_rate debe ser mayor que 0, recibido: {sac_config.learning_rate}")
            
            self.model = SAC(
                policy=sac_config.policy,
                env=venv,  # Usar DummyVecEnv directamente (sin normalización)
                # --- Hiperparámetros principales de optimización ---
                learning_rate=sac_config.learning_rate,
                buffer_size=sac_config.buffer_size,
                learning_starts=sac_config.learning_starts,
                batch_size=sac_config.batch_size,
                tau=sac_config.tau,
                gamma=sac_config.gamma,
                ent_coef=sac_config.ent_coef,
                # --- Frecuencia de entrenamiento ---
                train_freq=sac_config.train_freq,
                gradient_steps=sac_config.gradient_steps,
                # --- Configuración de la red y logging ---
                policy_kwargs=policy_kwargs,
                tensorboard_log=self.tensorboard_log,
                # --- Reproducibilidad y monitorización ---
                verbose=sac_config.verbose,
                seed=sac_config.seed,
                # --- Dispositivo (GPU/CPU) ---
                device=self.device,
            )
            
            log.info("Modelo SAC creado exitosamente.")
            log.info(f"✅ Modelo configurado para entrenar en: {self.device.upper()}")
            log.debug(f"Configuración del modelo: learning_rate={sac_config.learning_rate}, "
                     f"buffer_size={sac_config.buffer_size}, batch_size={sac_config.batch_size}")
            
        except ValueError as e:
            log.error(f"Error de validación al crear el modelo SAC: {e}")
            raise
        except Exception as e:
            log.error(f"Error inesperado al crear el modelo SAC: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def train(self) -> None:
        """ Entrena el agente SAC. """
        log.info(f"Iniciando entrenamiento del agente SAC por {self.total_timesteps} timesteps...")
        
        try:
            if self.model is None:
                raise RuntimeError("El modelo no ha sido creado. Ejecute CrearModelo() primero.")
            
            log.info("Comenzando proceso de aprendizaje...")
            self.model.learn(total_timesteps=self.total_timesteps)
            log.info("Entrenamiento del agente completado exitosamente.")
            
        except RuntimeError as e:
            log.error(f"Error de estado durante el entrenamiento: {e}")
            raise
        except KeyboardInterrupt:
            log.warning("Entrenamiento interrumpido por el usuario")
            raise
        except Exception as e:
            log.error(f"Error durante el entrenamiento del agente: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def GuardarModelo(self) -> None:
        """ Guarda el modelo y las estadísticas de normalización. """
        log.info("Guardando modelo y estadísticas de normalización...")
        
        try:
            if self.model is None:
                raise RuntimeError("No hay modelo para guardar. Ejecute CrearModelo() y train() primero.")
            
            # Crear rutas si no existen
            base_dir: str = self.config.Output.base_dir
            log.debug(f"Directorio base para guardar: {base_dir}")
            
            modelos_dir: str = f"{base_dir}/modelos"
            tensorboard_dir: str = f"{base_dir}/tensorboard"
            
            log.debug("Creando directorios necesarios...")
            os.makedirs(modelos_dir, exist_ok=True)
            os.makedirs(tensorboard_dir, exist_ok=True)
            log.debug(f"Directorios creados: {modelos_dir}, {tensorboard_dir}")

            # Guardar modelo
            log.debug(f"Guardando modelo en: {self.model_path}")
            self.model.save(self.model_path)
            log.info(f"Modelo guardado exitosamente en: {self.model_path}")
            
            log.info("Modelo guardado exitosamente.")
            
        except RuntimeError as e:
            log.error(f"Error de estado al guardar el modelo: {e}")
            raise

    def EvaluarEnv(self, env: gym.Env, n_episodes: int = 1, max_steps_per_episode: int | None = None,
                   save_dir: str | None = None) -> Dict[str, pd.DataFrame]:
        """Evalúa el `env` usando el modelo entrenado.

        Genera tres CSVs separados con el historial de `entorno`, `portafolio` y `operacion`.

        Retorna un dict con tres pandas.DataFrame: {'entorno': df_entorno, 'portafolio': df_portafolio, 'operacion': df_operacion}
        """

        log.info("Iniciando evaluación del entorno...")

        try:
            if env is None:
                raise ValueError("El entorno de evaluación no puede ser None")

            # Preparar directorio de salida
            base_dir = save_dir or getattr(self.config.Output, 'base_dir', '.')
            eval_dir = os.path.join(base_dir, 'evaluacion')
            os.makedirs(eval_dir, exist_ok=True)

            # 1) Vectorizar el env (mantenemos DummyVecEnv para compatibilidad)
            venv = DummyVecEnv([lambda: env])

            # 2) Asegurar que el modelo esté cargado y vinculado al entorno vectorizado
            if self.model is None:
                if os.path.isfile(self.model_path):
                    log.info(f"Cargando modelo desde: {self.model_path}")
                    # Cargar modelo vinculado al entorno vectorizado
                    self.model = SAC.load(self.model_path, env=venv)
                else:
                    raise RuntimeError("No hay modelo en memoria y no se encontró archivo en model_path")
            else:
                # Si el modelo ya existe en memoria (por ejemplo, tras entrenamiento en la misma sesión),
                # debemos asegurarnos de que utilice el entorno de evaluación. Usar set_env evita
                # re-cargar el modelo desde disco pero lo vincula al nuevo entorno.
                try:
                    self.model.set_env(venv)
                    log.debug("Modelo existente vinculado al entorno de evaluación mediante set_env().")
                except Exception as e:
                    log.warning(f"No se pudo set_env() en el modelo existente: {e}. Se recargará el modelo desde disco.")
                    if os.path.isfile(self.model_path):
                        self.model = SAC.load(self.model_path, env=venv)
                    else:
                        raise

            # 3) Ejecutar episodios
            entorno_rows: List[Dict[str, Any]] = []
            portafolio_rows: List[Dict[str, Any]] = []
            operacion_rows: List[Dict[str, Any]] = []

            obs = venv.reset()

            for ep in range(n_episodes):
                steps = 0
                done = False
                terminated = False
                truncated = False


                while True:
                    # cast obs to ndarray for the type checker; at runtime venv provides ndarray or dict
                    obs_input = cast(np.ndarray, obs)
                    action, _states = self.model.predict(obs_input, deterministic=True)
                    # VecEnv.step returns (obs, rewards, dones, infos)
                    obs, rewards, dones, infos = venv.step(action)

                    # extraer primer elemento del batch
                    info = infos[0] if isinstance(infos, (list, tuple, np.ndarray)) else infos
                    reward = rewards[0] if isinstance(rewards, (list, tuple, np.ndarray)) else rewards
                    done = bool(dones[0]) if isinstance(dones, (list, tuple, np.ndarray)) else bool(dones)

                    # Aplanar las tres secciones (si están presentes en el info)
                    entorno_section = info.get('entorno', {}) if isinstance(info, dict) else {}
                    portafolio_section = info.get('portafolio', {}) if isinstance(info, dict) else {}
                    operacion_section = info.get('operacion', {}) if isinstance(info, dict) else {}

                    # Añadir metadatos comunes
                    meta = {
                        'episodio': entorno_section.get('episodio', ep),
                        'paso': entorno_section.get('paso', steps),
                    }

                    # Merge meta into each section with prefixed keys
                    entorno_row = {**meta}
                    entorno_row.update({f"{k}": v for k, v in entorno_section.items()})
                    portafolio_row = {**meta}
                    portafolio_row.update({f"{k}": v for k, v in portafolio_section.items()})
                    operacion_row = {**meta}
                    operacion_row.update({f"{k}": v for k, v in operacion_section.items()})

                    entorno_rows.append(entorno_row)
                    portafolio_rows.append(portafolio_row)
                    operacion_rows.append(operacion_row)

                    steps += 1

                    # Preferir flags explícitas del info (TradingEnv provee terminated/truncated)
                    terminated = bool(entorno_section.get('terminated', False))
                    truncated = bool(entorno_section.get('truncated', False))

                    # Check termination conditions
                    if terminated or truncated or done or (max_steps_per_episode is not None and steps >= max_steps_per_episode):
                        # Reset for next episode unless it's the last
                        if ep < n_episodes - 1:
                            obs = venv.reset()
                        break

                log.info(f"Episodio {ep+1}/{n_episodes} finalizado con {steps} pasos")

            # 5) Convertir a DataFrame y guardar 3 CSVs separados
            df_entorno = pd.DataFrame(entorno_rows)
            df_portafolio = pd.DataFrame(portafolio_rows)
            df_operacion = pd.DataFrame(operacion_rows)

            entorno_csv = os.path.join(eval_dir, 'entorno.csv')
            portafolio_csv = os.path.join(eval_dir, 'portafolio.csv')
            operacion_csv = os.path.join(eval_dir, 'operacion.csv')

            df_entorno.to_csv(entorno_csv, index=False)
            df_portafolio.to_csv(portafolio_csv, index=False)
            df_operacion.to_csv(operacion_csv, index=False)

            log.info(f"CSV de evaluación guardados en: {eval_dir}")

            return {'entorno': df_entorno, 'portafolio': df_portafolio, 'operacion': df_operacion}

        except Exception as e:
            log.error(f"Error durante la evaluación: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise
