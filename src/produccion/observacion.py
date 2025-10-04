"""Constructor de observaciones para el agente en producción.

Normaliza los datos de mercado y portfolio de forma idéntica al entrenamiento.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.preprocessing import StandardScaler

from src.produccion.config.config import ProductionConfig

log = logging.getLogger("AFML.Observacion")


class ObservacionBuilder:
    """Construye observaciones normalizadas para el agente SAC."""
    
    def __init__(self, config: ProductionConfig, scaler: StandardScaler) -> None:
        """
        Inicializa el constructor de observaciones.
        
        Args:
            config: Configuración de producción
            scaler: StandardScaler entrenado para normalizar datos de mercado
        """
        self.config = config
        self.scaler = scaler
        self.window_size = config.window_size
        self.normalizar_portfolio = config.normalizar_portfolio
        
        # Valores estáticos para normalización de portfolio (mismos que en entrenamiento)
        # Estos valores son aproximados para escalar equity, PnL y posición
        self.equity_scale = 10000.0  # Escala basada en capital inicial
        self.pnl_scale = 1000.0      # Escala para PnL no realizado
        
        log.info("✅ Constructor de observaciones inicializado")
        log.info(f"   Window size: {self.window_size}")
        log.info(f"   Normalización portfolio: {'SÍ' if self.normalizar_portfolio else 'NO'}")
    
    def construir_observacion(
        self, 
        ventana_df: pd.DataFrame, 
        binance_state: Dict[str, Any]
    ) -> Dict[str, np.ndarray]:
        """
        Construye la observación normalizada para el agente.
        
        Args:
            ventana_df: DataFrame con ventana completa de datos (ya con indicadores)
            binance_state: Estado del portfolio de Binance con claves:
                - 'equity': float
                - 'pnl_no_realizado': float
                - 'posicion_abierta': bool
                
        Returns:
            Diccionario con estructura {'market': np.array, 'portfolio': np.array}
        """
        try:
            # 1. Extraer últimas window_size filas
            if len(ventana_df) < self.window_size:
                raise ValueError(
                    f"Ventana insuficiente: {len(ventana_df)} < {self.window_size}"
                )
            
            ventana_reciente = ventana_df.tail(self.window_size).copy()
            
            # 2. Eliminar columna timestamp si existe
            if 'timestamp' in ventana_reciente.columns:
                ventana_reciente = ventana_reciente.drop(columns=['timestamp'])
            
            # 3. Normalizar datos de mercado con scaler
            try:
                market_data = self.scaler.transform(ventana_reciente)
                market_obs = market_data.astype(np.float32)
                
                log.debug(f"Market observation normalizada: shape={market_obs.shape}")
                
            except Exception as e:
                log.error(f"Error al normalizar datos de mercado: {e}")
                raise
            
            # 4. Construir portfolio observation
            equity = binance_state.get('equity', 0.0)
            pnl_no_realizado = binance_state.get('pnl_no_realizado', 0.0)
            posicion_abierta = 1.0 if binance_state.get('posicion_abierta', False) else 0.0
            
            # 5. Normalizar portfolio si está configurado
            if self.normalizar_portfolio:
                # Normalización estática (igual que en entrenamiento)
                equity_norm = equity / self.equity_scale
                pnl_norm = pnl_no_realizado / self.pnl_scale
                # posicion_abierta ya es 0 o 1, no necesita normalización
                
                portfolio_obs = np.array(
                    [equity_norm, pnl_norm, posicion_abierta], 
                    dtype=np.float32
                )
                
                log.debug(
                    f"Portfolio normalizado: equity={equity_norm:.4f}, "
                    f"pnl={pnl_norm:.4f}, posicion={posicion_abierta}"
                )
            else:
                # Sin normalización
                portfolio_obs = np.array(
                    [equity, pnl_no_realizado, posicion_abierta], 
                    dtype=np.float32
                )
                
                log.debug(
                    f"Portfolio sin normalizar: equity={equity:.2f}, "
                    f"pnl={pnl_no_realizado:.2f}, posicion={posicion_abierta}"
                )
            
            # 6. Retornar observación completa
            observacion = {
                'market': market_obs,
                'portfolio': portfolio_obs
            }
            
            return observacion
            
        except Exception as e:
            log.error(f"Error al construir observación: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise
