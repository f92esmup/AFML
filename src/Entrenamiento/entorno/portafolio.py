""" Simulador de un portafolio de inversiones.

En este script nos encontramos con la clase Portafolio, que gestiona
las operaciones de trading, el balance, el equity y el historial de
operaciones. También incluye la clase Posicion para modelar una
operación abierta.
"""
import pandas as pd
import logging
from src.Entrenamiento.config import Config 
from typing import Tuple, Optional, Dict, Any

# Configurar logger
log: logging.Logger = logging.getLogger("AFML.portafolio")

class Posicion:
    def __init__(self, tipo: str, precio: float, cantidad: float, fecha: pd.Timestamp, 
                 velas: int, comision: float, slippage: float, margen: float, 
                 porcentaje_inv: float, trade_id: int = 0) -> None:
        """Inicializa una posición con validación completa."""
        
        try:
            if tipo not in ['long', 'short']:
                raise ValueError("El tipo de posición debe ser 'long' o 'short'")
            
            if precio <= 0:
                raise ValueError(f"El precio debe ser positivo, recibido: {precio}")
            
            if cantidad <= 0:
                raise ValueError(f"La cantidad debe ser positiva, recibida: {cantidad}")
            
            if porcentaje_inv <= 0 or porcentaje_inv > 1:
                raise ValueError(f"El porcentaje de inversión debe estar entre 0 y 1, recibido: {porcentaje_inv}")
            
            if velas < 0:
                raise ValueError(f"El número de velas no puede ser negativo: {velas}")
            
            if comision < 0:
                raise ValueError(f"La comisión no puede ser negativa: {comision}")
            
            if slippage < 0:
                raise ValueError(f"El slippage no puede ser negativo: {slippage}")
            
            if margen < 0:
                raise ValueError(f"El margen no puede ser negativo: {margen}")
            
            if trade_id < 0:
                raise ValueError(f"El trade_id no puede ser negativo: {trade_id}")
        
            self._tipo: str = tipo
            self._precio: float = precio
            self._cantidad: float = cantidad
            self._fecha: pd.Timestamp = fecha
            self._velas: int = velas
            self._comision: float = comision
            self._slippage: float = slippage
            self._margen: float = margen
            self._porcentaje_inv: float = porcentaje_inv
            self._trade_id: int = trade_id
            
        except Exception as e:
            log.error(f"Error al crear posición: {e}")
            raise
    
    @property
    def tipo(self) -> int:
        return 1 if self._tipo == 'long' else -1
    
    @property
    def porcentaje_inv(self) -> float:
        return self._porcentaje_inv
    
    @porcentaje_inv.setter
    def porcentaje_inv(self, valor: float) -> None:
        try:
            if valor <= 0 or valor > 1:
                raise ValueError(f"Porcentaje de inversión inválido: {valor}")
            self._porcentaje_inv = valor
        except Exception as e:
            log.error(f"Error al establecer porcentaje de inversión: {e}")
            raise
    
    @property
    def precio(self) -> float:
        return self._precio
    
    @precio.setter
    def precio(self, valor: float) -> None:
        try:
            if valor <= 0:
                raise ValueError(f"Precio inválido: {valor}")
            self._precio = valor
        except Exception as e:
            log.error(f"Error al establecer precio: {e}")
            raise
    
    @property
    def cantidad(self) -> float:
        return self._cantidad
    
    @cantidad.setter
    def cantidad(self, valor: float) -> None:
        try:
            if valor <= 0:
                raise ValueError(f"Cantidad inválida: {valor}")
            self._cantidad = valor
        except Exception as e:
            log.error(f"Error al establecer cantidad: {e}")
            raise
    
    @property
    def fecha(self) -> pd.Timestamp:
        return self._fecha
    
    @property
    def velas(self) -> int:
        return self._velas
    
    @velas.setter
    def velas(self, valor: int) -> None:
        try:
            if valor < 0:
                raise ValueError(f"Número de velas inválido: {valor}")
            self._velas = valor
        except Exception as e:
            log.error(f"Error al establecer número de velas: {e}")
            raise
    
    @property
    def comision(self) -> float:
        return self._comision
    
    @comision.setter
    def comision(self, valor: float) -> None:
        try:
            if valor < 0:
                raise ValueError(f"Comisión inválida: {valor}")
            self._comision = valor
        except Exception as e:
            log.error(f"Error al establecer comisión: {e}")
            raise
    
    @property
    def slippage(self) -> float:
        return self._slippage
    
    @slippage.setter
    def slippage(self, valor: float) -> None:
        try:
            if valor < 0:
                raise ValueError(f"Slippage inválido: {valor}")
            self._slippage = valor
        except Exception as e:
            log.error(f"Error al establecer slippage: {e}")
            raise
    
    @property
    def margen(self) -> float:
        return self._margen
    
    @margen.setter
    def margen(self, valor: float) -> None:
        try:
            if valor < 0:
                raise ValueError(f"Margen inválido: {valor}")
            self._margen = valor
        except Exception as e:
            log.error(f"Error al establecer margen: {e}")
            raise
    
    @property
    def trade_id(self) -> int:
        return self._trade_id
    
    @trade_id.setter
    def trade_id(self, valor: int) -> None:
        try:
            if valor < 0:
                raise ValueError(f"Trade ID inválido: {valor}")
            self._trade_id = valor
        except Exception as e:
            log.error(f"Error al establecer trade ID: {e}")
            raise
    
class Portafolio:
    def __init__(self, config: Config) -> None:
        """Inicializa el portafolio con validación completa."""
        
        try:
            if config is None:
                raise ValueError("La configuración no puede ser None")
            
            # Variables de configuración
            self.balance_inicial: float = config.portafolio.capital_inicial
            self.comision_prc: float = config.portafolio.comision
            self.slippage_prc: float = config.portafolio.slippage
            self.apalancamiento: float = config.portafolio.apalancamiento

            # Validar configuración
            if self.balance_inicial <= 0:
                raise ValueError(f"Capital inicial debe ser positivo: {self.balance_inicial}")
            if self.apalancamiento <= 0:
                raise ValueError(f"Apalancamiento debe ser positivo: {self.apalancamiento}")
            if self.comision_prc < 0 or self.comision_prc > 1:
                raise ValueError(f"Comisión debe estar entre 0 y 1: {self.comision_prc}")
            if self.slippage_prc < 0 or self.slippage_prc > 1:
                raise ValueError(f"Slippage debe estar entre 0 y 1: {self.slippage_prc}")

            # Variables para tracking de métricas del episodio actual
            self._equity_maximo_episodio: float = 0.0
            self._operaciones_episodio: int = 0
            self._pnl_total_episodio: float = 0.0
            
            # Generador de IDs únicos para trades (persiste entre episodios)
            self._next_trade_id: int = 1
            
            # Variables de estado
            self._balance: float = 0.0
            self._posicion_abierta: Optional[Posicion] = None
            
            self.reset()
            
        except Exception as e:
            log.error(f"Error crítico al inicializar portafolio: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def reset(self) -> None:
        """Reinicia el portafolio para un nuevo episodio."""
        
        try:
            # Propiedades del portafolio
            self._balance = self.balance_inicial # Es el dinero líquido disponible
            self._posicion_abierta = None  # Instancia de la clase Posición o None si no hay posición abierta
            
            # Reset de métricas del episodio
            self._equity_maximo_episodio = self.balance_inicial
            self._operaciones_episodio = 0
            self._pnl_total_episodio = 0.0
            
        except Exception as e:
            log.error(f"Error al reiniciar portafolio: {e}")
            raise
    
    def abrir_posicion(self, tipo: str, precio: float, porcentaje_inversion: float) -> Tuple[bool, Dict[str, Any]]:
        """Abre una nueva posición si hay suficiente margen."""
        
        try:
            # Validar parámetros
            if tipo not in ['long', 'short']:
                raise ValueError(f"Tipo de posición inválido: {tipo}")
            if precio <= 0:
                raise ValueError(f"Precio inválido: {precio}")
            if porcentaje_inversion <= 0 or porcentaje_inversion > 1:
                raise ValueError(f"Porcentaje de inversión inválido: {porcentaje_inversion}")
            
            if self._posicion_abierta is not None:
                log.warning("Ya existe una posición abierta")
                return False, {'error': 'posicion_ya_existe'}

            # 1. Calcular la cantidad a invertir
            cantidad: float = self._calcular_cantidad_invertir(precio, porcentaje_inversion)

            # 2. Calcular el margen requerido para la operación (la "fianza")
            margen_inmediato: float = self._calcular_margen(precio, cantidad)
            
            # 3. Calcular los costos de transacción
            comision: float
            slippage: float
            comision, slippage = self._calcular_comision_slippage(precio, cantidad)

            # 4. Calcular el costo total real para abrir la posición
            costo_total_apertura: float = margen_inmediato + comision + slippage

            # 5. Verificar si el balance líquido es suficiente para cubrir el costo
            if self._balance < costo_total_apertura:
                log.warning(f"Capital insuficiente: disponible={self._balance}, requerido={costo_total_apertura}")
                return False, {
                    'error': 'insuficiente_capital', 
                    'balance_disponible': self._balance, 
                    'costo_requerido': costo_total_apertura
                }

            # 6. Crear la posición con ID único
            trade_id: int = self._next_trade_id
            self._next_trade_id += 1
            
            self._posicion_abierta = Posicion(
                tipo=tipo, precio=precio, cantidad=cantidad, fecha=pd.Timestamp.now(), velas=0,
                comision=comision, slippage=slippage, margen=margen_inmediato, porcentaje_inv=porcentaje_inversion,
                trade_id=trade_id
            )

            # 7. Actualizar el balance restando ÚNICAMENTE el costo de apertura
            self._balance -= costo_total_apertura

            # 8. Información esencial de la operación
            apertura_info: Dict[str, Any] = {
                'tipo_operacion': 'apertura_posicion',
                'trade_id': trade_id,
                'tipo_posicion': tipo,
                'precio_entrada': precio,
                'cantidad': cantidad,
                'porcentaje_inversion': porcentaje_inversion
            }

            return True, apertura_info
            
        except Exception as e:
            log.error(f"Error al abrir posición {tipo}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise
    
    def modificar_posicion(self, precio: float, porcentaje_inversion: float) -> Tuple[bool, Dict[str, Any]]:
        """Modifica la posición abierta, ya sea aumentando o reduciendo."""
        
        try:
            # Si no hay posición abierta, no se puede modificar
            if self._posicion_abierta is None:
                log.warning("No hay posición abierta para modificar")
                return False, {'error': 'no_hay_posicion'}
            
            if precio <= 0:
                raise ValueError(f"Precio inválido: {precio}")
            if porcentaje_inversion <= 0 or porcentaje_inversion > 1:
                raise ValueError(f"Porcentaje de inversión inválido: {porcentaje_inversion}")
            
            porcentaje_inv_actual: float = self._posicion_abierta.porcentaje_inv

            if porcentaje_inversion > porcentaje_inv_actual:
                # Aumentar posición
                incremento: float = porcentaje_inversion - porcentaje_inv_actual
                success, info = self._aumentar_posicion(precio, incremento)
                return success, info
            elif porcentaje_inversion < porcentaje_inv_actual:
                # Reducir posición
                reduccion: float = porcentaje_inv_actual - porcentaje_inversion
                return self._reducir_posicion(precio, reduccion)
            else:
                # No hay cambio en el porcentaje de inversión
                return False, {'info': 'sin_cambios'}
                
        except Exception as e:
            log.error(f"Error al modificar posición: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _aumentar_posicion(self, precio: float, porcentaje_inversion_adicional: float) -> Tuple[bool, Dict[str, Any]]:
        """Añade capital a una posición existente, promediando el precio."""
        
        try:
            # EL porcentaje debe ser el incremento, no el total
            if self._posicion_abierta is None or porcentaje_inversion_adicional <= 0:
                return False, {'error': 'parametros_invalidos'}

            # --- Cálculos para la parte adicional ---
            cantidad_adicional: float = self._calcular_cantidad_invertir(precio, porcentaje_inversion_adicional)
            
            margen_adicional: float = self._calcular_margen(precio, cantidad_adicional)
            comision_adicional: float
            slippage_adicional: float
            comision_adicional, slippage_adicional = self._calcular_comision_slippage(precio, cantidad_adicional)

            # --- Verificación de balance ---
            # El costo real es solo el margen adicional y los costos de transacción
            costos_totales_adicionales: float = margen_adicional + comision_adicional + slippage_adicional
            
            # CORRECTO: Se comprueba si el balance puede cubrir el costo real
            if self._balance < costos_totales_adicionales:
                log.warning(f"Balance insuficiente para aumentar posición: disponible={self._balance}, requerido={costos_totales_adicionales}")
                return False, {
                    'error': 'insuficiente_balance', 
                    'balance_disponible': self._balance, 
                    'costo_requerido': costos_totales_adicionales
                }

            # --- Actualización del estado del portafolio ---
            # 1. Actualizar balance
            # CORRECTO: Se resta únicamente el costo real
            self._balance -= costos_totales_adicionales

            # 2. Actualizar los atributos de la posición
            nueva_cantidad: float = self._posicion_abierta.cantidad + cantidad_adicional
            nuevo_precio_promedio: float = ((self._posicion_abierta.precio * self._posicion_abierta.cantidad) + 
                                             (precio * cantidad_adicional)) / nueva_cantidad
            
            self._posicion_abierta.precio = nuevo_precio_promedio
            self._posicion_abierta.cantidad = nueva_cantidad
            self._posicion_abierta.margen += margen_adicional
            self._posicion_abierta.comision += comision_adicional
            self._posicion_abierta.slippage += slippage_adicional
            self._posicion_abierta.porcentaje_inv += porcentaje_inversion_adicional
            
            # Información esencial del aumento
            aumento_info: Dict[str, Any] = {
                'tipo_operacion': 'aumento_posicion',
                'trade_id': self._posicion_abierta.trade_id,
                'precio_nuevo': precio,
                'cantidad_adicional': cantidad_adicional,
                'cantidad_total': nueva_cantidad,
                'precio_promedio': nuevo_precio_promedio
            }
            
            return True, aumento_info
            
        except Exception as e:
            log.error(f"Error al aumentar posición: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _reducir_posicion(self, precio: float, porcentaje_a_reducir: float) -> Tuple[bool, Dict[str, Any]]:
        """
        Reduce una parte de la posición, realizando el PnL parcial.
        El porcentaje a reducir se basa en el equity, de forma simétrica a _aumentar_posicion.
        """
        
        try:
            if self._posicion_abierta is None or porcentaje_a_reducir <= 0:
                return False, {'error': 'parametros_invalidos'}
            
            # --- Cálculos para la parte a reducir ---
            cantidad_a_reducir: float = self._calcular_cantidad_invertir(precio, porcentaje_a_reducir)

            # Si la cantidad a reducir es mayor o igual a la posición actual, se cierra por completo.
            if cantidad_a_reducir >= self._posicion_abierta.cantidad:
                success, pnl, info = self.cerrar_posicion(precio)
                return success, info

            # Calcular PnL realizado para la parte que se cierra
            pnl_parcial_realizado: float = (self._posicion_abierta.tipo * 
                                           (precio - self._posicion_abierta.precio) * cantidad_a_reducir)
            
            # Calcular margen a liberar
            margen_liberado: float = self._calcular_margen(self._posicion_abierta.precio, cantidad_a_reducir)
            comision_reduccion: float
            slippage_reduccion: float
            comision_reduccion, slippage_reduccion = self._calcular_comision_slippage(precio, cantidad_a_reducir)

            # Información esencial de la reducción
            reduccion_info: Dict[str, Any] = {
                'tipo_operacion': 'reduccion_parcial',
                'trade_id': self._posicion_abierta.trade_id,
                'precio_salida': precio,
                'cantidad_reducida': cantidad_a_reducir,
                'cantidad_restante': self._posicion_abierta.cantidad - cantidad_a_reducir,
                'pnl_parcial': pnl_parcial_realizado
            }

            # Actualizar métricas
            self._operaciones_episodio += 1
            self._pnl_total_episodio += pnl_parcial_realizado

            # --- Actualización del estado del portafolio ---
            self._balance += pnl_parcial_realizado + margen_liberado - (comision_reduccion + slippage_reduccion)

            # Actualizar los atributos de la posición
            self._posicion_abierta.cantidad -= cantidad_a_reducir
            self._posicion_abierta.margen -= margen_liberado
            self._posicion_abierta.comision += comision_reduccion
            self._posicion_abierta.slippage += slippage_reduccion
            self._posicion_abierta.porcentaje_inv -= porcentaje_a_reducir

            return True, reduccion_info
            
        except Exception as e:
            log.error(f"Error al reducir posición: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def cerrar_posicion(self, precio_cierre: float) -> Tuple[bool, float, Dict[str, Any]]:
        """Cierra la posición más antigua abierta y retorna información de la operación."""
        
        try:
            if self._posicion_abierta is None:
                log.warning("No hay posición abierta para cerrar")
                return False, 0.0, {'error': 'no_hay_posicion'}
            
            if precio_cierre <= 0:
                raise ValueError(f"Precio de cierre inválido: {precio_cierre}")
            
            # 1. Calcular el PnL realizado
            PnL_realizado: float = self.calcular_PnL_no_realizado(precio_cierre)

            # 2. Guardar información antes de cerrar la posición
            margen_a_liberar: float = self._posicion_abierta.margen
            trade_id: int = self._posicion_abierta.trade_id
            tipo_posicion: str = 'long' if self._posicion_abierta.tipo == 1 else 'short'
            precio_entrada: float = self._posicion_abierta.precio
            cantidad: float = self._posicion_abierta.cantidad
            velas_abiertas: int = self._posicion_abierta.velas

            # 3. Información esencial del cierre
            operacion_info: Dict[str, Any] = {
                'tipo_operacion': 'cierre_completo',
                'trade_id': trade_id,
                'tipo_posicion': tipo_posicion,
                'precio_entrada': precio_entrada,
                'precio_salida': precio_cierre,
                'cantidad': cantidad,
                'velas_abiertas': velas_abiertas,
                'pnl_realizado': PnL_realizado
            }

            # 4. Actualizar métricas del episodio
            self._operaciones_episodio += 1
            self._pnl_total_episodio += PnL_realizado

            # 5. Cerrar posición
            self._posicion_abierta = None

            # 6. Actualizar balance
            self._balance += PnL_realizado + margen_a_liberar

            return True, PnL_realizado, operacion_info
            
        except Exception as e:
            log.error(f"Error al cerrar posición: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _calcular_margen(self, precio: float, cantidad: float) -> float:
        """Calcula el margen requerido para abrir una posición."""
        try:
            if precio <= 0 or cantidad <= 0:
                raise ValueError(f"Precio y cantidad deben ser positivos: precio={precio}, cantidad={cantidad}")
            
            margen: float = (precio * cantidad) / self.apalancamiento
            return margen
            
        except Exception as e:
            log.error(f"Error al calcular margen: {e}")
            raise
    
    def _calcular_comision_slippage(self, precio: float, cantidad: float) -> Tuple[float, float]:
        """Calcula la comisión y el slippage de una operación"""
        try:
            if precio <= 0 or cantidad <= 0:
                raise ValueError(f"Precio y cantidad deben ser positivos: precio={precio}, cantidad={cantidad}")
                
            comision: float = precio * cantidad * self.comision_prc
            slippage: float = precio * cantidad * self.slippage_prc
            return comision, slippage
            
        except Exception as e:
            log.error(f"Error al calcular comisión y slippage: {e}")
            raise
    
    def _calcular_cantidad_invertir(self, precio: float, porcentaje_inversion: float) -> float:
        """Calcula la cantidad a invertir basada en un porcentaje del balance y el tipo de operación."""
        try:
            if precio <= 0:
                raise ValueError(f"Precio inválido: {precio}")
            if porcentaje_inversion <= 0 or porcentaje_inversion > 1:
                raise ValueError(f"Porcentaje de inversión inválido: {porcentaje_inversion}")
                
            equity_actual: float = self.get_equity(precio)
            cantidad: float = (equity_actual * self.apalancamiento * porcentaje_inversion) / precio
            
            if cantidad <= 0:
                raise ValueError(f"Cantidad calculada inválida: {cantidad}")
                
            return cantidad
            
        except Exception as e:
            log.error(f"Error al calcular cantidad a invertir: {e}")
            raise
    
    def calcular_PnL_no_realizado(self, precio_actual: float) -> float:
        """Calcula el PnL no realizado de una operación."""
        try:
            if self._posicion_abierta is None:
                return 0.0  # No hay posición abierta, PnL no realizado es 0

            if precio_actual <= 0:
                raise ValueError(f"Precio actual inválido: {precio_actual}")

            # Extraer los datos de la posición abierta
            precio_entrada: float = self._posicion_abierta.precio
            cantidad: float = self._posicion_abierta.cantidad
            direccion: int = self._posicion_abierta.tipo  # 1 para long, -1 para short

            # Calcular el PnL no realizado
            PnL_no_realizado: float = (precio_actual - precio_entrada) * cantidad * direccion
            return PnL_no_realizado
            
        except Exception as e:
            log.error(f"Error al calcular PnL no realizado: {e}")
            raise
    
    def calcular_max_drawdown(self, precio_actual: float) -> float:
        """Calcula el max drawdown actual del episodio."""
        try:
            if precio_actual <= 0:
                raise ValueError(f"Precio actual inválido: {precio_actual}")
                
            equity_actual: float = self.get_equity(precio_actual)
            
            # Actualizar el equity máximo del episodio si corresponde
            if equity_actual > self._equity_maximo_episodio:
                self._equity_maximo_episodio = equity_actual
            
            # Calcular drawdown
            if self._equity_maximo_episodio == 0:
                return 0.0
            
            drawdown: float = (self._equity_maximo_episodio - equity_actual) / self._equity_maximo_episodio
            return max(0.0, drawdown)  # Asegurar que no sea negativo
            
        except Exception as e:
            log.error(f"Error al calcular max drawdown: {e}")
            raise
    
    def get_info_portafolio(self, precio_actual: float) -> Dict[str, Any]:
        """Información esencial del portafolio para reconstrucción."""
        try:
            if precio_actual <= 0:
                raise ValueError(f"Precio actual inválido: {precio_actual}")
                
            info: Dict[str, Any] = {
                'balance': self._balance,
                'equity': self.get_equity(precio_actual),
                'max_drawdown': self.calcular_max_drawdown(precio_actual),
                'operaciones_total': self._operaciones_episodio,
                'pnl_total': self._pnl_total_episodio,
                'posicion_abierta': self._posicion_abierta is not None
            }
            
            if self._posicion_abierta is not None:
                info.update({
                    'trade_id_activo': self._posicion_abierta.trade_id,
                    'tipo_posicion_activa': 'long' if self._posicion_abierta.tipo == 1 else 'short',
                    'precio_entrada_activa': self._posicion_abierta.precio,
                    'cantidad_activa': self._posicion_abierta.cantidad,
                    'velas_activa': self._posicion_abierta.velas,
                    'pnl_no_realizado': self.calcular_PnL_no_realizado(precio_actual)
                })
            
            return info
            
        except Exception as e:
            log.error(f"Error al obtener información del portafolio: {e}")
            raise

    def get_equity(self, precio_actual: float) -> float:
        """
        Calcula y devuelve el valor total del portafolio (equity) en tiempo real.
        Equity = Balance Líquido + Margen en Uso + PnL No Realizado.
        """
        try:
            if precio_actual <= 0:
                raise ValueError(f"Precio actual inválido: {precio_actual}")
                
            if self._posicion_abierta is None:
                # Si no hay posición, el equity es simplemente el balance.
                return self._balance

            # Si hay una posición abierta:
            pnl_no_realizado: float = self.calcular_PnL_no_realizado(precio_actual)
            margen_en_uso: float = self._posicion_abierta.margen
            
            equity: float = self._balance + margen_en_uso + pnl_no_realizado
            return equity
            
        except Exception as e:
            log.error(f"Error al calcular equity: {e}")
            raise
    
    def conteovelas(self) -> None:
        """ Aumenta el contador del número de velas que lleva abierta una operación"""
        try:
            if self._posicion_abierta is not None:
                self._posicion_abierta.velas += 1
                
        except Exception as e:
            log.error(f"Error al contar velas: {e}")
            raise

    @property
    def posicion_abierta(self) -> Optional[Posicion]:
        return self._posicion_abierta