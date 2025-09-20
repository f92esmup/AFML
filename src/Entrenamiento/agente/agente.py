""" Agente de aprendizaje por refuerzo. """
import os
import logging
from typing import Optional, TYPE_CHECKING
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
import torch as th

if TYPE_CHECKING:
    from src.Entrenamiento.config import Config

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.agente")

class AgenteSac:
    """ Agente de aprendizaje por refuerzo. """
    def __init__(self, config: 'Config', total_timesteps: int) -> None:
        """ Inicializa los parámetros del agente SAC. """
        log.info("Inicializando agente SAC...")
        
        try:
            self.model: Optional[SAC] = None
            self.vec_env: Optional[VecNormalize] = None
            self.config: 'Config' = config
            
            # Validar parámetros de entrada
            if total_timesteps <= 0:
                raise ValueError(f"total_timesteps debe ser mayor que 0, recibido: {total_timesteps}")
            
            self.model_path: str = config.Output.model_path
            self.vecnorm_path: str = config.Output.vecnorm_path
            self.tensorboard_log: str = config.Output.tensorboard_log
            self.total_timesteps: int = total_timesteps
            
            log.info(f"Agente SAC inicializado correctamente con {total_timesteps} timesteps totales")
            log.debug(f"Ruta del modelo: {self.model_path}")
            log.debug(f"Ruta de normalización: {self.vecnorm_path}")
            log.debug(f"Ruta de tensorboard: {self.tensorboard_log}")
            
        except Exception as e:
            log.error(f"Error durante la inicialización del agente SAC: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def CrearModelo(self, env: gym.Env) -> None:
        """ Crea el modelo del agente SAC con normalización de observaciones y recompensas. """
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
            
            # 1) Vectorizar el entorno
            log.debug("Vectorizando entorno...")
            venv: DummyVecEnv = DummyVecEnv([lambda: env])
            log.debug("Entorno vectorizado exitosamente.")

            # 2) Normalizar observaciones y recompensas
            log.debug("Configurando normalización de entorno...")
            vec_config = self.config.Vecnormalize
            self.vec_env = VecNormalize(
                venv,
                norm_obs=vec_config.norm_obs,
                norm_reward=vec_config.norm_reward,
                clip_obs=vec_config.clip_obs,
                gamma=vec_config.gamma,
            )
            log.info("Entorno normalizado configurado exitosamente.")
            log.debug(f"Configuración de normalización: norm_obs={vec_config.norm_obs}, "
                     f"norm_reward={vec_config.norm_reward}, gamma={vec_config.gamma}")

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
                env=self.vec_env,
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
            )
            
            log.info("Modelo SAC creado exitosamente.")
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
            
            # Guardar estadísticas de normalización
            if isinstance(self.vec_env, VecNormalize):
                log.debug(f"Guardando estadísticas de normalización en: {self.vecnorm_path}")
                self.vec_env.save(self.vecnorm_path)
                log.info(f"Estadísticas de normalización guardadas en: {self.vecnorm_path}")
            else:
                log.warning("No se encontró VecNormalize para guardar estadísticas de normalización")
            
            log.info("Modelo y estadísticas guardados exitosamente.")
            
        except RuntimeError as e:
            log.error(f"Error de estado al guardar el modelo: {e}")
            raise
        except OSError as e:
            log.error(f"Error de sistema al crear directorios o guardar archivos: {e}")
            log.error(f"Verifique permisos de escritura en: {self.config.Output.base_dir}")
            raise
        except Exception as e:
            log.error(f"Error inesperado al guardar el modelo: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise
