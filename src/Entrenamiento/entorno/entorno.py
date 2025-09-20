""" Entorno de entrenamiento para agentes de trading reinforcement learning"""
import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
from typing import Tuple

from src.Entrenamiento.config import Config
from src.Entrenamiento.entorno.portafolio import Portafolio

class TradingEnv(gym.Env):

    def __init__(self, config: Config, data: pd.DataFrame, portafolio: Portafolio):
        super().__init__()
        # Separar columnas numéricas (excluir timestamp)
        self.numeric_columns = [col for col in data.columns if col != 'timestamp']
        
        # Convertir solo columnas numéricas a NumPy para mayor eficiencia
        self.data_array = data[self.numeric_columns].values.astype(np.float32)
        self.n_filas, self.n_columnas = self.data_array.shape
        
        # Crear un mapeo de nombres de columnas a índices para acceso rápido
        self.column_map = {col: idx for idx, col in enumerate(self.numeric_columns)}
        self.close_idx = self.column_map['close']
        
        # Guardar también los timestamps si son necesarios
        self.timestamps = data['timestamp'].values if 'timestamp' in data.columns else None

        self.window_size = config.entorno.window_size

        self._construir_espacios()

        self.paso_actual = self.window_size - 1 # Porque en python los índices empiezan en 0
        self.episodio = 0 # El episodio del entrenamiento
        
        self.portafolio = portafolio
        
        self.max_drawdown_permitido = config.entorno.max_drawdown_permitido
        self.factor_aversion_riesgo = config.entorno.factor_aversion_riesgo
        self.umbral_manterner_posicion = config.entorno.umbral_mantener_posicion
        
        self.pnl_anterior = 0.0 # Para calcular la recompensa

    def _construir_espacios(self):
        """Construye los espacios de observación y acción."""
        # EL espacio de observación será una matriz con los datos de las últimas N velas
        # y el estado ACTUAL del portafolio (PnL no realizado, posición abierta) 
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.window_size, self.n_columnas + 2), # +2 para PnL y posición
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

        observacion = self._get_observation()
        
        info = {'status': 'Entorno reiniciado'}
        return observacion, info

    

    def step(self, action: np.ndarray) -> Tuple:
        """ Ejecución de un paso en el entorno.
        Para conocer el efecto de una acción, necesitamos conocer el instante actual t y el siguiente t+1.
        """

        self.portafolio.conteovelas()

        precio_actual = self.data_array[self.paso_actual, self.close_idx]

        # 1. Ejecutar la acción del instante t:
        operacion_info = self._ejecutar_action(action[0], precio_actual)

        # Avanzamos en el tiempo t --> t + 1
        self.paso_actual += 1
        
        # Comprobamos si se han terminado los datos:
        truncated = self.paso_actual >= self.n_filas - 1

        if truncated:
            observacion = np.zeros(self.observation_space.shape, dtype=np.float32) #type: ignore
            recompensa = 0
            terminated = False # No es un fallo, solo se acabaron los datos.
            
            # Información final del episodio
            info = {
                'status': 'Fin de los datos',
                'paso': self.paso_actual,
                'episodio': self.episodio,
                **self.portafolio.get_info_portafolio(self.data_array[self.paso_actual-1, self.close_idx])
            }

            return observacion, recompensa, terminated, truncated, info
        
        # Obtenemos el estado en el instante t + 1 
        precio_siguiente = self.data_array[self.paso_actual, self.close_idx]

        # Calculamos la recompensa:
        recompensa = self._recompensa(precio_siguiente)

        # Obtenemos la nueva observacion
        observacion = self._get_observation()

        # Comprobar si se interrumpe el entrenamiento:
        terminated = self.portafolio.calcular_max_drawdown(precio_siguiente) >= self.max_drawdown_permitido

        # Información optimizada para análisis y Power BI
        info = {
            'paso': self.paso_actual,
            'episodio': self.episodio,
            'timestamp': self.timestamps[self.paso_actual] if self.timestamps is not None else None,
            'action': float(action[0]),
            'precio': precio_siguiente,
            'recompensa': recompensa,
            'terminated': terminated,
            **operacion_info,
            **self.portafolio.get_info_portafolio(precio_siguiente)
        }

        return observacion, recompensa, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """ Construye la observación actual. """

        # 1. Separar la ventana de datos del mercado usando slicing directo de NumPy
        start = self.paso_actual + 1 - self.window_size
        end = self.paso_actual + 1
        ventana_datos = self.data_array[start:end]

        # 2. Calcular el PnL no realizado
        precio_actual = self.data_array[self.paso_actual, self.close_idx]
        pnl_no_realizado = self.portafolio.calcular_PnL_no_realizado(precio_actual)

        # 3. Obtener la posición abierta (ya está en un rango pequeño: -1, 0, 1)
        # Es buena práctica asegurarse de que sea un float para consistencia.
        posicion_abierta = 0.0
        if self.portafolio.posicion_abierta is not None:
            posicion_abierta = float(self.portafolio.posicion_abierta.tipo)

        # 4. Crear la información del portafolio de manera eficiente
        portafolio_info = np.full((self.window_size, 2), 
                                [pnl_no_realizado, posicion_abierta], 
                                dtype=np.float32)

        # 5. Combinar los datos del mercado con los del portafolio
        observacion = np.hstack((ventana_datos, portafolio_info))
        
        return observacion

    def get_column_value(self, row_idx: int, column_name: str) -> float:
        """Método auxiliar para obtener valores de columnas específicas por nombre."""
        if column_name not in self.column_map:
            raise ValueError(f"Columna '{column_name}' no encontrada. Columnas disponibles: {list(self.column_map.keys())}")
        if not (0 <= row_idx < self.n_filas):
            raise IndexError(f"Índice {row_idx} fuera de rango. Rango válido: 0-{self.n_filas-1}")
        return self.data_array[row_idx, self.column_map[column_name]]
    
    def get_timestamp(self, row_idx: int):
        """Obtener timestamp de una fila específica."""
        if self.timestamps is not None:
            if not (0 <= row_idx < len(self.timestamps)):
                raise IndexError(f"Índice {row_idx} fuera de rango para timestamps")
            return self.timestamps[row_idx]
        return None

    def _recompensa(self, precio: float) -> float:
        """ Calcula la recompensa."""
        pnl_actual = self.portafolio.calcular_PnL_no_realizado(precio)

        pnl = pnl_actual - self.pnl_anterior

        if pnl < 0:
            # Penalización por pérdidas
            recompensa = pnl * self.factor_aversion_riesgo
        else:
            # Recompensa por ganancias
            recompensa = pnl
        
        self.pnl_anterior = pnl_actual
        return recompensa

    def _ejecutar_action(self, action: float, precio: float) -> dict:
        """ Ejecuta la acción en el portafolio y retorna información de la operación. """
        operacion_info = {'tipo_accion': 'mantener', 'resultado': True}
        
        if action > self.umbral_manterner_posicion:
            tipo_posicion = 'long'
            operacion_info['tipo_accion'] = 'long'

            if self.portafolio.posicion_abierta is None:
                """ No hay posición abierta, abrir una nueva posición larga """
                resultado, info_apertura = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)
                operacion_info.update({'operacion': 'abrir_long', 'resultado': resultado, **info_apertura})
                
            elif self.portafolio.posicion_abierta.tipo == -1:
                """ Hay una posición corta abierta, cerrarla """
                resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(precio_cierre=precio)
                if resultado:
                    self.pnl_anterior = 0.0 # Reiniciar el PnL anterior al cerrar la posición
                operacion_info.update({'operacion': 'cerrar_short', 'resultado': resultado, **info_cierre})

            elif self.portafolio.posicion_abierta.tipo == 1:
                """ Ya hay una posición larga abierta, reducir o aumentar la posición """
                resultado, info_mod = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=action)
                operacion_info.update({'operacion': 'modificar_long', 'resultado': resultado, **info_mod})
                
        elif action < -self.umbral_manterner_posicion:
            tipo_posicion = 'short'
            porcentaje_inversion = abs(action)
            operacion_info['tipo_accion'] = 'short'

            if self.portafolio.posicion_abierta is None:
                """ No hay posición abierta, abrir una nueva posición corta """
                resultado, info_apertura = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=porcentaje_inversion)
                operacion_info.update({'operacion': 'abrir_short', 'resultado': resultado, **info_apertura})
                
            elif self.portafolio.posicion_abierta.tipo == 1:
                """ Hay una posición larga abierta, cerrarla """
                resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(precio_cierre=precio)
                if resultado:
                    self.pnl_anterior = 0.0 # Reiniciar el PnL anterior al cerrar la posición
                operacion_info.update({'operacion': 'cerrar_long', 'resultado': resultado, **info_cierre})

            elif self.portafolio.posicion_abierta.tipo == -1:
                """ Ya hay una posición corta abierta, reducir o aumentar la posición """
                resultado, info_mod = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=porcentaje_inversion)
                operacion_info.update({'operacion': 'modificar_short', 'resultado': resultado, **info_mod})
        
        return operacion_info