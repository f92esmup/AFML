"""Se encarga de el enlace con Binance"""

from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

# Creamos el logger
log = logging.getLogger("AFML.Binance")


class Binance:
    def __init__(self, cliente: Client):
        """Conexión con el endpoint de FUTUROS de Binance"""

        self.cliente = cliente

        # Variables contienen información de la cuenta
        self.balance: float = 0.0
        self.equity: float = 0.0

    def create_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        reduceonly: bool,
        type: str = "MARKET",
    ) -> dict:
        """Crea cualquier tipo de orden"""
        try:
            orden = self.cliente.futures_create_order(
                symbol=symbol,
                side=side,
                type=type,
                quantity=quantity,
                reduceOnly=reduceonly,
            )
        except BinanceAPIException as e:
            log.error(f"Error al crear la orden: {e}")
            raise e  # TENGO QUE CREAR UNA FUCIÓN DE PARADO DE EMERGENCIA SEGURA QUE SE LLAME EN ESTOS CASOS.

        return orden

    def get_account_info(self) -> bool:
        """Obtiene información de la cuenta"""

        # Hacemos la llamada a la API de Binance
        try:
            account_info = self.cliente.futures_account()
        except BinanceAPIException as e:
            log.error(f"Error al obtener la información de la cuenta: {e}")
            return False

        return True
