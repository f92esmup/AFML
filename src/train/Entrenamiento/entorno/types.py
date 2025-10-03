from typing import TypedDict, Optional


class OperationInfo(TypedDict, total=False):
    # standardized operation info returned by Portafolio methods
    operacion: str  # abrir_long, cerrar_short, aumento_posicion, reduccion_parcial, mantener
    tipo_accion: str  # long / short / mantener
    resultado: bool
    error: Optional[str]
    trade_id: Optional[int]
    tipo_posicion: Optional[str]
    precio_entrada: Optional[float]
    precio_salida: Optional[float]
    cantidad: Optional[float]
    cantidad_adicional: Optional[float]
    cantidad_total: Optional[float]
    cantidad_restante: Optional[float]
    cantidad_reducida: Optional[float]
    porcentaje_inversion: Optional[float]
    comision: Optional[float]
    slippage: Optional[float]
    margen: Optional[float]
    margen_liberado: Optional[float]
    pnl_realizado: Optional[float]
    pnl_parcial: Optional[float]
    velas_abiertas: Optional[int]


class PortafolioSnapshot(TypedDict, total=False):
    balance: float
    equity: float
    max_drawdown: float
    operaciones_total: int
    pnl_total: float
    posicion_abierta: bool
    trade_id_activo: Optional[int]
    tipo_posicion_activa: Optional[str]
    precio_entrada_activa: Optional[float]
    cantidad_activa: Optional[float]
    velas_activa: Optional[int]
    pnl_no_realizado: Optional[float]
