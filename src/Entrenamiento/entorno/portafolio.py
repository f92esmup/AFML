""" Simulador de un portafolio de inversiones"""
import pandas as pd
from src.Entrenamiento.config import Config 
from typing import Tuple

class Posicion:
    def __init__(self, tipo: str, precio: float, cantidad: float, fecha, comision: float, slippage:float, margen: float)-> None:
        if tipo not in ['long', 'short']:
            raise ValueError("El tipo de posición debe ser 'long' o 'short'")
        
        self._tipo = tipo  # 'long' o 'short'
        self._precio = precio
        self._cantidad = cantidad
        self._fecha = fecha
        self._PnL_no_realizado = 0
        # COmprobar si el stoploss es adecuado.
        self._comision = comision
        self._slippage = slippage
        self._margen = margen
    
    @property
    def tipo(self):
        mapeo = {
            'long': 1,
            'short': -1
        }
        return mapeo.get(self._tipo, 0)  # Devuelve 0 si el tipo no está en el diccionario
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
    @property
    def PnL_no_realizado(self):
        return self._PnL_no_realizado
    @PnL_no_realizado.setter
    def PnL_no_realizado(self, valor: float)-> None:
        self._PnL_no_realizado = valor
    
# HAY ALGO QUE NO ESTOY TENIENDO EN CUENTA. YO LAS POSICOINES LAS ACTUALIZO CON RECOMPRAR,PROMEDIANDO EL PRECIO POR LO QUE EN LA PRACTICA SIIMRPE HAY UNA ÚNICA POSICIÓN ABIERTA
class Portafolio:
    def __init__(self, config: Config) -> None:
        # Variables de configuración
        self.balance_inicial = config.portafolio.capital_inicial
        self.comision_prc = config.portafolio.comision
        self.slippage_prc = config.portafolio.slippage
        self.porcentaje_margen_requerido = config.portafolio.margen_minimo
        self.apalancamiento = config.portafolio.apalancamiento

        self._historial_ordenes = pd.DataFrame(columns=['fecha', 'tipo', 'precio_entrada', 'precio_salida', 'PnL_realizado', 'comision', 'slippage', 'margen', 'episodio'])  # Lista de diccionarios

        self.reset()

    def reset(self):
                # Propiedades del portafolio
        self._balance = self.balance_inicial # Es el dinero líquido disponible
        self._equity = self.balance_inicial # Es el valor total del portafolio (balance + PnL no realizado)
        self._posicion_abierta = None  # Instancia de la clase Posición o None si no hay posición abierta
    
    def abrir_posición(self, tipo: str, precio: float, porcentaje_inversion: float) -> bool:
        """Abre una nueva posición si hay suficiente margen."""
        # Calcular la cantidad a invertir
        cantidad = self._calcular_cantidad_invertir(precio, porcentaje_inversion)

        # Calcular el margen inmediato
        margen_inmediato = self._calcular_margen(precio, cantidad, self.porcentaje_margen_requerido)
        
        # Calcular la comisión y el slippage
        comision, slippage = self._calcular_comision_slippage(precio, cantidad)

        # Balance actualizado tras abrir la posición
        balance_actualizado = self._balance - (margen_inmediato + comision + slippage) - cantidad * precio
        # Confirmar que el margen total es menor que el balance
        if balance_actualizado < 0:
            return False

        # Crear la posición
        self._posicion_abierta = Posicion(
            tipo=tipo, precio=precio, cantidad=cantidad, fecha=pd.Timestamp.now(),
            comision=comision, slippage=slippage, margen=margen_inmediato
        )

        # Actualizar el balance
        self._balance = balance_actualizado

        return True
    
    def modificar_posicion(self, precio: float, porcentaje_inversion: float) -> bool:
        """Modifica la posición existente añadiendo o reduciendo la cantidad."""
        if self._posicion_abierta is None:
            return False  # No hay posición abierta para modificar.
        

        return True
    
    def cerrar_posicion(self, precio_cierre: float, episodio: int) -> Tuple[bool, float]:
        """Cierra la posición más antigua abierta."""
        if self._posicion_abierta is None:
            return False, 0.0  # No hay posición abierta para cerrar.
        
        # Calcular el PnL realizado
        PnL_realizado = self._calcular_PnL_no_realizado(precio_cierre)

        # Registrar la orden en el historial
        self._registrar_orden_en_historial(precio_cierre, PnL_realizado, episodio)

        # Actualizar el balance
        self._balance += PnL_realizado + self._posicion_abierta.margen

        # Cerrar la posición
        self._posicion_abierta = None

        return True, PnL_realizado
    
    def _calcular_margen(self, precio: float, cantidad: float, porcentaje_margen_requerido: float) -> float:
        """Calcula el margen requerido para abrir una posición."""
        return (precio * cantidad * porcentaje_margen_requerido) / self.apalancamiento
    
    def _calcular_comision_slippage(self, precio: float, cantidad: float) -> tuple:
        """Calcula la comisión y el slippage de una operación"""
        comision = precio * cantidad * self.comision_prc
        slippage = precio * cantidad * self.slippage_prc
        return comision, slippage
    
    def _calcular_cantidad_invertir(self, precio: float, porcentaje_inversion: float) -> float:
        """Calcula la cantidad a invertir basada en un porcentaje del balance y el tipo de operación."""
        return (self.balance * self.apalancamiento * porcentaje_inversion) / precio
    
    def _calcular_PnL_no_realizado(self, precio_actual: float) -> float:
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
    
    def _calcular_max_drawdown(self) -> float:
        """Calcula el max drawdown actual del portafolio."""
        if self._historial_ordenes.empty:
            return 0.0  # No hay historial, no hay drawdown

        # Calcular el pico máximo de equity
        pico_maximo = self._historial_ordenes['equity'].max()

        return (pico_maximo - self.equity) / pico_maximo
    
    def _registrar_orden_en_historial(self, precio_cierre: float, PnL_realizado: float, episodio: int) -> None:
        """Registra una orden en el historial del portafolio."""
        if self._posicion_abierta is None:
            return

        nueva_fila = {
            'fecha': self._posicion_abierta.fecha,
            'tipo': self._posicion_abierta.tipo,
            'precio_entrada': self._posicion_abierta.precio,
            'precio_salida': precio_cierre,
            'PnL_realizado': PnL_realizado,
            'comision': self._posicion_abierta.comision,
            'slippage': self._posicion_abierta.slippage,
            'margen': self._posicion_abierta.margen,
            'episodio': episodio
        }
        # Añadir la nueva fila al DataFrame
        self._historial_ordenes = pd.concat([self._historial_ordenes, pd.DataFrame([nueva_fila])], ignore_index=True)

