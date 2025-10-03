"""Entorno de entrenamiento para agentes de trading reinforcement learning"""

import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Any, Optional, List
from sklearn.preprocessing import StandardScaler

from src.train.config.config import UnifiedConfig
from src.train.Entrenamiento.entorno.portafolio import Portafolio
from src.train.Entrenamiento.entorno.info_builder import build_info_dict

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.entorno")


class TradingEnv(gym.Env):
    def __init__(
        self, 
        config: UnifiedConfig, 
        data: pd.DataFrame, 
        portafolio: Portafolio,
        scaler: Optional[StandardScaler] = None
    ) -> None:
        """Inicializa el entorno de trading con logging, validación y normalización opcional."""

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
            self.numeric_columns: List[str] = [
                col for col in data.columns if col != "timestamp"
            ]

            # Convertir solo columnas numéricas a NumPy para mayor eficiencia
            try:
                self.data_array: np.ndarray = data[self.numeric_columns].values.astype(
                    np.float32
                )
                self.n_filas: int
                self.n_columnas: int
                self.n_filas, self.n_columnas = self.data_array.shape
            except Exception as e:
                log.error(f"Error al convertir datos a array NumPy: {e}")
                raise ValueError(f"Error en la conversión de datos: {e}")

            # Crear un mapeo de nombres de columnas a índices para acceso rápido
            self.column_map: Dict[str, int] = {
                col: idx for idx, col in enumerate(self.numeric_columns)
            }

            if "close" not in self.column_map:
                raise ValueError("La columna 'close' es requerida en los datos")

            self.close_idx: int = self.column_map["close"]

            # Guardar también los timestamps si son necesarios - Fix type annotation
            self.timestamps: Optional[Any] = None
            if "timestamp" in data.columns:
                try:
                    # Convert to numpy array explicitly to fix type issues
                    self.timestamps = np.asarray(data["timestamp"].values)
                except Exception as e:
                    log.warning(f"Error al procesar timestamps: {e}")
                    self.timestamps = None

            self.window_size: int = config.entorno.window_size
            if self.window_size <= 0 or self.window_size >= self.n_filas:
                raise ValueError(
                    f"Window size inválido: {self.window_size}. Debe estar entre 1 y {self.n_filas - 1}"
                )

            self._construir_espacios()

            self.paso_actual: int = self.window_size - 1
            self.episodio: int = 0

            self.portafolio: Portafolio = portafolio

            self.max_drawdown_permitido: float = config.entorno.max_drawdown_permitido
            self.factor_aversion_riesgo: float = config.entorno.factor_aversion_riesgo
            self.umbral_mantener_posicion: float = (
                config.entorno.umbral_mantener_posicion
            )
            # Penalización cuando el agente no opera (evita aprendizaje por inacción)
            self.penalizacion_no_operar: float = config.entorno.penalizacion_no_operar

            # Usamos prev_equity para calcular recompensa relativa basada en equity
            self.prev_equity: float = 0.0

            # Configurar scaler para normalización (NUEVO)
            self.scaler: Optional[StandardScaler] = scaler
            
            # Validar compatibilidad del scaler si está presente
            if self.scaler is not None:
                if hasattr(self.scaler, 'feature_names_in_'):
                    scaler_features = list(self.scaler.feature_names_in_)
                    if scaler_features != self.numeric_columns:
                        log.error("¡Las características del scaler no coinciden con los datos!")
                        log.error(f"Scaler esperaba: {scaler_features}")
                        log.error(f"Datos tienen: {self.numeric_columns}")
                        raise ValueError("Incompatibilidad entre scaler y datos")
                
                log.info("✅ Entorno inicializado con normalización de observaciones")
                log.debug(f"Scaler configurado para {len(self.scaler.feature_names_in_)} características")
            else:
                log.warning("⚠️  Entorno SIN normalización - scaler no proporcionado")

        except Exception as e:
            log.error(f"Error crítico durante la inicialización del entorno: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _construir_espacios(self) -> None:
        """Construye los espacios de observación y acción con validación."""

        try:
            # EL espacio de observación será una matriz con los datos de las últimas N velas
            # y el estado ACTUAL del portafolio (equity, PnL no realizado, posición abierta).
            # Ahora añadimos 3 columnas adicionales: [equity, pnl_no_realizado, posicion]
            # pero la información del portafolio solo se colocará en la ÚLTIMA fila de la ventana
            # (filas anteriores contendrán ceros en esas columnas) para evitar repetirla N veces.
            # Usamos un Dict space con dos entradas:
            # - 'market': la ventana de mercado (window_size x n_columnas)
            # - 'portfolio': vector con [equity, pnl_no_realizado, posicion] (forma (3,))
            # Esto evita el "truco" de repetir la info del portafolio N veces y es más claro
            self.observation_space = spaces.Dict(
                {
                    "market": spaces.Box(
                        low=-np.inf,
                        high=np.inf,
                        shape=(self.window_size, self.n_columnas),
                        dtype=np.float32,
                    ),
                    "portfolio": spaces.Box(
                        low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32
                    ),
                }
            )

            # EL espacio de acción será un valor continuo entre -1 y 1
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(1,), dtype=np.float32
            )

        except Exception as e:
            log.error(f"Error al construir espacios: {e}")
            raise

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, Any]]:
        """Reinicia el entorno para un nuevo episodio de entrenamiento."""

        try:
            super().reset(seed=seed)
            self.paso_actual = self.window_size - 1
            self.episodio += 1
            self.portafolio.reset()

            # Inicializar prev_equity con el equity actual para que la primera recompensa sea 0
            precio_inicio: float = float(
                self.data_array[self.paso_actual, self.close_idx]
            )

            self.prev_equity = float(self.portafolio.get_equity(precio_inicio))

            observacion: Any = self._get_observation()

            info: Dict[str, Any] = {"status": "Entorno reiniciado"}

            return observacion, info

        except Exception as e:
            log.error(f"Error al reiniciar el entorno: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def step(self, action: np.ndarray) -> Tuple[Any, float, bool, bool, Dict[str, Any]]:
        """Ejecución de un paso en el entorno con manejo completo de errores."""

        try:
            # Validar acción
            if action is None or len(action) == 0:
                raise ValueError("La acción no puede ser None o vacía")

            if not isinstance(action, np.ndarray):
                action = np.array(action, dtype=np.float32)

            self.portafolio.conteovelas()

            precio_actual: float = float(
                self.data_array[self.paso_actual, self.close_idx]
            )

            # 1. Ejecutar la acción del instante t:
            operacion_info: Dict[str, Any] = self._ejecutar_action(
                action[0], precio_actual
            )

            # Avanzamos en el tiempo t --> t + 1
            self.paso_actual += 1

            # Comprobamos si se han terminado los datos:
            truncated: bool = self.paso_actual >= self.n_filas - 1

            if truncated:
                # Para el caso truncado retornamos una observación vacía/ceros compatible con el Dict
                market_obs = np.zeros(
                    (self.window_size, self.n_columnas), dtype=np.float32
                )
                # Usar el precio anterior válido para calcular la info del portafolio
                precio_prev = (
                    float(self.data_array[self.paso_actual - 1, self.close_idx])
                    if (self.paso_actual - 1) >= 0
                    else float(self.data_array[0, self.close_idx])
                )
                pnl_no_realizado = (
                    self.portafolio.calcular_PnL_no_realizado(precio_prev)
                    if self.portafolio.posicion_abierta is not None
                    else 0.0
                )
                equity = float(self.portafolio.get_equity(precio_prev))
                posicion_abierta = (
                    float(self.portafolio.posicion_abierta.tipo)
                    if self.portafolio.posicion_abierta is not None
                    else 0.0
                )
                portfolio_obs = np.array(
                    [equity, pnl_no_realizado, posicion_abierta], dtype=np.float32
                )

                observacion = {"market": market_obs, "portfolio": portfolio_obs}
                recompensa: float = 0.0
                terminated: bool = False
                entorno_raw = {
                    "status": "Fin de los datos",
                    "paso": self.paso_actual,
                    "episodio": self.episodio,
                    "timestamp": self.timestamps[self.paso_actual - 1]
                    if self.timestamps is not None
                    else None,
                    "action": float(action[0]),
                }

                portafolio_raw = self.portafolio.get_info_portafolio(precio_prev)

                # operacion info may be empty here
                operacion_raw: Dict[str, Any] = {}

                info = build_info_dict(
                    entorno=entorno_raw,
                    portafolio=portafolio_raw,
                    operacion=operacion_raw,
                )

                return observacion, recompensa, terminated, truncated, info

            # Obtenemos el estado en el instante t + 1
            precio_siguiente: float = float(
                self.data_array[self.paso_actual, self.close_idx]
            )

            # Calculamos la recompensa (si no hay posición abierta y la recompensa es 0,
            # aplicaremos una penalización para evitar aprender a no operar)
            recompensa = self._recompensa(precio_siguiente)

            # Obtenemos la nueva observacion
            observacion = self._get_observation()

            # Comprobar si se interrumpe el entrenamiento:
            terminated = (
                self.portafolio.calcular_max_drawdown(precio_siguiente)
                >= self.max_drawdown_permitido
            )

            if terminated:
                log.warning(
                    f"Episodio terminado por max drawdown: {self.portafolio.calcular_max_drawdown(precio_siguiente):.4f}"
                )

            # Información optimizada y con estructura fija para análisis
            entorno_raw = {
                "paso": self.paso_actual,
                "episodio": self.episodio,
                "timestamp": self.timestamps[self.paso_actual]
                if self.timestamps is not None
                else None,
                "action": float(action[0]),
                "precio": precio_siguiente,
                "recompensa": recompensa,
                "terminated": terminated,
            }

            portafolio_raw = self.portafolio.get_info_portafolio(precio_siguiente)

            operacion_raw = operacion_info or {}

            info = build_info_dict(
                entorno=entorno_raw, portafolio=portafolio_raw, operacion=operacion_raw
            )

            return observacion, recompensa, terminated, truncated, info

        except Exception as e:
            log.error(f"Error crítico en step() en paso {self.paso_actual}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _get_observation(self) -> Dict[str, np.ndarray]:
        """Construye la observación actual con manejo de errores."""

        try:
            # 1. Separar la ventana de datos del mercado usando slicing directo de NumPy
            start: int = self.paso_actual + 1 - self.window_size
            end: int = self.paso_actual + 1

            if start < 0 or end > self.n_filas:
                raise IndexError(
                    f"Índices fuera de rango: start={start}, end={end}, n_filas={self.n_filas}"
                )

            ventana_datos: np.ndarray = self.data_array[start:end]

            # 2. APLICAR NORMALIZACIÓN si el scaler está disponible
            if self.scaler is not None:
                try:
                    # Transformación directa con NumPy (más eficiente)
                    ventana_normalizada = self.scaler.transform(ventana_datos)
                    market_obs = ventana_normalizada.astype(np.float32)
                    
                except Exception as e:
                    log.error(f"Error al normalizar observación: {e}")
                    log.warning("Usando datos sin normalizar como fallback")
                    market_obs = ventana_datos.astype(np.float32)
            else:
                # Sin scaler, usar datos originales
                market_obs = ventana_datos.astype(np.float32)

            # 3. Calcular la información actual del portafolio (solo una vez)
            precio_actual: float = float(
                self.data_array[self.paso_actual, self.close_idx]
            )
            pnl_no_realizado: float = self.portafolio.calcular_PnL_no_realizado(
                precio_actual
            )

            # equity actual útil para que el agente tenga una señal del tamaño de la cuenta
            equity_actual: float = float(self.portafolio.get_equity(precio_actual))

            # 4. Obtener la posición abierta
            posicion_abierta: float = 0.0
            if self.portafolio.posicion_abierta is not None:
                posicion_abierta = float(self.portafolio.posicion_abierta.tipo)

            # 5. Devolver un dict con dos entradas para mayor claridad y compatibilidad con SB3
            # NOTA: portfolio_obs NO se normaliza, solo market_obs
            portfolio_obs: np.ndarray = np.array(
                [equity_actual, pnl_no_realizado, posicion_abierta], dtype=np.float32
            )

            return {"market": market_obs, "portfolio": portfolio_obs}

        except Exception as e:
            log.error(f"Error al construir observación: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def get_column_value(self, row_idx: int, column_name: str) -> float:
        """Método auxiliar para obtener valores de columnas específicas por nombre."""
        try:
            if column_name not in self.column_map:
                raise ValueError(
                    f"Columna '{column_name}' no encontrada. Columnas disponibles: {list(self.column_map.keys())}"
                )
            if not (0 <= row_idx < self.n_filas):
                raise IndexError(
                    f"Índice {row_idx} fuera de rango. Rango válido: 0-{self.n_filas - 1}"
                )

            return float(self.data_array[row_idx, self.column_map[column_name]])

        except Exception as e:
            log.error(
                f"Error al obtener valor de columna {column_name} en fila {row_idx}: {e}"
            )
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
            # Calculamos la recompensa como cambio relativo del equity:
            equity_actual: float = float(self.portafolio.get_equity(precio))
            delta_equity: float = equity_actual - self.prev_equity

            if delta_equity < 0:
                recompensa: float = delta_equity * self.factor_aversion_riesgo
            else:
                recompensa = delta_equity
            # Si no hay posición abierta y la recompensa es 0, aplicar penalización
            try:
                if (
                    float(recompensa) == 0.0
                    and self.portafolio.posicion_abierta is None
                ):
                    recompensa = float(recompensa) - float(self.penalizacion_no_operar)
            except Exception:
                # En caso de cualquier problema inspeccionando la posición, no bloquear la recompensa
                pass

            # Actualizamos prev_equity para el siguiente paso
            self.prev_equity = equity_actual
            return float(recompensa)

        except Exception as e:
            log.error(f"Error al calcular recompensa: {e}")
            raise

    def _ejecutar_action(self, action: float, precio: float) -> Dict[str, Any]:
        """Ejecuta la acción en el portafolio y retorna información de la operación."""

        try:
            # Fix: Aceptar también tipos numpy además de tipos nativos de Python
            if not isinstance(action, (int, float, np.number)):
                raise ValueError(
                    f"La acción debe ser un número, recibido: {type(action)}"
                )
            if not isinstance(precio, (int, float)) or precio <= 0:
                raise ValueError(
                    f"El precio debe ser un número positivo, recibido: {precio}"
                )

            operacion_info: Dict[str, Any] = {
                "tipo_accion": "mantener",
                "resultado": True,
            }

            if action > self.umbral_mantener_posicion:
                tipo_posicion: str = "long"
                operacion_info["tipo_accion"] = "long"

                if self.portafolio.posicion_abierta is None:
                    resultado, info_apertura = self.portafolio.abrir_posicion(
                        tipo=tipo_posicion, precio=precio, porcentaje_inversion=action
                    )
                    operacion_info.update(
                        {
                            "operacion": "abrir_long",
                            "resultado": resultado,
                            **info_apertura,
                        }
                    )

                elif self.portafolio.posicion_abierta.tipo == -1:
                    resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(
                        precio_cierre=precio
                    )
                    operacion_info.update(
                        {
                            "operacion": "cerrar_short",
                            "resultado": resultado,
                            **info_cierre,
                        }
                    )

                elif self.portafolio.posicion_abierta.tipo == 1:
                    resultado, info_mod = self.portafolio.modificar_posicion(
                        precio=precio, porcentaje_inversion=action
                    )
                    operacion_info.update(
                        {
                            "operacion": "modificar_long",
                            "resultado": resultado,
                            **info_mod,
                        }
                    )

            elif action < -self.umbral_mantener_posicion:
                tipo_posicion = "short"
                porcentaje_inversion = abs(action)
                operacion_info["tipo_accion"] = "short"

                if self.portafolio.posicion_abierta is None:
                    resultado, info_apertura = self.portafolio.abrir_posicion(
                        tipo=tipo_posicion,
                        precio=precio,
                        porcentaje_inversion=porcentaje_inversion,
                    )
                    operacion_info.update(
                        {
                            "operacion": "abrir_short",
                            "resultado": resultado,
                            **info_apertura,
                        }
                    )

                elif self.portafolio.posicion_abierta.tipo == 1:
                    resultado, pnl, info_cierre = self.portafolio.cerrar_posicion(
                        precio_cierre=precio
                    )
                    operacion_info.update(
                        {
                            "operacion": "cerrar_long",
                            "resultado": resultado,
                            **info_cierre,
                        }
                    )

                elif self.portafolio.posicion_abierta.tipo == -1:
                    resultado, info_mod = self.portafolio.modificar_posicion(
                        precio=precio, porcentaje_inversion=porcentaje_inversion
                    )
                    operacion_info.update(
                        {
                            "operacion": "modificar_short",
                            "resultado": resultado,
                            **info_mod,
                        }
                    )

            return operacion_info

        except Exception as e:
            log.error(f"Error al ejecutar acción {action} con precio {precio}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise
