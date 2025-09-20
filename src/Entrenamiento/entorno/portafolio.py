""" Simulador de un portafolio de inversiones.

En este script nos encontramos con la clase Portafolio, que gestiona
las operaciones de trading, el balance, el equity y el historial de
operaciones. También incluye la clase Posicion para modelar una
operación abierta.
"""
import pandas as pd
from src.Entrenamiento.config import Config 
from typing import Tuple

class Posicion:
    def __init__(self, tipo: str, precio: float, cantidad: float, fecha: pd.Timestamp, velas: int, comision: float, slippage:float, margen: float, porcentaje_inv: float)-> None:
        if tipo not in ['long', 'short']:
            raise ValueError("El tipo de posición debe ser 'long' o 'short'")
        
        self._tipo = tipo  # 'long' o 'short'
        self._precio = precio
        self._cantidad = cantidad
        self._fecha = fecha
        self._velas = velas
        self._comision = comision
        self._slippage = slippage
        self._margen = margen
        self._porcentaje_inv = porcentaje_inv
    
    @property
    def tipo(self):
        return 1 if self._tipo == 'long' else -1
    @property
    def porcentaje_inv(self):
        return self._porcentaje_inv
    @porcentaje_inv.setter
    def porcentaje_inv(self, valor: float)-> None:
        self._porcentaje_inv = valor
    @property
    def precio(self):
        return self._precio
    @precio.setter
    def precio(self, valor: float)-> None:
        self._precio = valor
    @property
    def cantidad(self):
        return self._cantidad
    @cantidad.setter
    def cantidad(self, valor: float)-> None:
        self._cantidad = valor
    @property
    def fecha(self):
        return self._fecha
    @property
    def velas(self):
        return self._velas
    @velas.setter
    def velas(self, valor: int) -> None:
        self._velas = valor
    @property
    def comision(self):
        return self._comision
    @comision.setter
    def comision(self, valor: float)-> None:
        self._comision = valor
    @property
    def slippage(self):
        return self._slippage
    @slippage.setter
    def slippage(self, valor: float)-> None:
        self._slippage = valor
    @property
    def margen(self):
        return self._margen
    @margen.setter
    def margen(self, valor: float)-> None:
        self._margen = valor
    
