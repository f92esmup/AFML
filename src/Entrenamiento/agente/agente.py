""" Agente de aprendizaje por refuerzo. """
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.noise import NormalActionNoise
import torch as th
from src.Entrenamiento.config import Config

class AgenteSac:
    """ Agente de aprendizaje por refuerzo. """
    def __init__(self, config: Config):
        """ Inicializa los parámetros del agente SAC. """
        self.model = None
        # Configuración SAC:

    def CrearModelo(self, env: gym.Env, ):
        """ Crea el modelo del agente SAC. """

        policy_kwargs = dict(
            net_arch=dict(
                pi=[256, 256],  # Capas de la red de la política (pi): tamaño de cada capa oculta.
                qf=[256, 256],  # Capas de las redes Q (qf): arquitectura para cada crítico.
            ),
            activation_fn=th.nn.ReLU,  # Función de activación de las capas ocultas.
            log_std_init=-3.0,         # Valor inicial de log(σ) para la política Gaussiana.
            ortho_init=False,          # Inicialización ortogonal de pesos (False evita valores grandes iniciales).
            n_critics=2,               # Número de críticos Q independientes (promedia para mayor estabilidad).
        )

        self.model = SAC(
            policy="MlpPolicy",                    # Tipo de política (MLP para observaciones vectoriales).
            env=env,                               # Entorno Gym/Gymnasium.
            learning_rate=3e-4,                    # Tasa de aprendizaje del optimizador (Adam).
            buffer_size=1_000_000,                 # Tamaño del replay buffer (número de transiciones almacenadas).
            learning_starts=5_000,                 # Pasos de calentamiento antes de empezar a entrenar.
            batch_size=256,                        # Tamaño del lote muestreado del buffer en cada actualización.
            tau=0.005,                             # Coeficiente de actualización suave (Polyak) de redes objetivo.
            gamma=0.99,                            # Factor de descuento para recompensas futuras.
            train_freq=(1, "step"),                # Frecuencia de entrenamiento: cada 1 paso de entorno.
            gradient_steps=1,                      # Número de pasos de gradiente por llamada de entrenamiento.
            action_noise=None,                     # Ruido de acción (no aplica a SAC; se ignora).
            replay_buffer_class=None,              # Clase custom de replay buffer (None usa la predeterminada).
            replay_buffer_kwargs=dict(
                handle_timeout_termination=True    # Trata timeouts como terminaciones truncadas al almacenar.
            ),
            optimize_memory_usage=False,           # Ahorro de memoria en el buffer (puede ralentizar entrenamiento).
            ent_coef="auto_0.1",                   # Coef. de entropía: "auto" con valor inicial 0.1 (auto-tuning de α).
            target_update_interval=1,              # Intervalo de actualización de la red objetivo (en pasos).
            target_entropy="auto",                 # Entropía objetivo para la política (auto calcula heurística).
            use_sde=False,                         # Exploración SDE dependiente del estado (no suele usarse en SAC).
            sde_sample_freq=-1,                    # Frecuencia de re-muestreo de SDE (-1: solo al reset).
            use_sde_at_warmup=False,               # Usar SDE durante el calentamiento (si SDE está activo).
            stats_window_size=100,                 # Ventana para medias/métricas de logging.
            tensorboard_log="./tb",                # Carpeta de logs para TensorBoard.
            policy_kwargs=policy_kwargs,           # Argumentos de construcción de la política.
            verbose=1,                             # Nivel de verbosidad (0: silencioso, 1: info, 2: debug).
            seed=42,                               # Semilla para reproducibilidad.
            device="auto",                         # Dispositivo de cómputo ("cpu", "cuda", o auto-detección).
        )
    def train(self):
        """ Entrena el agente SAC. """
        self.model.learn(totlal_timesteps=self.total_timesteps)
    def GuardarModelo(self):
        """ Guarda el modelo entrenado. """
    def evaluate(self):
        """ Evalúa el modelo entrenado. """