"""Tests para el módulo info_builder.py"""

import pytest
from typing import Dict, Any

from src.train.Entrenamiento.entorno.info_builder import build_info_dict, _ensure_keys


class TestEnsureKeys:
    """Tests para la función auxiliar _ensure_keys."""
    
    def test_ensure_keys_with_empty_source(self):
        """Debe rellenar con valores por defecto cuando la fuente está vacía."""
        keys = {'key1': None, 'key2': False, 'key3': 0}
        result = _ensure_keys({}, keys)
        
        assert result == {'key1': None, 'key2': False, 'key3': 0}
    
    def test_ensure_keys_with_none_source(self):
        """Debe manejar fuente None correctamente."""
        keys = {'key1': 'default', 'key2': 42}
        result = _ensure_keys(None, keys)
        
        assert result == {'key1': 'default', 'key2': 42}
    
    def test_ensure_keys_with_partial_source(self):
        """Debe combinar valores existentes con valores por defecto."""
        keys = {'key1': None, 'key2': False, 'key3': 0}
        source = {'key1': 'value1', 'key3': 100}
        result = _ensure_keys(source, keys)
        
        assert result == {'key1': 'value1', 'key2': False, 'key3': 100}
    
    def test_ensure_keys_with_complete_source(self):
        """Debe usar todos los valores de la fuente cuando están presentes."""
        keys = {'key1': None, 'key2': False}
        source = {'key1': 'value1', 'key2': True}
        result = _ensure_keys(source, keys)
        
        assert result == {'key1': 'value1', 'key2': True}
    
    def test_ensure_keys_ignores_extra_keys_in_source(self):
        """Debe ignorar claves en la fuente que no están en keys."""
        keys = {'key1': None, 'key2': False}
        source = {'key1': 'value1', 'key2': True, 'extra': 'ignored'}
        result = _ensure_keys(source, keys)
        
        assert result == {'key1': 'value1', 'key2': True}
        assert 'extra' not in result


