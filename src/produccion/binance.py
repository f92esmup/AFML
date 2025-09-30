"""Se encarga de el enlace con Binance"""

from binance.client import client


class Binance:
    def __init__(self, cliente: client):
        """Inicialización de binance"""

        self.cliente = cliente
