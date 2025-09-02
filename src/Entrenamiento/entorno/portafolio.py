""" Simulador de un portafolio de inversiones"""
import pandas as pd

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
    @property
    def cantidad(self):
        return self._cantidad
    @property
    def fecha(self):
        return self._fecha
    @property
    def comision(self):
        return self._comision
    @property
    def slippage(self):
        return self._slippage
    @property
    def margen(self):
        return self._margen
    @property
    def PnL_no_realizado(self):
        return self._PnL_no_realizado
    @PnL_no_realizado.setter
    def PnL_no_realizado(self, valor: float)-> None:
        self._PnL_no_realizado = valor
    
# HAY ALGO QUE NO ESTOY TENIENDO EN CUENTA. YO LAS POSICOINES LAS ACTUALIZO CON RECOMPRAR,PROMEDIANDO EL PRECIO POR LO QUE EN LA PRACTICA SIEMRPE HAY UNA ÚNICA POSICIÓN ABIERTA
class Portafolio:
    def __init__(self, config):
        # Variables de configuración
        self.balance_inicial = 
        self.comision_prc = 
        self.slippage_prc = 
        self.porcentaje_margen_requerido = 
        self.apalancamiento = 
        self.reset()

    def reset(self):
                # Propiedades del portafolio
        self._balance = 0.0 # Es el dinero líquido disponible
        self._equity = 0.0 # Es el valor total del portafolio (balance + PnL no realizado)
        self._historial_ordenes = pd.DataFrame()  # Lista de diccionarios
        self._posicion_abierta = None  # Instancia de la clase Posición o None si no hay posición abierta

    @property
    def balance(self) -> float:
        return self._balance
    @property
    def equity(self) ->float:
        return 0.0
    @property
    def posicion_abierta(self):
        return self._posicion_abierta
    @property
    def historial_ordenes(self) -> pd.DataFrame:
        return self._historial_ordenes
    @historial_ordenes.setter
    def añadir_historial_ordenes(self):
    
        
    
    
    
    def abrir_posición(self, tipo: str, precio: float, porcentaje_inversion: float)-> bool:
        """ Abre una nueva posición si hay suficiente margen """
        # La cantidad debe estar previamente verificada. Para que no supere la cantidad de capital que tenemos disponible.
        # Esta función se usa cuando no esxiste ninguna posición abierta, por lo que se sobreentiende que el margen es cero.
        # 1. Calculamos la cantidad a invertir
        cantidad = self._calcular_cantidad_invertir(precio, porcentaje_inversion)

        # 2. Calculamos el margen inmediato de esta operación
        margen_inmediato = self._calcular_margen(precio, cantidad, self.porcentaje_margen_requerido)

        # 3. Confirmar que el margen total es menor que el balance
        if self.balance > margen_inmediato: 
            return False

        # 4. Caluclamos la comisión y el slippage
        comision, slippage = self._calcular_comision_slippage(precio, cantidad)

        # 5. Creamos la operación
        self._posicion_abierta = Posicion(tipo=tipo, precio=precio, cantidad=cantidad, fecha=pd.Timestamp.now(), comision=comision, slippage=slippage, margen=margen_inmediato)
        return True
    
    def modificar_posicion(self, cantidad: float, ) -> tuple[bool, float]:
        """modificar la posición existente."""
        if self.posicion_abierta is None:
            return False, 0.0
         
        
        return True, 0.0
    
    def cerrar_posicion(self, precio_cierre: float) -> bool:
        """Cierra la posición más antigua abierta."""
        return True
    
    def _calcular_margen(self, precio: float, cantidad: float, porcentaje_margen_requerido: float) -> float:
        """Calcula el margen requerido para abrir una posición."""
        return precio * cantidad * porcentaje_margen_requerido
    
    def _calcular_comision_slippage(self, precio: float, cantidad: float) -> tuple:
        """Calcula la comisión y el slippage de una operación"""
        comision = precio * cantidad * self.comision_prc
        slippage = precio * cantidad * self.slippage_prc
        return comision, slippage
    
    def _calcular_cantidad_invertir(self, precio: float, porcentaje_inversion: float) -> float:
        """calcula la cantidad a invertir basada en un porcentaje del balance"""
        return (self.balance * porcentaje_inversion) / precio
    
    def _calcular_PnL_no_realizado(self, precio_actual: float):
        """calcula el PnL no realizado de una operación"""
    
    def _calcular_max_drawdown(self) -> float:
        """Calcula el max drawdown actual del portafolio."""
        


