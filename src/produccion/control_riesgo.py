"""Sistema de control de riesgo para el trading en producción.

Gestiona validaciones de seguridad, límites de drawdown y protocolo de emergencia.
"""

import logging
from typing import Dict, Any, Tuple, Optional

from src.produccion.binance import BinanceConnector
from src.produccion.config.config import ProductionConfig

log = logging.getLogger("AFML.ControlRiesgo")


class ControlRiesgo:
    """Valida operaciones y gestiona el protocolo de emergencia."""
    
    def __init__(self, config: ProductionConfig, binance: BinanceConnector) -> None:
        """
        Inicializa el sistema de control de riesgo.
        
        Args:
            config: Configuración de producción
            binance: Conector de Binance para obtener información de la cuenta
        """
        self.config = config
        self.binance = binance
        
        # Parámetros de riesgo
        self.max_drawdown = config.max_drawdown_permitido
        self.capital_inicial = config.capital_inicial
        
        # Tracking del equity máximo alcanzado
        self.max_equity_alcanzado = self.capital_inicial
        
        # Estado del sistema
        self.emergencia_activa = False
        self.razon_emergencia: Optional[str] = None
        
        log.info("✅ Control de riesgo inicializado")
        log.info(f"   Max drawdown permitido: {self.max_drawdown * 100:.1f}%")
        log.info(f"   Capital inicial: {self.capital_inicial}")
    
    def verificar_drawdown(self) -> Tuple[bool, float]:
        """
        Verifica si el drawdown actual está dentro de los límites permitidos.
        
        Returns:
            Tupla (ok: bool, drawdown_actual: float)
            - ok: True si está dentro del límite, False si se excedió
            - drawdown_actual: Valor del drawdown actual (0.0 a 1.0)
        """
        try:
            # Obtener equity actual
            position_info = self.binance.get_position_info()
            equity_actual = position_info['equity']
            
            # Actualizar max equity si es necesario
            if equity_actual > self.max_equity_alcanzado:
                self.max_equity_alcanzado = equity_actual
                log.debug(f"Nuevo máximo equity alcanzado: {self.max_equity_alcanzado:.2f}")
            
            # Calcular drawdown actual
            if self.max_equity_alcanzado > 0:
                drawdown_actual = (self.max_equity_alcanzado - equity_actual) / self.max_equity_alcanzado
            else:
                drawdown_actual = 0.0
            
            # Verificar si se excedió el límite
            ok = drawdown_actual < self.max_drawdown
            
            if not ok:
                log.critical(f"🚨 LÍMITE DE DRAWDOWN EXCEDIDO!")
                log.critical(f"   Drawdown actual: {drawdown_actual * 100:.2f}%")
                log.critical(f"   Límite: {self.max_drawdown * 100:.2f}%")
                log.critical(f"   Max equity: {self.max_equity_alcanzado:.2f}")
                log.critical(f"   Equity actual: {equity_actual:.2f}")
            elif drawdown_actual > self.max_drawdown * 0.8:
                # Advertencia cuando está cerca del límite (80% del drawdown máximo)
                log.warning(f"⚠️  Drawdown alto: {drawdown_actual * 100:.2f}% (límite: {self.max_drawdown * 100:.2f}%)")
            
            return ok, drawdown_actual
            
        except Exception as e:
            log.error(f"Error al verificar drawdown: {e}")
            # En caso de error, asumir que NO está ok por seguridad
            return False, 1.0
    
    def validar_accion_pre(self, accion_interpretada: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida la acción ANTES de ejecutarla.
        
        Args:
            accion_interpretada: Diccionario con información de la acción:
                {
                    'tipo': 'long'/'short'/'mantener',
                    'operacion': 'abrir'/'cerrar'/'aumentar'/'reducir',
                    'debe_ejecutar': bool
                }
        
        Returns:
            Tupla (valida: bool, razon: str)
            - valida: True si la acción puede ejecutarse
            - razon: Razón de rechazo si no es válida
        """
        try:
            # Si es emergencia activa, rechazar todo
            if self.emergencia_activa:
                return False, "Sistema en modo emergencia"
            
            # Si no debe ejecutar, aprobar (es solo mantener)
            if not accion_interpretada.get('debe_ejecutar', False):
                return True, "Mantener posición - sin validaciones necesarias"
            
            # Obtener información de la cuenta
            position_info = self.binance.get_position_info()
            
            # Validar que haya balance disponible para abrir posiciones
            if accion_interpretada['operacion'] in ['abrir', 'aumentar']:
                if position_info['balance'] <= 0:
                    return False, "Balance insuficiente"
                
                # Aquí podrías añadir más validaciones:
                # - Verificar margen disponible
                # - Límite de tamaño de posición
                # - etc.
            
            # Si llegamos aquí, la acción es válida
            return True, "Validación exitosa"
            
        except Exception as e:
            log.error(f"Error al validar acción: {e}")
            return False, f"Error en validación: {e}"
    
    def activar_protocolo_emergencia(self, razon: str) -> Dict[str, Any]:
        """
        Activa el protocolo de emergencia: cierra todas las posiciones inmediatamente.
        
        Args:
            razon: Razón de la activación del protocolo
            
        Returns:
            Diccionario con el resultado del protocolo:
            {
                'exitoso': bool,
                'posiciones_cerradas': int,
                'balance_final': float,
                'equity_final': float,
                'errores': List[str]
            }
        """
        try:
            log.critical("=" * 80)
            log.critical("🚨 ACTIVANDO PROTOCOLO DE EMERGENCIA 🚨")
            log.critical(f"Razón: {razon}")
            log.critical("=" * 80)
            
            self.emergencia_activa = True
            self.razon_emergencia = razon
            
            # Cerrar todas las posiciones
            resultado_cierre = self.binance.close_all_positions(emergency=True)
            
            # Determinar si fue exitoso
            exitoso = len(resultado_cierre['errores']) == 0
            
            resultado = {
                'exitoso': exitoso,
                'posiciones_cerradas': resultado_cierre['posiciones_cerradas'],
                'balance_final': resultado_cierre['balance_final'],
                'equity_final': resultado_cierre['equity_final'],
                'errores': resultado_cierre['errores'],
            }
            
            if exitoso:
                log.critical("✅ Protocolo de emergencia ejecutado exitosamente")
            else:
                log.critical("❌ Protocolo de emergencia completado con errores")
                for error in resultado['errores']:
                    log.critical(f"   - {error}")
            
            log.critical("=" * 80)
            
            return resultado
            
        except Exception as e:
            log.critical(f"❌ ERROR CRÍTICO en protocolo de emergencia: {e}")
            return {
                'exitoso': False,
                'posiciones_cerradas': 0,
                'balance_final': 0.0,
                'equity_final': 0.0,
                'errores': [str(e)],
            }
    
    def puede_reiniciar(self) -> bool:
        """
        Determina si el sistema puede reiniciarse después de una emergencia.
        
        Returns:
            True si puede reiniciar, False si debe permanecer detenido
        """
        # Si la emergencia fue por max drawdown, NO permitir reinicio
        if self.razon_emergencia and 'drawdown' in self.razon_emergencia.lower():
            log.warning("❌ No se puede reiniciar: emergencia por max drawdown")
            return False
        
        # Para otros tipos de emergencia (errores de conexión, etc.), sí permitir
        log.info("✅ Reinicio permitido: emergencia operacional")
        return True
    
    def reset_emergencia(self) -> None:
        """Resetea el estado de emergencia (solo si puede reiniciar)."""
        if self.puede_reiniciar():
            self.emergencia_activa = False
            self.razon_emergencia = None
            log.info("Estado de emergencia reseteado")
        else:
            log.warning("No se puede resetear el estado de emergencia")