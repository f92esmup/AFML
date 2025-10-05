"""Se encarga de el enlace con Binance"""

from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, Optional, List
import logging
import time
from requests.exceptions import ReadTimeout, ConnectionError, Timeout

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
        
        # Información de la posición activa
        self._posicion_info: Optional[Dict[str, Any]] = None
        
        # Tracking de equity máximo para cálculo de drawdown
        self._max_equity: float = 0.0
        
        # Valores iniciales REALES de la cuenta (se obtienen en initialize_account)
        self._equity_inicial: float = 0.0
        self._balance_inicial: float = 0.0

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
            # Solo loguear el error, no re-lanzar
            # El apalancamiento puede estar ya configurado desde otra sesión
            log.error(f"Error al configurar apalancamiento: {e}")
    
    def initialize_account(self) -> bool:
        """
        Inicializa la cuenta obteniendo los valores REALES iniciales de Binance.
        DEBE llamarse ANTES de inicializar ControlRiesgo y ObservacionBuilder.
        
        Returns:
            True si la inicialización fue exitosa, False en caso contrario
        """
        try:
            log.info("Inicializando cuenta desde Binance API...")
            
            # Obtener información de cuenta
            success = self.get_account_info()
            if not success:
                log.error("❌ Error al obtener información inicial de la cuenta")
                return False
            
            # Guardar valores iniciales REALES
            self._equity_inicial = self._equity
            self._balance_inicial = self._balance
            self._max_equity = self._equity  # Inicializar max_equity con equity real
            
            log.info("✅ Cuenta inicializada correctamente")
            log.info(f"   Balance inicial: {self._balance_inicial:.2f} USDT")
            log.info(f"   Equity inicial: {self._equity_inicial:.2f} USDT")
            log.info(f"   Posición abierta: {'SÍ' if self._posicion_abierta else 'NO'}")
            
            # Advertencia si ya hay posiciones abiertas
            if self._posicion_abierta:
                log.warning("⚠️  ADVERTENCIA: Ya existe una posición abierta al iniciar")
                log.warning(f"   El sistema continuará gestionando esta posición")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Error crítico al inicializar cuenta: {e}")
            return False

    def create_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        reduce_only: bool = False,
        time_in_force: str = "GTC",
    ) -> Optional[Dict[str, Any]]:
        """
        Crea una orden genérica para Futures USDT-M con configuración one-way y reintentos automáticos

        Args:
            symbol: Símbolo del par de trading (ej: 'BTCUSDT')
            side: Dirección de la orden ('BUY' o 'SELL')
            quantity: Cantidad a operar
            order_type: Tipo de orden ('MARKET', 'LIMIT', etc.)
            reduce_only: Si la orden es solo para reducir posición
            time_in_force: Tiempo de vigencia de la orden

        Returns:
            Diccionario con la respuesta de la API de Binance o None en caso de error

        Raises:
            BinanceAPIException: Error en la API de Binance
        """
        max_retries = 3
        base_delay = 1  # segundos (más corto para órdenes)
        
        for attempt in range(max_retries):
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

            except (ReadTimeout, ConnectionError, Timeout) as e:
                attempt_num = attempt + 1
                if attempt_num < max_retries:
                    delay = base_delay * (2 ** attempt)
                    log.warning(
                        f"⚠️ Timeout al crear orden (intento {attempt_num}/{max_retries}). "
                        f"Reintentando en {delay}s... Error: {type(e).__name__}"
                    )
                    time.sleep(delay)
                else:
                    log.error(
                        f"❌ Error de timeout al crear orden después de {max_retries} intentos: {e}"
                    )
                    return None
                    
            except BinanceAPIException as e:
                log.error(f"Error al crear la orden: {e}")
                # No re-lanzar, retornar None para que el llamador maneje el error
                return None
            except Exception as e:
                log.error(f"Error inesperado al crear orden: {e}")
                return None
        
        return None

    def get_account_info(self) -> bool:
        """
        Obtiene y actualiza la información de la cuenta de Futures con reintentos automáticos

        Returns:
            True si la operación fue exitosa, False en caso contrario
        """
        max_retries = 3
        base_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                # Obtener información general de la cuenta
                account_info = self._client.futures_account()

                # Actualizar balance y equity
                self._balance = float(account_info["totalWalletBalance"])
                self._equity = float(account_info["totalMarginBalance"])
                self._pnl_total = float(account_info["totalUnrealizedProfit"])
                
                # Actualizar max equity para cálculo de drawdown
                if self._equity > self._max_equity:
                    self._max_equity = self._equity

                # Verificar si hay posiciones abiertas y guardar información
                positions = self._client.futures_position_information(
                    symbol=self._config.simbolo
                )
                
                self._posicion_abierta = False
                self._posicion_info = None
                
                for pos in positions:
                    position_amt = float(pos["positionAmt"])
                    if position_amt != 0:
                        self._posicion_abierta = True
                        self._posicion_info = pos
                        break

                log.debug(
                    f"Información de cuenta actualizada - Balance: {self._balance}, Equity: {self._equity}, Posición: {self._posicion_abierta}"
                )
                return True

            except (ReadTimeout, ConnectionError, Timeout) as e:
                attempt_num = attempt + 1
                if attempt_num < max_retries:
                    # Backoff exponencial: 2s, 4s, 8s
                    delay = base_delay * (2 ** attempt)
                    log.warning(
                        f"⚠️ Timeout en API de Binance (intento {attempt_num}/{max_retries}). "
                        f"Reintentando en {delay}s... Error: {type(e).__name__}"
                    )
                    time.sleep(delay)
                else:
                    log.error(
                        f"❌ Error de timeout después de {max_retries} intentos: {e}"
                    )
                    return False
                    
            except BinanceAPIException as e:
                log.error(f"Error al obtener la información de la cuenta: {e}")
                return False
            except Exception as e:
                log.error(f"Error inesperado al obtener información de cuenta: {e}")
                return False
        
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
    
    @property
    def equity_inicial(self) -> float:
        """Equity inicial REAL obtenido de Binance al iniciar"""
        return self._equity_inicial
    
    @property
    def balance_inicial(self) -> float:
        """Balance inicial REAL obtenido de Binance al iniciar"""
        return self._balance_inicial
    
    def get_position_info(self) -> Dict[str, Any]:
        """
        Obtiene información detallada de la posición actual.
        
        Returns:
            Diccionario con información del portfolio compatible con info_builder:
            {
                'balance': float,
                'equity': float,
                'max_drawdown': float,
                'pnl_total': float,
                'posicion_abierta': bool,
                'tipo_posicion_activa': str o None,
                'precio_entrada_activa': float o None,
                'cantidad_activa': float o None,
                'pnl_no_realizado': float,
            }
        """
        try:
            # Actualizar información primero
            self.get_account_info()
            
            # Calcular drawdown
            drawdown = 0.0
            if self._max_equity > 0:
                drawdown = (self._max_equity - self._equity) / self._max_equity
            
            info = {
                'balance': self._balance,
                'equity': self._equity,
                'max_drawdown': drawdown,
                'pnl_total': self._pnl_total,
                'posicion_abierta': self._posicion_abierta,
                'pnl_no_realizado': self._pnl_total,
            }
            
            # Añadir información de posición activa si existe
            if self._posicion_info is not None and self._posicion_abierta:
                info.update({
                    'tipo_posicion_activa': 'LONG' if float(self._posicion_info.get('positionAmt', 0)) > 0 else 'SHORT',
                    'precio_entrada_activa': float(self._posicion_info.get('entryPrice', 0)),
                    'cantidad_activa': abs(float(self._posicion_info.get('positionAmt', 0))),
                })
            else:
                info.update({
                    'tipo_posicion_activa': None,
                    'precio_entrada_activa': None,
                    'cantidad_activa': None,
                })
            
            return info
            
        except Exception as e:
            log.error(f"Error al obtener información de posición: {e}")
            # Retornar diccionario con valores por defecto en caso de error
            return {
                'balance': 0.0,
                'equity': 0.0,
                'max_drawdown': 0.0,
                'pnl_total': 0.0,
                'posicion_abierta': False,
                'tipo_posicion_activa': None,
                'precio_entrada_activa': None,
                'cantidad_activa': None,
                'pnl_no_realizado': 0.0,
            }
    
    def close_all_positions(self, emergency: bool = False) -> Dict[str, Any]:
        """
        Cierra todas las posiciones abiertas y cancela órdenes pendientes.
        CRÍTICO para el protocolo de emergencia.
        
        Args:
            emergency: Si es True, indica que es un cierre de emergencia
            
        Returns:
            Diccionario con el resultado:
            {
                'posiciones_cerradas': int,
                'ordenes_canceladas': int,
                'balance_final': float,
                'equity_final': float,
                'errores': List[str]
            }
        """
        resultado = {
            'posiciones_cerradas': 0,
            'ordenes_canceladas': 0,
            'balance_final': 0.0,
            'equity_final': 0.0,
            'errores': []
        }
        
        try:
            if emergency:
                log.critical("🚨 INICIANDO CIERRE DE EMERGENCIA DE TODAS LAS POSICIONES")
            else:
                log.warning("Cerrando todas las posiciones...")
            
            # 1. Cancelar todas las órdenes pendientes
            max_retries = 3
            base_delay = 1
            
            for attempt in range(max_retries):
                try:
                    self._client.futures_cancel_all_open_orders(symbol=self._config.simbolo)
                    resultado['ordenes_canceladas'] = 1  # No sabemos el número exacto
                    log.info("✅ Órdenes pendientes canceladas")
                    break  # Éxito, salir del loop
                except (ReadTimeout, ConnectionError, Timeout) as e:
                    attempt_num = attempt + 1
                    if attempt_num < max_retries:
                        delay = base_delay * (2 ** attempt)
                        log.warning(
                            f"⚠️ Timeout al cancelar órdenes (intento {attempt_num}/{max_retries}). "
                            f"Reintentando en {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        error_msg = f"Error de timeout al cancelar órdenes después de {max_retries} intentos: {e}"
                        log.error(error_msg)
                        resultado['errores'].append(error_msg)
                except BinanceAPIException as e:
                    error_msg = f"Error al cancelar órdenes: {e}"
                    log.error(error_msg)
                    resultado['errores'].append(error_msg)
                    break  # Error de API, no reintentar
            
            # 2. Obtener posiciones actuales con reintentos
            positions = None
            for attempt in range(max_retries):
                try:
                    positions = self._client.futures_position_information(symbol=self._config.simbolo)
                    break  # Éxito, salir del loop
                except (ReadTimeout, ConnectionError, Timeout) as e:
                    attempt_num = attempt + 1
                    if attempt_num < max_retries:
                        delay = base_delay * (2 ** attempt)
                        log.warning(
                            f"⚠️ Timeout al obtener posiciones (intento {attempt_num}/{max_retries}). "
                            f"Reintentando en {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        error_msg = f"Error de timeout al obtener posiciones después de {max_retries} intentos: {e}"
                        log.error(error_msg)
                        resultado['errores'].append(error_msg)
                        return resultado
                except BinanceAPIException as e:
                    error_msg = f"Error al obtener posiciones: {e}"
                    log.error(error_msg)
                    resultado['errores'].append(error_msg)
                    return resultado
            
            if positions is None:
                error_msg = "No se pudieron obtener las posiciones"
                log.error(error_msg)
                resultado['errores'].append(error_msg)
                return resultado
            
            # 3. Cerrar cada posición abierta
            for pos in positions:
                position_amt = float(pos['positionAmt'])
                
                if position_amt != 0:
                    side = 'SELL' if position_amt > 0 else 'BUY'  # Definir antes del try
                    try:
                        # Determinar el lado de la orden de cierre
                        quantity = abs(position_amt)
                        
                        log.info(f"Cerrando posición {side}: cantidad={quantity}")
                        
                        # Crear orden de cierre (reduceOnly=True)
                        order = self.create_order(
                            symbol=self._config.simbolo,
                            side=side,
                            quantity=quantity,
                            order_type='MARKET',
                            reduce_only=True
                        )
                        
                        if order is not None:
                            resultado['posiciones_cerradas'] += 1
                            log.info(f"✅ Posición cerrada exitosamente: {order['orderId']}")
                        else:
                            error_msg = f"Error al cerrar posición {side}: create_order retornó None"
                            log.error(error_msg)
                            resultado['errores'].append(error_msg)
                        
                    except BinanceAPIException as e:
                        error_msg = f"Error al cerrar posición {side}: {e}"
                        log.error(error_msg)
                        resultado['errores'].append(error_msg)
            
            # 4. Actualizar información final
            self.get_account_info()
            resultado['balance_final'] = self._balance
            resultado['equity_final'] = self._equity
            
            if emergency:
                log.critical(f"🚨 CIERRE DE EMERGENCIA COMPLETADO")
                log.critical(f"   Posiciones cerradas: {resultado['posiciones_cerradas']}")
                log.critical(f"   Balance final: {resultado['balance_final']}")
                log.critical(f"   Equity final: {resultado['equity_final']}")
            else:
                log.info(f"✅ Cierre de posiciones completado")
            
            return resultado
            
        except Exception as e:
            error_msg = f"Error crítico en close_all_positions: {e}"
            log.error(error_msg)
            resultado['errores'].append(error_msg)
            return resultado
    
    def calculate_position_size(
        self, 
        action: float, 
        precio_actual: float
    ) -> float:
        """
        Calcula el tamaño de la posición basado en la acción del agente.
        
        EQUIVALENCIA MATEMÁTICA CON ENTRENAMIENTO:
        - Usa EQUITY (no balance) como base del cálculo
        - Incluye apalancamiento para determinar cantidad
        - Valida que el margen requerido no exceda el balance disponible
        - NO simula comisiones/slippage (Binance ya los incluye en equity real)
        
        Fórmula: cantidad = (equity * apalancamiento * intensidad) / precio
        donde intensidad = abs(action) y representa el % del equity a usar
        
        Args:
            action: Acción del agente (valor entre -1 y 1)
                   El valor absoluto representa el porcentaje del equity a usar
            precio_actual: Precio actual del activo
            
        Returns:
            Cantidad a operar (en unidades del activo), 0.0 si no hay balance suficiente
        """
        try:
            # El valor absoluto de la acción indica el porcentaje del equity a usar
            intensidad = abs(action)

            # PASO 1: Calcular cantidad objetivo usando EQUITY (equivalente a entrenamiento)
            # cantidad = (equity * apalancamiento * porcentaje_inversion) / precio
            cantidad_objetivo = (self._equity * self._config.apalancamiento * intensidad) / precio_actual
            
            if cantidad_objetivo <= 0:
                log.warning(f"Cantidad objetivo calculada es <= 0: {cantidad_objetivo}")
                return 0.0
            
            # PASO 2: Calcular margen requerido (lo que Binance descontará del balance)
            # margen = (precio * cantidad) / apalancamiento
            margen_requerido = (precio_actual * cantidad_objetivo) / self._config.apalancamiento
            
            # PASO 3: Validar que el margen cabe en el balance disponible
            if margen_requerido > self._balance:
                # NO HAY SUFICIENTE BALANCE DISPONIBLE
                # NO se ejecuta la operación (retornar 0)
                log.warning(
                    f"⚠️  Balance insuficiente para ejecutar la operación"
                )
                log.warning(
                    f"   Margen requerido: ${margen_requerido:.2f}"
                )
                log.warning(
                    f"   Balance disponible: ${self._balance:.2f}"
                )
                log.warning(
                    f"   Cantidad objetivo: {cantidad_objetivo:.6f}"
                )
                log.warning(
                    f"   Operación NO ejecutada"
                )
                
                return 0.0
            
            # El margen cabe en el balance, usar cantidad objetivo
            cantidad_final = round(cantidad_objetivo, 3)
            
            log.debug(
                f"Cantidad calculada: {cantidad_final} "
                f"(equity: ${self._equity:.2f}, intensidad: {intensidad:.2%}, "
                f"margen requerido: ${margen_requerido:.2f})"
            )
            
            return cantidad_final
            
        except Exception as e:
            log.error(f"Error al calcular tamaño de posición: {e}")
            return 0.0
