""" Entorno de entrenamiento para agentes de trading reinforcement learning"""
import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Any, Optional, List

from src.Entrenamiento.config import Config
from src.Entrenamiento.entorno.portafolio import Portafolio

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.entorno")

class TradingEnv(gym.Env):

    def __init__(self, config: Config, data: pd.DataFrame, portafolio: Portafolio) -> None:
        """Inicializa el entorno de trading con logging y validación completa."""
        
        try:
            super().__init__()
            
            # Validar entradas
            if config is None:
                raise ValueError("La configuración no puede ser None")
            if data is None or data.empty:
                raise ValueError("Los datos no pueden ser None o estar vacíos")
            if portafolio is None:
                raise ValueError("El portafolio no puede ser None")
            
            # Separar columnas numéricas (excluir timestamp)
            self.numeric_columns: List[str] = [col for col in data.columns if col != 'timestamp']
            
            # Convertir solo columnas numéricas a NumPy para mayor eficiencia
            try:
                self.data_array: np.ndarray = data[self.numeric_columns].values.astype(np.float32)
                self.n_filas: int
                self.n_columnas: int
                self.n_filas, self.n_columnas = self.data_array.shape
            except Exception as e:
                log.error(f"Error al convertir datos a array NumPy: {e}")
                raise ValueError(f"Error en la conversión de datos: {e}")
            
            # Crear un mapeo de nombres de columnas a índices para acceso rápido
            self.column_map: Dict[str, int] = {col: idx for idx, col in enumerate(self.numeric_columns)}
            
            if 'close' not in self.column_map:
                raise ValueError("La columna 'close' es requerida en los datos")
            
            self.close_idx: int = self.column_map['close']
            
            # Guardar también los timestamps si son necesarios - Fix type annotation
            self.timestamps: Optional[Any] = None
            if 'timestamp' in data.columns:
                try:
                    # Convert to numpy array explicitly to fix type issues
                    self.timestamps = np.asarray(data['timestamp'].values)
                except Exception as e:
                    log.warning(f"Error al procesar timestamps: {e}")
                    self.timestamps = None

            self.window_size: int = config.entorno.window_size
            if self.window_size <= 0 or self.window_size >= self.n_filas:
                raise ValueError(f"Window size inválido: {self.window_size}. Debe estar entre 1 y {self.n_filas-1}")

            self._construir_espacios()

            self.paso_actual: int = self.window_size - 1
            self.episodio: int = 0
            
            self.portafolio: Portafolio = portafolio
            
            self.max_drawdown_permitido: float = config.entorno.max_drawdown_permitido
            self.factor_aversion_riesgo: float = config.entorno.factor_aversion_riesgo
            self.umbral_manterner_posicion: float = config.entorno.umbral_mantener_posicion
            
            self.pnl_anterior: float = 0.0
            
        except Exception as e:
            log.error(f"Error crítico durante la inicialización del entorno: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _construir_espacios(self) -> None:
        """Construye los espacios de observación y acción con validación."""
        
        try:
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
            
        except Exception as e:
            log.error(f"Error al construir espacios: {e}")
            raise

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reinicia el entorno para un nuevo episodio de entrenamiento."""
        
        try:
            super().reset(seed=seed)
            self.paso_actual = self.window_size - 1
            self.episodio += 1
            self.portafolio.reset()

            observacion: np.ndarray = self._get_observation()
            
            info: Dict[str, Any] = {'status': 'Entorno reiniciado'}
            
            return observacion, info
            
        except Exception as e:
            log.error(f"Error al reiniciar el entorno: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Ejecución de un paso en el entorno con manejo completo de errores."""
        
        try:
            # Validar acción
            if action is None or len(action) == 0:
                raise ValueError("La acción no puede ser None o vacía")
            
            if not isinstance(action, np.ndarray):
                action = np.array(action, dtype=np.float32)

            self.portafolio.conteovelas()

            precio_actual: float = float(self.data_array[self.paso_actual, self.close_idx])

            # 1. Ejecutar la acción del instante t:
            operacion_info: Dict[str, Any] = self._ejecutar_action(action[0], precio_actual)

            # Avanzamos en el tiempo t --> t + 1
            self.paso_actual += 1
            
            # Comprobamos si se han terminado los datos:
            truncated: bool = self.paso_actual >= self.n_filas - 1

            if truncated:
                observacion: np.ndarray = np.zeros(self.observation_space.shape, dtype=np.float32) #type: ignore
                recompensa: float = 0.0
                terminated: bool = False
                
                info: Dict[str, Any] = {
                    'status': 'Fin de los datos',
                    'paso': self.paso_actual,
                    'episodio': self.episodio,
                    **self.portafolio.get_info_portafolio(self.data_array[self.paso_actual-1, self.close_idx])
                }

                return observacion, recompensa, terminated, truncated, info
            
            # Obtenemos el estado en el instante t + 1 
            precio_siguiente: float = float(self.data_array[self.paso_actual, self.close_idx])

            # Calculamos la recompensa:
            recompensa = self._recompensa(precio_siguiente)

            # Obtenemos la nueva observacion
            observacion = self._get_observation()

            # Comprobar si se interrumpe el entrenamiento:
            terminated = self.portafolio.calcular_max_drawdown(precio_siguiente) >= self.max_drawdown_permitido

            if terminated:
                log.warning(f"Episodio terminado por max drawdown: {self.portafolio.calcular_max_drawdown(precio_siguiente):.4f}")

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
            
        except Exception as e:
            log.error(f"Error crítico en step() en paso {self.paso_actual}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _get_observation(self) -> np.ndarray:
        """Construye la observación actual con manejo de errores."""
        
        try:
            # 1. Separar la ventana de datos del mercado usando slicing directo de NumPy
            start: int = self.paso_actual + 1 - self.window_size
            end: int = self.paso_actual + 1
            
            if start < 0 or end > self.n_filas:
                raise IndexError(f"Índices fuera de rango: start={start}, end={end}, n_filas={self.n_filas}")
            
            ventana_datos: np.ndarray = self.data_array[start:end]

            # 2. Calcular el PnL no realizado
            precio_actual: float = float(self.data_array[self.paso_actual, self.close_idx])
            pnl_no_realizado: float = self.portafolio.calcular_PnL_no_realizado(precio_actual)

            # 3. Obtener la posición abierta
            posicion_abierta: float = 0.0
            if self.portafolio.posicion_abierta is not None:
                posicion_abierta = float(self.portafolio.posicion_abierta.tipo)

            # 4. Crear la información del portafolio de manera eficiente
            portafolio_info: np.ndarray = np.full((self.window_size, 2), 
                                    [pnl_no_realizado, posicion_abierta], 
                                    dtype=np.float32)

            # 5. Combinar los datos del mercado con los del portafolio
            observacion: np.ndarray = np.hstack((ventana_datos, portafolio_info))
            
            return observacion
            
        except Exception as e:
            log.error(f"Error al construir observación: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def get_column_value(self, row_idx: int, column_name: str) -> float:
        """Método auxiliar para obtener valores de columnas específicas por nombre."""
        try:
            if column_name not in self.column_map:
                raise ValueError(f"Columna '{column_name}' no encontrada. Columnas disponibles: {list(self.column_map.keys())}")
            if not (0 <= row_idx < self.n_filas):
                raise IndexError(f"Índice {row_idx} fuera de rango. Rango válido: 0-{self.n_filas-1}")
            
            return float(self.data_array[row_idx, self.column_map[column_name]])
            
        except Exception as e:
            log.error(f"Error al obtener valor de columna {column_name} en fila {row_idx}: {e}")
            raise
    
    def get_timestamp(self, row_idx: int) -> Optional[Any]:
        """Obtener timestamp de una fila específica."""
        try:
            if self.timestamps is not None:
                if not (0 <= row_idx < len(self.timestamps)):
                    raise IndexError(f"Índice {row_idx} fuera de rango para timestamps")
                return self.timestamps[row_idx]
            return None
            
        except Exception as e:
            log.error(f"Error al obtener timestamp en fila {row_idx}: {e}")
            raise

    def _recompensa(self, precio: float) -> float:
        """Calcula la recompensa con validación."""
        try:
            pnl_actual: float = self.portafolio.calcular_PnL_no_realizado(precio)
            pnl: float = pnl_actual - self.pnl_anterior

            if pnl < 0:
                # Penalización por pérdidas
                recompensa: float = pnl * self.factor_aversion_riesgo
            else:
                # Recompensa por ganancias
                recompensa = pnl
            
            self.pnl_anterior = pnl_actual
            return recompensa
            
        except Exception as e:
            log.error(f"Error al calcular recompensa: {e}")
            raise

    def _ejecutar_action(self, action: float, precio: float) -> Dict[str, Any]:
        """Ejecuta la acción en el portafolio y retorna información de la operación."""
        
        try:
            # Fix: Aceptar también tipos numpy además de tipos nativos de Python
            if not isinstance(action, (int, float, np.number)):
                raise ValueError(f"La acción debe ser un número, recibido: {type(action)}")
            if not isinstance(precio, (int, float)) or precio <= 0:
                raise ValueError(f"El precio debe ser un número positivo, recibido: {precio}")
            
            operacion_info: Dict[str, Any] = {'tipo_accion': 'mantener', 'resultado': True}
            
            if action > self.umbral_manterner_posicion:
                tipo_posicion: str = 'long'
                operacion_info['tipo_accion'] = 'long'

                if self.portafolio.posicion_abierta is None:
                    resultado, info_apertura = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=action)
                    operacion_info.update({'operacion': 'abrir_long', 'resultado': resultado, **info_apertura})
                    
                elif self.portafolio.posicion_abierta.tipo == -1:
                    resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(precio_cierre=precio)
                    if resultado:
                        self.pnl_anterior = 0.0
                    operacion_info.update({'operacion': 'cerrar_short', 'resultado': resultado, **info_cierre})

                elif self.portafolio.posicion_abierta.tipo == 1:
                    resultado, info_mod = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=action)
                    operacion_info.update({'operacion': 'modificar_long', 'resultado': resultado, **info_mod})
                    
            elif action < -self.umbral_manterner_posicion:
                tipo_posicion = 'short'
                porcentaje_inversion = abs(action)
                operacion_info['tipo_accion'] = 'short'

                if self.portafolio.posicion_abierta is None:
                    resultado, info_apertura = self.portafolio.abrir_posicion(tipo=tipo_posicion, precio=precio, porcentaje_inversion=porcentaje_inversion)
                    operacion_info.update({'operacion': 'abrir_short', 'resultado': resultado, **info_apertura})
                    
                elif self.portafolio.posicion_abierta.tipo == 1:
                    resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(precio_cierre=precio)
                    if resultado:
                        self.pnl_anterior = 0.0
                    operacion_info.update({'operacion': 'cerrar_long', 'resultado': resultado, **info_cierre})

                elif self.portafolio.posicion_abierta.tipo == -1:
                    resultado, info_mod = self.portafolio.modificar_posicion(precio=precio, porcentaje_inversion=porcentaje_inversion)
                    operacion_info.update({'operacion': 'modificar_short', 'resultado': resultado, **info_mod})
            
            return operacion_info
            
        except Exception as e:
            log.error(f"Error al ejecutar acción {action} con precio {precio}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise