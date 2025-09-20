""" Agente de aprendizaje por refuerzo. """
import os
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
import torch as th
from src.Entrenamiento.config import Config

class AgenteSac:
    """ Agente de aprendizaje por refuerzo. """
    def __init__(self, config: Config, total_timesteps: int):
        """ Inicializa los parámetros del agente SAC. """
        self.model = None
        self.vec_env = None  # Entorno vectorizado + normalizado
        self.config = config

        self.model_path = config.Output.model_path
        self.vecnorm_path = config.Output.vecnorm_path
        self.tensorboard_log = config.Output.tensorboard_log

        self.total_timesteps = total_timesteps

    def CrearModelo(self, env: gym.Env):
        """ Crea el modelo del agente SAC con normalización de observaciones y recompensas. """

        # 1) Vectorizar el entorno
        venv = DummyVecEnv([lambda: env])

        # 2) Normalizar observaciones y recompensas
        #    Nota: gamma aquí debe coincidir con el gamma del algoritmo para la normalización de retornos.
        vec_config = self.config.Vecnormalize
        self.vec_env = VecNormalize(
            venv,
            norm_obs=vec_config.norm_obs,
            norm_reward=vec_config.norm_reward,
            clip_obs=vec_config.clip_obs,
            gamma=vec_config.gamma,
        )

        # Extraer configuración de policy_kwargs
        policy_config = self.config.policy_kwargs
        policy_kwargs = dict(
            net_arch=dict(
                pi=policy_config.net_arch.pi,
                qf=policy_config.net_arch.qf,
            ),
            activation_fn=th.nn.ReLU,  # Función de activación de las capas ocultas.
            log_std_init=policy_config.log_std_init,
            n_critics=policy_config.n_critics,
        )

        # Parámetros clave para el ajuste del modelo SAC.
        # Los parámetros con valores por defecto que no se suelen modificar han sido omitidos por claridad.
        sac_config = self.config.SACmodel
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

    def train(self):
        """ Entrena el agente SAC. """
        self.model.learn(total_timesteps=self.total_timesteps) #type: ignore

    def GuardarModelo(self):
        """ Guarda el modelo y las estadísticas de normalización. """
        # Crear rutas si no existen:
        base_dir= self.config.Output.base_dir

        os.makedirs(f"{base_dir}/modelos", exist_ok=True)
        os.makedirs(f"{base_dir}/tensorboard", exist_ok=True)

        if self.model is not None:
            self.model.save(self.model_path)
        if isinstance(self.vec_env, VecNormalize):
            self.vec_env.save(self.vecnorm_path)
