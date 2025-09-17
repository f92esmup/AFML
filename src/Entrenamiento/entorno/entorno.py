""" Entorno de entrenamiento para agentes de trading reinforcement learning"""
import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from typing import Tuple

from src.Entrenamiento.config import Config
from src.Entrenamiento.entorno.portafolio import Portafolio

class TradingEnv(gym.Env):

    def __init__(self, config: Config, data: pd.DataFrame, scaler: StandardScaler, portafolio: Portafolio):
        super().__init__()
        self.data = data

        self.window_size = config.entorno.window_size

        self._construir_espacios()

        self.paso_actual = self.window_size - 1 # Porque en python los índices empiezan en 0
        self.episodio = 0 # El episodio del entrenamiento
        
        self.scaler = scaler # Aquí se podría poner un scaler si se quiere normalizar los datos.

        self.portafolio = portafolio
        
        self.max_drawdown_permitido = config.entorno.max_drawdown_permitido
        self.factor_aversion_riesgo = config.entorno.factor_aversion_riesgo
        self.umbral_manterner_posicion = config.entorno.umbral_manter_posicion

        # Parámetros de control para aplicar la recompensa
        # 
    def _construir_espacios(self):
        """Construye los espacios de observación y acción."""
        # EL espacio de observación será una matriz con los datos de las últimas N velas
        # y el estado ACTUAL del portafolio (PnL no realizado, posición abierta) 
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.window_size, self.data.shape[1] + 2), # Shape devuelve el (nº filas, nº columnas).
            dtype=np.float32
        )

        # EL espacio de acción será un valor continuo entre -1 y 1
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(1,), 
            dtype=np.float32
        )

    def reset(self, *, seed=None, options=None):
        """ Reinicia el entorno para un nuevo episodio de entrenamiento."""
        super().reset(seed=seed)
        self.paso_actual = self.window_size - 1
        self.episodio += 1
        self.portafolio.reset()

        precio_inicial = self.data.iloc[self.paso_actual]['close']
        equity_inicial = self.portafolio.get_equity(precio_inicial)

        observacion = self._get_observation(equity_inicial)
        
        info = {'status': 'Entorno reiniciado'}
        return observacion, info

    

    def step(self, action: np.ndarray) -> Tuple:
        """ Ejecución de un paso en el entorno.
        Para conocer el efecto de una acción, necesitamos conocer el instante actual t y el siguiente t+1.
        """


        precio_actual = self.data.iloc[self.paso_actual]['close']

        # 1. Ejecutar la acción del instante t:
        self._ejecutar_action(action[0], precio_actual)

        # Avanzamos en el tiempo t --> t + 1
        self.paso_actual += 1
        
        # Comprobamos si se han termiando los datos:
        truncated = self.paso_actual >= len(self.data) -1

        if truncated:
            observacion = np.zeros(self.observation_space.shape, dtype=np.float32)
            recompensa = 0
            terminated = False # No es un fallo, solo se acabaron los datos.
            info = {'status': 'Fin de los datos'}

            return observacion, recompensa, terminated, truncated, info
        
        # Obtenemos el estado el instante t + 1 
        precio_siguiente = self.data.iloc[self.paso_actual]['close']
        equity_siguiente = self.portafolio.get_equity(precio_siguiente)

        # Calculamos la recompensa:
        recompensa = self._recompensa(precio_siguiente, equity_siguiente)

        # Obtenemos la nueva observacion
        observacion = self._get_observation(equity_siguiente)

        # Comprobar si se interrumpe el entrenamiento:
        terminated = self.portafolio.calcular_max_drawdown(precio_siguiente, self.episodio) >= self.max_drawdown_permitido

        # Creamos la información
        info = {
            'recompensa': recompensa,
            'paso': self.paso_actual,
            'action': action[0]
        }

        return observacion, recompensa, terminated, truncated, info

    def _get_observation(self, equity: float) -> np.ndarray:
        """ Construye y NORMALIZA la observación actual. """

        # 1. Separar la ventana de datos del mercado
        start = self.paso_actual + 1 - self.window_size
        end = self.paso_actual + 1
        ventana_datos = self.data.iloc[start:end].values
        
        # 2. Normalizar los datos del mercado usando el scaler pre-ajustado
        #ventana_datos_normalizados = self.scaler.transform(ventana_datos)
        # Usanmos Vecnormalizer para normalizar la observación
        
        # 3. Calcular el PnL no realizado
        precio_actual = self.data.iloc[self.paso_actual]['close']
        pnl_no_realizado = self.portafolio.calcular_PnL_no_realizado(precio_actual)
        
        # 4. NORMALIZAR EL PNL: Dividirlo por una base dinámica (el equitiy actual)
        # Esto convierte el PnL absoluto en un PnL relativo al equity en ese momento.
        pnl_normalizado = pnl_no_realizado / equity

        # 5. Obtener la posición abierta (ya está en un rango pequeño: -1, 0, 1)
        # Es buena práctica asegurarse de que sea un float para consistencia.
        posicion_abierta = 0.0
        if self.portafolio.posicion_abierta is not None:
            posicion_abierta = float(self.portafolio.posicion_abierta.tipo)

        # 6. Crear la información del portafolio con el PnL YA NORMALIZADO
        portafolio_info = np.array([[pnl_normalizado, posicion_abierta]] * self.window_size)

        # 7. Combinar los datos normalizados del mercado con los del portafolio
        observacion = np.hstack((ventana_datos_normalizados, portafolio_info))
        
        # 8. Devolver el array final, asegurando que el tipo de dato es float32
        return observacion.astype(np.float32)
    
    def _recompensa(self, precio: float, equity: float) -> float:
        """ Calcula la recompensa y la normaliza."""
        pnl = self.portafolio.calcular_PnL_no_realizado(precio)

        if pnl < 0:
            # Penalización por pérdidas
            recompensa = pnl * self.factor_aversion_riesgo
        else:
            # Recompensa por ganancias
            recompensa = pnl
        
        recompensa_normalizada = recompensa / equity
        return recompensa_normalizada

    def _ejecutar_action(self, action: float, precio: float) -> bool:
        """ Ejecuta la acción en el portafolio. """
        # La acción es un valor continuo entre -1 y 1
        # -1: Vender todo (posición corta máxima)
        # 0: Mantener la posición actual (no hacer nada)
        # 1: Comprar todo (posición larga máxima)

        #  La primera capa de if determina el tipo de posicion a tomar
        # La segunda capa de if determina si se abre una nueva posición o se cierra la actual
        resultado = False
        if action > self.umbral_manterner_posicion:
            tipo_posicion = 'long'

            if self.portafolio.posicion_abierta is None:
                """ No hay posición abierta, abrir una nueva posición larga """
                resultado = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)
            elif self.portafolio.posicion_abierta.tipo == -1:
                """ Hay una posición corta abierta, cerrarla """
                resultado, _ = self.portafolio.cerrar_posicion(precio_cierre=precio, episodio=self.episodio)

                # Abrir una nueva posición larga
                resultado = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)

            elif self.portafolio.posicion_abierta.tipo == 1:
                """ Ya hay una posición larga abierta, reducir o aumentar la posición """
                resultado = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=action, episodio=self.episodio)
        elif action < -self.umbral_manterner_posicion:
            tipo_posicion = 'short'

            if self.portafolio.posicion_abierta is None:
                """ No hay posición abierta, abrir una nueva posición corta """
                resultado = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)
            elif self.portafolio.posicion_abierta.tipo == 1:
                """ Hay una posición larga abierta, cerrarla """
                resultado, _ = self.portafolio.cerrar_posicion(precio_cierre=precio, episodio=self.episodio)

                # Abrir una nueva posición corta
                resultado = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)
            elif self.portafolio.posicion_abierta.tipo == -1:
                """ Ya hay una posición corta abierta, reducir o aumentar la posición """
                resultado = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=action, episodio=self.episodio)
        
        else:
            pass # Mantener la posición actual (no hacer nada)

        return resultado