class Portafolio:
    def __init__(self, config: Config) -> None:
        # Variables de configuración
        self.balance_inicial = config.portafolio.capital_inicial
        self.comision_prc = config.portafolio.comision
        self.slippage_prc = config.portafolio.slippage
        self.apalancamiento = config.portafolio.apalancamiento

        # Variables para tracking de métricas del episodio actual
        self._equity_maximo_episodio = 0.0
        self._operaciones_episodio = 0
        self._pnl_total_episodio = 0.0
        
        self.reset()

    def reset(self):
        # Propiedades del portafolio
        self._balance = self.balance_inicial # Es el dinero líquido disponible
        self._posicion_abierta = None  # Instancia de la clase Posición o None si no hay posición abierta
        
        # Reset de métricas del episodio
        self._equity_maximo_episodio = self.balance_inicial
        self._operaciones_episodio = 0
        self._pnl_total_episodio = 0.0
    
    def abrir_posicion(self, tipo: str, precio: float, porcentaje_inversion: float) -> bool:
        """Abre una nueva posición si hay suficiente margen."""
        # 1. Calcular la cantidad a invertir
        cantidad = self._calcular_cantidad_invertir(precio, porcentaje_inversion)

        # 2. Calcular el margen requerido para la operación (la "fianza")
        margen_inmediato = self._calcular_margen(precio, cantidad)
        
        # 3. Calcular los costos de transacción
        comision, slippage = self._calcular_comision_slippage(precio, cantidad)

        # 4. Calcular el costo total real para abrir la posición
        costo_total_apertura = margen_inmediato + comision + slippage

        # 5. Verificar si el balance líquido es suficiente para cubrir el costo
        if self._balance < costo_total_apertura:
            return False # No hay suficiente capital líquido

        # 6. Crear la posición
        self._posicion_abierta = Posicion(
            tipo=tipo, precio=precio, cantidad=cantidad, fecha=pd.Timestamp.now(), velas = 0,
            comision=comision, slippage=slippage, margen=margen_inmediato, porcentaje_inv=porcentaje_inversion
        )

        # 7. Actualizar el balance restando ÚNICAMENTE el costo de apertura
        self._balance -= costo_total_apertura

        return True
    
    def modificar_posicion(self, precio: float, porcentaje_inversion: float) -> Tuple[bool, dict]:
        """Modifica la posición abierta, ya sea aumentando o reduciendo."""
        # Si no hay posición abierta, no se puede modificar
        if self._posicion_abierta is None:
            return False, {}
        
        porcentaje_inv_actual = self._posicion_abierta.porcentaje_inv

        if porcentaje_inversion > porcentaje_inv_actual:
            # Aumentar posición
            incremento = porcentaje_inversion - porcentaje_inv_actual
            success = self._aumentar_posicion(precio, incremento)
            info = {'tipo_operacion': 'aumento_posicion', 'incremento': incremento} if success else {}
            return success, info
        elif porcentaje_inversion < porcentaje_inv_actual:
            # Reducir posición
            reduccion = porcentaje_inv_actual - porcentaje_inversion
            return self._reducir_posicion(precio, reduccion)
        else:
            # No hay cambio en el porcentaje de inversión
            return False, {}

    def _aumentar_posicion(self, precio: float, porcentaje_inversion_adicional: float) -> bool:
        """Añade capital a una posición existente, promediando el precio."""
        # EL porcentaje debe ser el incremento, no el total
        if self._posicion_abierta is None or porcentaje_inversion_adicional <= 0:
            return False

        # --- Cálculos para la parte adicional ---
        cantidad_adicional = self._calcular_cantidad_invertir(precio, porcentaje_inversion_adicional)
        
        margen_adicional = self._calcular_margen(precio, cantidad_adicional)
        comision_adicional, slippage_adicional = self._calcular_comision_slippage(precio, cantidad_adicional)

        # --- Verificación de balance ---
        # El costo real es solo el margen adicional y los costos de transacción
        costos_totales_adicionales = margen_adicional + comision_adicional + slippage_adicional
        
        # CORRECTO: Se comprueba si el balance puede cubrir el costo real
        if self._balance < costos_totales_adicionales:
            return False  # No hay suficiente balance

        # --- Actualización del estado del portafolio ---
        # 1. Actualizar balance
        # CORRECTO: Se resta únicamente el costo real
        self._balance -= costos_totales_adicionales

        # 2. Actualizar los atributos de la posición
        nueva_cantidad = self._posicion_abierta.cantidad + cantidad_adicional
        nuevo_precio_promedio = ((self._posicion_abierta.precio * self._posicion_abierta.cantidad) + 
                                 (precio * cantidad_adicional)) / nueva_cantidad
        
        self._posicion_abierta.precio = nuevo_precio_promedio
        self._posicion_abierta.cantidad = nueva_cantidad
        self._posicion_abierta.margen += margen_adicional
        self._posicion_abierta.comision += comision_adicional
        self._posicion_abierta.slippage += slippage_adicional
        self._posicion_abierta.porcentaje_inv += porcentaje_inversion_adicional
        
        return True

    def _reducir_posicion(self, precio: float, porcentaje_a_reducir: float) -> Tuple[bool, dict]:
        """
        Reduce una parte de la posición, realizando el PnL parcial.
        El porcentaje a reducir se basa en el equity, de forma simétrica a _aumentar_posicion.
        """
        if self._posicion_abierta is None or porcentaje_a_reducir <= 0:
            return False, {}
        
        # --- Cálculos para la parte a reducir ---
        cantidad_a_reducir = self._calcular_cantidad_invertir(precio, porcentaje_a_reducir)

        # Si la cantidad a reducir es mayor o igual a la posición actual, se cierra por completo.
        if cantidad_a_reducir >= self._posicion_abierta.cantidad:
            success, pnl, info = self.cerrar_posicion(precio)
            return success, info

        # Calcular PnL realizado para la parte que se cierra
        pnl_parcial_realizado = (self._posicion_abierta.tipo * (precio - self._posicion_abierta.precio) * cantidad_a_reducir)
        
        # Calcular margen a liberar
        margen_liberado = self._calcular_margen(self._posicion_abierta.precio, cantidad_a_reducir)
        comision_reduccion, slippage_reduccion = self._calcular_comision_slippage(precio, cantidad_a_reducir)

        # Crear información de la reducción
        reduccion_info = {
            'tipo_operacion': 'reduccion_parcial',
            'tipo_posicion': 'long' if self._posicion_abierta.tipo == 1 else 'short',
            'precio_entrada': self._posicion_abierta.precio,
            'precio_salida': precio,
            'cantidad_reducida': cantidad_a_reducir,
            'cantidad_restante': self._posicion_abierta.cantidad - cantidad_a_reducir,
            'pnl_parcial': pnl_parcial_realizado,
            'comision_reduccion': comision_reduccion,
            'slippage_reduccion': slippage_reduccion,
            'margen_liberado': margen_liberado
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

    def cerrar_posicion(self, precio_cierre: float) -> Tuple[bool, float, dict]:
        """Cierra la posición más antigua abierta y retorna información de la operación."""
        if self._posicion_abierta is None:
            return False, 0.0, {}
        
        # 1. Calcular el PnL realizado
        PnL_realizado = self.calcular_PnL_no_realizado(precio_cierre)

        # 2. Crear información de la operación para el info
        operacion_info = {
            'tipo_operacion': 'cierre_completo',
            'tipo_posicion': 'long' if self._posicion_abierta.tipo == 1 else 'short',
            'precio_entrada': self._posicion_abierta.precio,
            'precio_salida': precio_cierre,
            'cantidad': self._posicion_abierta.cantidad,
            'velas_abiertas': self._posicion_abierta.velas,
            'pnl_realizado': PnL_realizado,
            'comision_total': self._posicion_abierta.comision,
            'slippage_total': self._posicion_abierta.slippage,
            'margen_usado': self._posicion_abierta.margen,
            'fecha_apertura': self._posicion_abierta.fecha
        }

        # 3. Actualizar métricas del episodio
        self._operaciones_episodio += 1
        self._pnl_total_episodio += PnL_realizado

        # 4. Guardar margen a liberar y cerrar posición
        margen_a_liberar = self._posicion_abierta.margen
        self._posicion_abierta = None

        # 5. Actualizar balance
        self._balance += PnL_realizado + margen_a_liberar

        return True, PnL_realizado, operacion_info

    def _calcular_margen(self, precio: float, cantidad: float) -> float:
        """Calcula el margen requerido para abrir una posición."""
        return (precio * cantidad) / self.apalancamiento
    
    def _calcular_comision_slippage(self, precio: float, cantidad: float) -> tuple:
        """Calcula la comisión y el slippage de una operación"""
        comision = precio * cantidad * self.comision_prc
        slippage = precio * cantidad * self.slippage_prc
        return comision, slippage
    
    def _calcular_cantidad_invertir(self, precio: float, porcentaje_inversion: float) -> float:
        """Calcula la cantidad a invertir basada en un porcentaje del balance y el tipo de operación."""
        equity_actual = self.get_equity(precio)

        return (equity_actual * self.apalancamiento * porcentaje_inversion) / precio
    
    def calcular_PnL_no_realizado(self, precio_actual: float) -> float:
        """Calcula el PnL no realizado de una operación."""
        if self._posicion_abierta is None:
            return 0.0  # No hay posición abierta, PnL no realizado es 0

        # Extraer los datos de la posición abierta
        precio_entrada = self._posicion_abierta.precio
        cantidad = self._posicion_abierta.cantidad
        direccion = self._posicion_abierta.tipo  # 1 para long, -1 para short

        # Calcular el PnL no realizado
        PnL_no_realizado = (precio_actual - precio_entrada) * cantidad * direccion
        return PnL_no_realizado
    
    def calcular_max_drawdown(self, precio_actual: float) -> float:
        """Calcula el max drawdown actual del episodio."""
        equity_actual = self.get_equity(precio_actual)
        
        # Actualizar el equity máximo del episodio si corresponde
        if equity_actual > self._equity_maximo_episodio:
            self._equity_maximo_episodio = equity_actual
        
        # Calcular drawdown
        if self._equity_maximo_episodio == 0:
            return 0.0
        
        return (self._equity_maximo_episodio - equity_actual) / self._equity_maximo_episodio
    
    def get_info_portafolio(self, precio_actual: float) -> dict:
        """Obtiene información completa del estado actual del portafolio para el info de gymnasium."""
        equity_actual = self.get_equity(precio_actual)
        max_drawdown = self.calcular_max_drawdown(precio_actual)
        
        info = {
            'balance': self._balance,
            'equity': equity_actual,
            'max_drawdown': max_drawdown,
            'equity_maximo_episodio': self._equity_maximo_episodio,
            'operaciones_episodio': self._operaciones_episodio,
            'pnl_total_episodio': self._pnl_total_episodio,
            'posicion_abierta': self._posicion_abierta is not None,
        }
        
        if self._posicion_abierta is not None:
            info.update({
                'tipo_posicion': 'long' if self._posicion_abierta.tipo == 1 else 'short',
                'precio_entrada_posicion': self._posicion_abierta.precio,
                'cantidad_posicion': self._posicion_abierta.cantidad,
                'velas_posicion_abierta': self._posicion_abierta.velas,
                'pnl_no_realizado': self.calcular_PnL_no_realizado(precio_actual),
                'margen_usado': self._posicion_abierta.margen,
                'porcentaje_inversion': self._posicion_abierta.porcentaje_inv
            })
        
        return info

    def get_equity(self, precio_actual: float) -> float:
        """
        Calcula y devuelve el valor total del portafolio (equity) en tiempo real.
        Equity = Balance Líquido + Margen en Uso + PnL No Realizado.
        """
        if self._posicion_abierta is None:
            # Si no hay posición, el equity es simplemente el balance.
            return self._balance

        # Si hay una posición abierta:
        pnl_no_realizado = self.calcular_PnL_no_realizado(precio_actual)
        margen_en_uso = self._posicion_abierta.margen
        
        return self._balance + margen_en_uso + pnl_no_realizado
    
    def conteovelas(self) -> None:
        """ Aumenta el contador del núnmero de velas que lleva abierta una operación"""
        if self._posicion_abierta is not None:
            self._posicion_abierta.velas += 1
    


    @property
    def posicion_abierta(self):
        return self._posicion_abierta