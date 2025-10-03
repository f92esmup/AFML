"""Se encarga de el enlace con Binance"""

from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any
import logging

from src.produccion.config.config import ProductionConfig

# Creamos el logger
log = logging.getLogger("AFML.Binance")


class BinanceConnector:
    """Clase responsable de la conexión y operaciones con la API de Binance Futures USDT-M"""

    def __init__(self, client: Client, config: ProductionConfig) -> None:
        """
        Inicializa el conector de Binance con configuración one-way para Futures USDT-M

        Args:
            client: Cliente de Binance ya configurado
            config: Objeto de configuración de producción
        """
        self._client = client
        self._config = config

        # Atributos privados para información de la cuenta
        self._balance: float = 0.0
        self._equity: float = 0.0
        self._pnl_total: float = 0.0
        self._posicion_abierta: bool = False

        # Configurar apalancamiento al inicializar
        self._setup_leverage()

    def _setup_leverage(self) -> None:
        """Configura el apalancamiento para el símbolo especificado"""
        try:
            self._client.futures_change_leverage(
                symbol=self._config.simbolo, leverage=int(self._config.apalancamiento)
            )
            log.info(
                f"Apalancamiento configurado a {self._config.apalancamiento}x para {self._config.simbolo}"
            )
        except BinanceAPIException as e:
            log.error(f"Error al configurar apalancamiento: {e}")
            raise e

    def create_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        reduce_only: bool = False,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Crea una orden genérica para Futures USDT-M con configuración one-way

        Args:
            symbol: Símbolo del par de trading (ej: 'BTCUSDT')
            side: Dirección de la orden ('BUY' o 'SELL')
            quantity: Cantidad a operar
            order_type: Tipo de orden ('MARKET', 'LIMIT', etc.)
            reduce_only: Si la orden es solo para reducir posición
            time_in_force: Tiempo de vigencia de la orden

        Returns:
            Diccionario con la respuesta de la API de Binance

        Raises:
            BinanceAPIException: Error en la API de Binance
        """
        try:
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "reduceOnly": reduce_only,
            }

            # Solo agregar timeInForce para órdenes que no sean MARKET
            if order_type != "MARKET":
                order_params["timeInForce"] = time_in_force

            orden = self._client.futures_create_order(**order_params)
            log.info(f"Orden creada exitosamente: {orden['orderId']}")

            # Actualizar información de cuenta después de crear orden
            self.get_account_info()

            return orden

        except BinanceAPIException as e:
            log.error(f"Error al crear la orden: {e}")
            raise e

    def get_account_info(self) -> bool:
        """
        Obtiene y actualiza la información de la cuenta de Futures

        Returns:
            True si la operación fue exitosa, False en caso contrario
        """
        try:
            # Obtener información general de la cuenta
            account_info = self._client.futures_account()

            # Actualizar balance y equity
            self._balance = float(account_info["totalWalletBalance"])
            self._equity = float(account_info["totalMarginBalance"])
            self._pnl_total = float(account_info["totalUnrealizedProfit"])

            # Verificar si hay posiciones abiertas
            positions = self._client.futures_position_information(
                symbol=self._config.simbolo
            )
            self._posicion_abierta = any(
                float(pos["positionAmt"]) != 0 for pos in positions
            )

            log.debug(
                f"Información de cuenta actualizada - Balance: {self._balance}, Equity: {self._equity}"
            )
            return True

        except BinanceAPIException as e:
            log.error(f"Error al obtener la información de la cuenta: {e}")
            return False

    # Propiedades para acceso controlado a los atributos privados
    @property
    def balance(self) -> float:
        """Balance total de la wallet en USDT"""
        return self._balance

    @property
    def equity(self) -> float:
        """Equity total (balance + PnL no realizado) en USDT"""
        return self._equity

    @property
    def pnl_total(self) -> float:
        """PnL total no realizado en USDT"""
        return self._pnl_total

    @property
    def posicion_abierta(self) -> bool:
        """Indica si hay una posición abierta en el símbolo configurado"""
        return self._posicion_abierta

    @property
    def simbolo(self) -> str:
        """Símbolo configurado para trading"""
        return self._config.simbolo

    @property
    def apalancamiento(self) -> float:
        """Nivel de apalancamiento configurado"""
        return self._config.apalancamiento
