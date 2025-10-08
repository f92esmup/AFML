"""
Tests para la función ejecutar_operacion() en live.py

Estos tests verifican específicamente el fix del bug de cierre de posiciones:
- Operaciones de cierre NO deben fallar por balance insuficiente
- Operaciones de abrir/aumentar SÍ deben validar margen disponible
- La interpretación de acciones NO debe cambiar
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any


# Importar la función a testear
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from live import ejecutar_operacion


class TestEjecutarOperacionCierre:
    """Tests para operaciones de CIERRE - Lo que se corrigió en el fix"""
    
    def test_cerrar_short_con_balance_bajo_debe_funcionar(self):
        """
        TEST CRÍTICO: Cerrar SHORT debe funcionar aunque balance_disponible < equity
        
        Este es el bug que se corrigió. Antes fallaba, ahora debe funcionar.
        """
        # Setup: Mock de BinanceConnector con balance bajo pero posición abierta
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Estado: Posición SHORT abierta con balance parcialmente comprometido
        mock_binance.get_position_info.return_value = {
            'balance': 4986.13,  # Balance disponible
            'equity': 5506.68,   # Equity total (incluye PnL no realizado)
            'posicion_abierta': True,
            'tipo_posicion_activa': 'SHORT',
            'cantidad_activa': 0.679344,
            'precio_entrada_activa': 121500.0,
            'pnl_no_realizado': 520.55,
        }
        
        # Mock de create_order que retorna orden exitosa
        mock_binance.create_order.return_value = {
            'orderId': 123456789,
            'status': 'FILLED',
            'executedQty': '0.679344',
        }
        
        mock_binance.get_account_info.return_value = True
        
        # Acción interpretada: CERRAR SHORT
        accion_interpretada = {
            'tipo_accion': 'long',  # Quiere ir long, pero tiene short
            'operacion': 'cerrar_short',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        precio = 121588.11
        
        # EJECUTAR
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, precio)
        
        # VERIFICAR
        assert resultado['resultado'] is True, "El cierre debe ser exitoso"
        assert resultado['operacion'] == 'cerrar_short'
        assert 'trade_id' in resultado
        assert resultado['trade_id'] == 123456789
        
        # Verificar que se llamó create_order con reduce_only=True
        mock_binance.create_order.assert_called()
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['reduce_only'] is True, "Debe usar reduce_only para cerrar"
        assert call_kwargs['side'] == 'BUY', "Cerrar SHORT requiere BUY"
        assert call_kwargs['quantity'] == 0.679344, "Debe usar cantidad_activa exacta"
        
        # Verificar que NO se llamó calculate_position_size para el cierre
        assert not hasattr(mock_binance, 'calculate_position_size') or \
               not mock_binance.calculate_position_size.called, \
               "NO debe calcular nueva cantidad para cerrar"
    
    def test_cerrar_long_con_balance_bajo_debe_funcionar(self):
        """
        TEST CRÍTICO: Cerrar LONG debe funcionar aunque balance sea bajo
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Estado: Posición LONG abierta
        mock_binance.get_position_info.return_value = {
            'balance': 3000.0,
            'equity': 5200.0,
            'posicion_abierta': True,
            'tipo_posicion_activa': 'LONG',
            'cantidad_activa': 0.5,
            'precio_entrada_activa': 120000.0,
            'pnl_no_realizado': 2200.0,
        }
        
        mock_binance.create_order.return_value = {
            'orderId': 987654321,
            'status': 'FILLED',
        }
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'short',
            'operacion': 'cerrar_long',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        # VERIFICAR
        assert resultado['resultado'] is True
        assert resultado['operacion'] == 'cerrar_long'
        
        # Verificar llamada correcta a create_order
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['reduce_only'] is True
        assert call_kwargs['side'] == 'SELL', "Cerrar LONG requiere SELL"
        assert call_kwargs['quantity'] == 0.5
    
    def test_cerrar_sin_posicion_abierta_debe_fallar_apropiadamente(self):
        """
        TEST: Intentar cerrar sin posición debe retornar error apropiado
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Estado: SIN posición abierta
        mock_binance.get_position_info.return_value = {
            'balance': 5000.0,
            'equity': 5000.0,
            'posicion_abierta': False,
            'tipo_posicion_activa': None,
            'cantidad_activa': None,
        }
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'cerrar_short',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        # VERIFICAR
        assert resultado['resultado'] is False, "Debe fallar apropiadamente"
        assert 'error' in resultado
        assert 'No hay posición abierta' in resultado['error']
        
        # NO debe haber intentado crear orden
        mock_binance.create_order.assert_not_called()


class TestEjecutarOperacionAbrir:
    """Tests para operaciones de ABRIR - No debe cambiar comportamiento"""
    
    def test_abrir_long_con_balance_suficiente(self):
        """
        TEST: Abrir LONG con balance suficiente debe funcionar (sin cambios)
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Estado: Sin posición, con balance
        mock_binance.get_position_info.return_value = {
            'balance': 5000.0,
            'equity': 5000.0,
            'posicion_abierta': False,
            'tipo_posicion_activa': None,
            'cantidad_activa': None,
        }
        
        # calculate_position_size retorna cantidad válida
        mock_binance.calculate_position_size.return_value = 0.5
        
        mock_binance.create_order.return_value = {
            'orderId': 111111111,
            'status': 'FILLED',
        }
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'abrir_long',
            'debe_ejecutar': True,
            'intensidad': 0.8,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        # VERIFICAR
        assert resultado['resultado'] is True
        assert resultado['operacion'] == 'abrir_long'
        
        # Debe haber llamado calculate_position_size
        mock_binance.calculate_position_size.assert_called_once()
        
        # Verificar llamada a create_order
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['side'] == 'BUY'
        assert call_kwargs['quantity'] == 0.5
        assert 'reduce_only' not in call_kwargs or call_kwargs['reduce_only'] is False
    
    def test_abrir_short_con_balance_suficiente(self):
        """
        TEST: Abrir SHORT con balance suficiente debe funcionar (sin cambios)
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Estado previo y posterior completos
        estado_previo = {
            'balance': 5000.0,
            'equity': 5000.0,
            'posicion_abierta': False,
            'cantidad_activa': None,
        }
        
        estado_posterior = {
            'balance': 4800.0,
            'equity': 5000.0,
            'posicion_abierta': True,
            'cantidad_activa': 0.3,
            'tipo_posicion_activa': 'SHORT',
        }
        
        # Configurar get_position_info para retornar estados diferentes
        mock_binance.get_position_info.side_effect = [estado_previo, estado_posterior]
        
        mock_binance.calculate_position_size.return_value = 0.3
        mock_binance.create_order.return_value = {'orderId': 222222222}
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'short',
            'operacion': 'abrir_short',
            'debe_ejecutar': True,
            'intensidad': 0.6,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is True
        assert resultado['operacion'] == 'abrir_short'
        
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['side'] == 'SELL'
        assert call_kwargs['quantity'] == 0.3
    
    def test_abrir_con_balance_insuficiente_debe_fallar(self):
        """
        TEST CRÍTICO: Abrir con balance insuficiente debe fallar (sin cambios)
        
        Esta validación debe seguir funcionando para operaciones de ABRIR.
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        mock_binance.get_position_info.return_value = {
            'balance': 100.0,  # Balance muy bajo
            'equity': 100.0,
            'posicion_abierta': False,
        }
        
        # calculate_position_size retorna 0 (balance insuficiente)
        mock_binance.calculate_position_size.return_value = 0.0
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'abrir_long',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        # VERIFICAR
        assert resultado['resultado'] is False, "Debe fallar por balance insuficiente"
        assert 'error' in resultado
        assert 'Balance insuficiente' in resultado['error'] or 'Cantidad calculada es 0' in resultado['error']
        
        # NO debe haber creado orden
        mock_binance.create_order.assert_not_called()


