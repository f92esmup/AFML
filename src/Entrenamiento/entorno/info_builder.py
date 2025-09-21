"""Utilities to build a stable, nested info dictionary for the environment.

This module exposes a single helper `build_info_dict` that guarantees the
returned dict always contains the same keys grouped under `entorno`,
`portafolio` and `operacion`. Missing values are filled with `None` (or
`False` for booleans) so downstream processors can rely on a fixed schema.
"""
from typing import Dict, Any, Optional


def _ensure_keys(src: Optional[Dict[str, Any]], keys: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    src = src or {}
    for k, default in keys.items():
        out[k] = src.get(k, default)
    return out


def build_info_dict(entorno: Optional[Dict[str, Any]] = None,
                    portafolio: Optional[Dict[str, Any]] = None,
                    operacion: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Return a nested info dict with fixed keys.

    Each section uses sensible defaults (mostly None) when a value is not
    provided.
    """

    entorno_keys = {
        'paso': None,
        'episodio': None,
        'timestamp': None,
        'action': None,
        'precio': None,
        'recompensa': None,
        'terminated': False,
        'truncated': False,
        'status': None,
    }

    portafolio_keys = {
        'balance': None,
        'equity': None,
        'max_drawdown': None,
        'operaciones_total': None,
        'pnl_total': None,
        'posicion_abierta': False,
        # active position details
        'trade_id_activo': None,
        'tipo_posicion_activa': None,
        'precio_entrada_activa': None,
        'cantidad_activa': None,
        'velas_activa': None,
        'pnl_no_realizado': None,
    }

    operacion_keys = {
        'tipo_accion': None,      # mantener/long/short
        'operacion': None,        # abrir_long, cerrar_short, etc
        'resultado': None,
        'error': None,
        'trade_id': None,
        'tipo_posicion': None,
        'precio_entrada': None,
        'precio_salida': None,
        'cantidad': None,
        'cantidad_adicional': None,
        'cantidad_total': None,
        'cantidad_restante': None,
        'cantidad_reducida': None,
        'porcentaje_inversion': None,
        'comision': None,
        'slippage': None,
        'margen': None,
        'margen_liberado': None,
        'pnl_realizado': None,
        'pnl_parcial': None,
        'velas_abiertas': None,
    }

    entorno_clean = _ensure_keys(entorno, entorno_keys)
    portafolio_clean = _ensure_keys(portafolio, portafolio_keys)
    operacion_clean = _ensure_keys(operacion, operacion_keys)

    return {
        'entorno': entorno_clean,
        'portafolio': portafolio_clean,
        'operacion': operacion_clean,
    }