class TestBuildInfoDict:
    """Tests para la función principal build_info_dict."""
    
    def test_build_info_dict_with_no_arguments(self):
        """Debe crear estructura completa con valores por defecto cuando no hay argumentos."""
        result = build_info_dict()
        
        # Verificar que tiene las tres secciones principales
        assert 'entorno' in result
        assert 'portafolio' in result
        assert 'operacion' in result
        
        # Verificar que todas las claves de entorno están presentes
        assert 'paso' in result['entorno']
        assert 'episodio' in result['entorno']
        assert 'timestamp' in result['entorno']
        assert 'action' in result['entorno']
        assert 'precio' in result['entorno']
        assert 'recompensa' in result['entorno']
        assert 'terminated' in result['entorno']
        assert 'truncated' in result['entorno']
        assert 'status' in result['entorno']
        
        # Verificar valores por defecto
        assert result['entorno']['paso'] is None
        assert result['entorno']['terminated'] is False
        assert result['entorno']['truncated'] is False
    
    def test_build_info_dict_with_entorno_data(self):
        """Debe procesar correctamente datos de entorno."""
        entorno_data = {
            'paso': 10,
            'episodio': 5,
            'precio': 50000.0,
            'recompensa': 0.5,
            'terminated': True
        }
        
        result = build_info_dict(entorno=entorno_data)
        
        assert result['entorno']['paso'] == 10
        assert result['entorno']['episodio'] == 5
        assert result['entorno']['precio'] == 50000.0
        assert result['entorno']['recompensa'] == 0.5
        assert result['entorno']['terminated'] is True
        assert result['entorno']['timestamp'] is None  # No proporcionado
    
    def test_build_info_dict_with_portafolio_data(self):
        """Debe procesar correctamente datos de portafolio."""
        portafolio_data = {
            'balance': 10000.0,
            'equity': 10500.0,
            'max_drawdown': 0.05,
            'posicion_abierta': True,
            'pnl_total': 500.0
        }
        
        result = build_info_dict(portafolio=portafolio_data)
        
        assert result['portafolio']['balance'] == 10000.0
        assert result['portafolio']['equity'] == 10500.0
        assert result['portafolio']['max_drawdown'] == 0.05
        assert result['portafolio']['posicion_abierta'] is True
        assert result['portafolio']['pnl_total'] == 500.0
        assert result['portafolio']['trade_id_activo'] is None  # No proporcionado
    
    def test_build_info_dict_with_operacion_data(self):
        """Debe procesar correctamente datos de operación."""
        operacion_data = {
            'tipo_accion': 'long',
            'operacion': 'abrir_long',
            'resultado': True,
            'trade_id': 1,
            'precio_entrada': 50000.0,
            'cantidad': 0.1,
            'comision': 5.0
        }
        
        result = build_info_dict(operacion=operacion_data)
        
        assert result['operacion']['tipo_accion'] == 'long'
        assert result['operacion']['operacion'] == 'abrir_long'
        assert result['operacion']['resultado'] is True
        assert result['operacion']['trade_id'] == 1
        assert result['operacion']['precio_entrada'] == 50000.0
        assert result['operacion']['cantidad'] == 0.1
        assert result['operacion']['comision'] == 5.0
        assert result['operacion']['error'] is None  # No proporcionado
    
    def test_build_info_dict_with_all_sections(self):
        """Debe combinar correctamente datos de las tres secciones."""
        entorno_data = {'paso': 20, 'precio': 51000.0}
        portafolio_data = {'balance': 9500.0, 'equity': 9800.0}
        operacion_data = {'tipo_accion': 'short', 'resultado': True}
        
        result = build_info_dict(
            entorno=entorno_data,
            portafolio=portafolio_data,
            operacion=operacion_data
        )
        
        # Verificar que cada sección tiene sus datos
        assert result['entorno']['paso'] == 20
        assert result['entorno']['precio'] == 51000.0
        assert result['portafolio']['balance'] == 9500.0
        assert result['portafolio']['equity'] == 9800.0
        assert result['operacion']['tipo_accion'] == 'short'
        assert result['operacion']['resultado'] is True
    
    def test_build_info_dict_structure_consistency(self):
        """Debe retornar siempre la misma estructura sin importar la entrada."""
        # Primera llamada sin argumentos
        result1 = build_info_dict()
        keys1 = set(result1['entorno'].keys())
        
        # Segunda llamada con datos parciales
        result2 = build_info_dict(entorno={'paso': 1})
        keys2 = set(result2['entorno'].keys())
        
        # Tercera llamada con datos completos
        entorno_full = {
            'paso': 1, 'episodio': 1, 'timestamp': None, 'action': 0.5,
            'precio': 50000, 'recompensa': 0.1, 'terminated': False,
            'truncated': False, 'status': 'ok'
        }
        result3 = build_info_dict(entorno=entorno_full)
        keys3 = set(result3['entorno'].keys())
        
        # Todas deben tener las mismas claves
        assert keys1 == keys2 == keys3
    
    def test_build_info_dict_default_booleans(self):
        """Debe usar False como valor por defecto para booleanos específicos."""
        result = build_info_dict()
        
        # Verificar valores booleanos por defecto
        assert result['entorno']['terminated'] is False
        assert result['entorno']['truncated'] is False
        assert result['portafolio']['posicion_abierta'] is False
    
    def test_build_info_dict_preserves_none_values(self):
        """Debe preservar valores None explícitos."""
        operacion_data = {
            'tipo_accion': 'mantener',
            'resultado': True,
            'error': None,  # Explícitamente None
            'trade_id': None
        }
        
        result = build_info_dict(operacion=operacion_data)
        
        assert result['operacion']['error'] is None
        assert result['operacion']['trade_id'] is None
    
    def test_build_info_dict_with_complete_portafolio_snapshot(self):
        """Debe manejar un snapshot completo de portafolio."""
        portafolio_data = {
            'balance': 10000.0,
            'equity': 10500.0,
            'max_drawdown': 0.05,
            'operaciones_total': 10,
            'pnl_total': 500.0,
            'posicion_abierta': True,
            'trade_id_activo': 5,
            'tipo_posicion_activa': 'long',
            'precio_entrada_activa': 49500.0,
            'cantidad_activa': 0.2,
            'velas_activa': 15,
            'pnl_no_realizado': 100.0
        }
        
        result = build_info_dict(portafolio=portafolio_data)
        
        # Verificar que todos los campos están presentes y correctos
        assert result['portafolio']['balance'] == 10000.0
        assert result['portafolio']['equity'] == 10500.0
        assert result['portafolio']['max_drawdown'] == 0.05
        assert result['portafolio']['operaciones_total'] == 10
        assert result['portafolio']['pnl_total'] == 500.0
        assert result['portafolio']['posicion_abierta'] is True
        assert result['portafolio']['trade_id_activo'] == 5
        assert result['portafolio']['tipo_posicion_activa'] == 'long'
        assert result['portafolio']['precio_entrada_activa'] == 49500.0
        assert result['portafolio']['cantidad_activa'] == 0.2
        assert result['portafolio']['velas_activa'] == 15
        assert result['portafolio']['pnl_no_realizado'] == 100.0
    
    def test_build_info_dict_operation_with_all_fields(self):
        """Debe manejar operación con todos los campos posibles."""
        operacion_data = {
            'tipo_accion': 'long',
            'operacion': 'aumento_posicion',
            'resultado': True,
            'error': None,
            'trade_id': 3,
            'tipo_posicion': 'long',
            'precio_entrada': 50000.0,
            'precio_salida': None,
            'cantidad': 0.1,
            'cantidad_adicional': 0.05,
            'cantidad_total': 0.15,
            'cantidad_restante': None,
            'cantidad_reducida': None,
            'porcentaje_inversion': 0.5,
            'comision': 5.0,
            'slippage': 2.5,
            'margen': 5000.0,
            'margen_liberado': None,
            'pnl_realizado': None,
            'pnl_parcial': None,
            'velas_abiertas': 10
        }
        
        result = build_info_dict(operacion=operacion_data)
        
        # Verificar algunos campos clave
        assert result['operacion']['operacion'] == 'aumento_posicion'
        assert result['operacion']['cantidad_adicional'] == 0.05
        assert result['operacion']['cantidad_total'] == 0.15
        assert result['operacion']['velas_abiertas'] == 10