class TestEjecutarOperacionAumentar:
    """Tests para operaciones de AUMENTAR - No debe cambiar comportamiento"""
    
    def test_aumentar_long_con_balance_suficiente(self):
        """
        TEST: Aumentar LONG debe funcionar con balance suficiente (sin cambios)
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        mock_binance.get_position_info.return_value = {
            'balance': 3000.0,
            'equity': 4000.0,
            'posicion_abierta': True,
            'tipo_posicion_activa': 'LONG',
            'cantidad_activa': 0.3,
        }
        
        mock_binance.calculate_position_size.return_value = 0.2
        mock_binance.create_order.return_value = {'orderId': 333333333}
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'aumentar_long',
            'debe_ejecutar': True,
            'intensidad': 0.5,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is True
        assert resultado['operacion'] == 'aumentar_long'
        
        # Debe calcular nueva cantidad
        mock_binance.calculate_position_size.assert_called_once()
        
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['side'] == 'BUY'
        assert call_kwargs['quantity'] == 0.2
    
    def test_aumentar_short_con_balance_suficiente(self):
        """
        TEST: Aumentar SHORT debe funcionar con balance suficiente (sin cambios)
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        mock_binance.get_position_info.return_value = {
            'balance': 3000.0,
            'equity': 4000.0,
            'posicion_abierta': True,
            'tipo_posicion_activa': 'SHORT',
            'cantidad_activa': 0.4,
        }
        
        mock_binance.calculate_position_size.return_value = 0.15
        mock_binance.create_order.return_value = {'orderId': 444444444}
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'short',
            'operacion': 'aumentar_short',
            'debe_ejecutar': True,
            'intensidad': 0.4,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is True
        assert resultado['operacion'] == 'aumentar_short'
        
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['side'] == 'SELL'
        assert call_kwargs['quantity'] == 0.15


