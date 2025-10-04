"""Agente SAC para producción.

Encapsula la carga del modelo entrenado, predicción determinística e interpretación de acciones.
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
from stable_baselines3 import SAC

from src.produccion.config.config import ProductionConfig

log = logging.getLogger("AFML.AgenteProduccion")


class AgenteProduccion:
    """Agente de trading usando modelo SAC entrenado."""
    
    def __init__(self, config: ProductionConfig) -> None:
        """
        Inicializa el agente de producción.
        
        Args:
            config: Configuración de producción con path del modelo
        """
        self.config = config
        self.umbral_mantener = config.umbral_mantener_posicion
        
        # Cargar modelo entrenado
        log.info(f"Cargando modelo desde: {config.model_path}")
        try:
            self.model = SAC.load(config.model_path)
            log.info("✅ Modelo SAC cargado exitosamente")
        except Exception as e:
            log.error(f"Error al cargar el modelo: {e}")
            raise
    
    def predict(self, observacion: Dict[str, np.ndarray]) -> float:
        """
        Genera una predicción determinística del modelo.
        
        Args:
            observacion: Diccionario con claves 'market' y 'portfolio'
            
        Returns:
            Acción del agente (valor escalar entre -1 y 1)
        """
        try:
            # Predicción determinística (sin exploración)
            accion, _states = self.model.predict(observacion, deterministic=True)
            
            # Extraer valor escalar
            accion_valor = float(accion[0])
            
            log.debug(f"Predicción del modelo: {accion_valor:.4f}")
            
            return accion_valor
            
        except Exception as e:
            log.error(f"Error en predicción del modelo: {e}")
            # Retornar acción neutra en caso de error
            return 0.0
    
    def interpretar_accion(
        self, 
        accion: float, 
        tiene_posicion_abierta: bool,
        tipo_posicion_activa: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interpreta la acción del agente y determina la operación a realizar.
        Lógica idéntica a entorno.py para mantener consistencia.
        
        Args:
            accion: Valor de la acción entre -1 y 1
            tiene_posicion_abierta: Si hay una posición actualmente abierta
            tipo_posicion_activa: 'LONG' o 'SHORT' si hay posición abierta
            
        Returns:
            Diccionario con la interpretación:
            {
                'tipo_accion': 'long'/'short'/'mantener',
                'operacion': 'abrir'/'cerrar'/'aumentar'/'reducir'/'mantener',
                'debe_ejecutar': bool,
                'intensidad': float,  # Valor absoluto de la acción
            }
        """
        # Valor absoluto indica la intensidad
        intensidad = abs(accion)
        
        # Por defecto: mantener posición
        resultado = {
            'tipo_accion': 'mantener',
            'operacion': 'mantener',
            'debe_ejecutar': False,
            'intensidad': intensidad,
        }
        
        # CASO 1: Acción es mantener (dentro del umbral)
        if -self.umbral_mantener <= accion <= self.umbral_mantener:
            log.debug(f"Acción MANTENER (valor: {accion:.4f}, umbral: ±{self.umbral_mantener})")
            return resultado
        
        # CASO 2: Acción es LONG (comprar)
        if accion > self.umbral_mantener:
            resultado['tipo_accion'] = 'long'
            
            if not tiene_posicion_abierta:
                # Abrir nueva posición LONG
                resultado['operacion'] = 'abrir_long'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → ABRIR LONG (intensidad: {intensidad:.2f})")
                
            elif tipo_posicion_activa == 'LONG':
                # Ya tenemos LONG, aumentar posición
                resultado['operacion'] = 'aumentar_long'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → AUMENTAR LONG (intensidad: {intensidad:.2f})")
                
            elif tipo_posicion_activa == 'SHORT':
                # Tenemos SHORT, solo cerrar (NO reabrir - una acción por paso)
                resultado['operacion'] = 'cerrar_short'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → CERRAR SHORT (intensidad: {intensidad:.2f})")
        
        # CASO 3: Acción es SHORT (vender)
        elif accion < -self.umbral_mantener:
            resultado['tipo_accion'] = 'short'
            
            if not tiene_posicion_abierta:
                # Abrir nueva posición SHORT
                resultado['operacion'] = 'abrir_short'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → ABRIR SHORT (intensidad: {intensidad:.2f})")
                
            elif tipo_posicion_activa == 'SHORT':
                # Ya tenemos SHORT, aumentar posición
                resultado['operacion'] = 'aumentar_short'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → AUMENTAR SHORT (intensidad: {intensidad:.2f})")
                
            elif tipo_posicion_activa == 'LONG':
                # Tenemos LONG, solo cerrar (NO reabrir - una acción por paso)
                resultado['operacion'] = 'cerrar_long'
                resultado['debe_ejecutar'] = True
                log.info(f"Interpretar acción → CERRAR LONG (intensidad: {intensidad:.2f})")
        
        return resultado