class TestEjecutarOperacionExcepciones:
    """Tests para manejo de excepciones y casos edge"""
    
    def test_create_order_retorna_none(self):
        """
        TEST: Si create_order retorna None, debe manejar apropiadamente
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        mock_binance.get_position_info.return_value = {
            'balance': 5000.0,
            'equity': 5000.0,
            'posicion_abierta': False,
        }
        
        mock_binance.calculate_position_size.return_value = 0.5
        mock_binance.create_order.return_value = None  # API falló
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'abrir_long',
            'debe_ejecutar': True,
            'intensidad': 0.8,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is False
        assert 'error' in resultado
        assert 'create_order retornó None' in resultado['error']
    
    def test_excepcion_durante_ejecucion(self):
        """
        TEST: Excepciones durante ejecución deben ser capturadas
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Primera llamada retorna estado OK, segunda lanza excepción
        mock_binance.get_position_info.side_effect = [
            {
                'balance': 5000.0,
                'equity': 5000.0,
                'posicion_abierta': True,
                'tipo_posicion_activa': 'SHORT',
                'cantidad_activa': 0.5,
            },
            Exception("Error de red")  # Segunda llamada falla
        ]
        
        mock_binance.create_order.return_value = {'orderId': 123456}
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'cerrar_short',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is False
        assert 'error' in resultado
        assert 'Error de red' in resultado['error']


class TestEjecutarOperacionIntegracion:
    """Tests de integración que verifican el flujo completo"""
    
    def test_cerrar_short_y_verificar_no_calcula_cantidad(self):
        """
        TEST DE INTEGRACIÓN: Verificar que cerrar NO llama a calculate_position_size
        
        Este es el comportamiento clave del fix: los cierres usan cantidad_activa,
        NO calculan una nueva cantidad.
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        # Posición SHORT abierta
        mock_binance.get_position_info.return_value = {
            'balance': 2000.0,
            'equity': 5500.0,
            'posicion_abierta': True,
            'tipo_posicion_activa': 'SHORT',
            'cantidad_activa': 0.679344,
        }
        
        mock_binance.create_order.return_value = {'orderId': 555555555}
        mock_binance.get_account_info.return_value = True
        
        # Configurar calculate_position_size para verificar que NO se llama
        mock_binance.calculate_position_size = Mock(return_value=0.0)
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'cerrar_short',
            'debe_ejecutar': True,
            'intensidad': 1.0,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121588.11)
        
        # VERIFICACIONES CRÍTICAS
        assert resultado['resultado'] is True, "Debe cerrar exitosamente"
        
        # ¡VERIFICACIÓN CLAVE DEL FIX!
        # calculate_position_size NO debe haberse llamado para el cierre
        mock_binance.calculate_position_size.assert_not_called()
        
        # Debe haber usado cantidad_activa exacta
        call_kwargs = mock_binance.create_order.call_args[1]
        assert call_kwargs['quantity'] == 0.679344
    
    def test_abrir_long_y_verificar_si_calcula_cantidad(self):
        """
        TEST DE INTEGRACIÓN: Verificar que abrir SÍ llama a calculate_position_size
        
        Contraste con el test anterior: abrir/aumentar SÍ deben calcular cantidad.
        """
        mock_binance = Mock()
        mock_binance.simbolo = "BTCUSDT"
        
        estado_previo = {
            'balance': 5000.0,
            'equity': 5000.0,
            'posicion_abierta': False,
            'cantidad_activa': None,
        }
        
        estado_posterior = {
            'balance': 4700.0,
            'equity': 5000.0,
            'posicion_abierta': True,
            'cantidad_activa': 0.4,
            'tipo_posicion_activa': 'LONG',
        }
        
        mock_binance.get_position_info.side_effect = [estado_previo, estado_posterior]
        mock_binance.calculate_position_size = Mock(return_value=0.4)
        mock_binance.create_order.return_value = {'orderId': 666666666}
        mock_binance.get_account_info.return_value = True
        
        accion_interpretada = {
            'tipo_accion': 'long',
            'operacion': 'abrir_long',
            'debe_ejecutar': True,
            'intensidad': 0.8,
        }
        
        resultado = ejecutar_operacion(mock_binance, accion_interpretada, 121500.0)
        
        assert resultado['resultado'] is True
        
        # ¡VERIFICACIÓN CLAVE!
        # Para abrir, SÍ debe llamar calculate_position_size
        mock_binance.calculate_position_size.assert_called_once()
        
        # Verificar que se pasaron los parámetros correctos
        call_args = mock_binance.calculate_position_size.call_args
        assert call_args[1]['action'] == 0.8  # intensidad para long
        assert call_args[1]['precio_actual'] == 121500.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
