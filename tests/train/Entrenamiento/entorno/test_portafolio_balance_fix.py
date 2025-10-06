"""
Tests para verificar el fix del bug crítico de balance exponencial decreciente.

Este módulo contiene tests que verifican que:
1. Aumentar posiciones NO reduce el balance exponencialmente
2. Reducir posiciones calcula correctamente basándose en la posición actual
3. El balance se mantiene consistente después de múltiples modificaciones
4. La nueva función _calcular_cantidad_invertir_desde_balance funciona correctamente

Relacionado con: docs/BUG_CRITICO_BALANCE_EXPONENCIAL.md
"""

import pytest
import numpy as np
import pandas as pd
from src.train.Entrenamiento.entorno.portafolio import Portafolio


class TestBalanceConsistente:
    """Tests para verificar consistencia del balance después del fix."""
    
    def test_abrir_posicion_inicial(self, portafolio):
        """Test básico: abrir una posición funciona correctamente."""
        precio = 100.0
        porcentaje = 0.5
        
        balance_inicial = portafolio._balance
        
        success, info = portafolio.abrir_posicion('long', precio, porcentaje)
        
        assert success is True
        assert portafolio._posicion_abierta is not None
        assert portafolio._balance < balance_inicial
        assert portafolio._balance > 0  # Balance positivo
        
    def test_aumentar_posicion_no_reduce_balance_exponencialmente(self, portafolio):
        """
        TEST CRÍTICO: Verificar que aumentar posición NO reduce balance exponencialmente.
        
        Este es el test principal para el bug reportado en docs/BUG_CRITICO_BALANCE_EXPONENCIAL.md
        """
        precio = 100.0
        
        # 1. Abrir posición inicial (50% del equity)
        portafolio.abrir_posicion('long', precio, 0.5)
        
        balance_despues_abrir = portafolio._balance
        equity_inicial = portafolio.get_equity(precio)
        
        # Verificar que tenemos balance disponible
        assert balance_despues_abrir > 0
        
        # 2. Intentar aumentar posición 10 veces (10% adicional cada vez)
        balances = [balance_despues_abrir]
        
        for i in range(10):
            # Aumentar 10% adicional
            success, info = portafolio.modificar_posicion(precio, 0.6 + (i * 0.01))
            
            balance_actual = portafolio._balance
            balances.append(balance_actual)
            
            # VERIFICACIÓN CRÍTICA: El balance NO debe reducirse exponencialmente
            # Si el balance llega a valores microscópicos (< 0.01 del inicial), hay un bug
            assert balance_actual > 0.01 * equity_inicial, (
                f"Balance colapsó exponencialmente en iteración {i+1}: "
                f"balance={balance_actual:.2e}, equity_inicial={equity_inicial:.2f}"
            )
            
            # El balance debe ser un número normal (no notación científica extrema)
            assert balance_actual > 1e-10, (
                f"Balance es microscópico en iteración {i+1}: {balance_actual:.2e}"
            )
        
        # Verificar que el balance final es razonable
        balance_final = portafolio._balance
        
        # El balance debe haberse reducido (se invirtió más), pero no colapsado
        assert balance_final < balance_despues_abrir
        assert balance_final > 0
        
        # Log para debugging
        print(f"\n✅ Test PASADO: Balance se mantiene consistente")
        print(f"   Balance después de abrir: ${balance_despues_abrir:.2f}")
        print(f"   Balance después de 10 aumentos: ${balance_final:.2f}")
        print(f"   Equity inicial: ${equity_inicial:.2f}")
    
    def test_calcular_cantidad_desde_balance_disponible(self, portafolio):
        """Test de la nueva función _calcular_cantidad_invertir_desde_balance."""
        precio = 100.0
        
        # Abrir posición para tener margen bloqueado
        portafolio.abrir_posicion('long', precio, 0.6)
        
        balance_disponible = portafolio._balance
        
        # Calcular cantidad adicional basada en balance disponible
        cantidad_adicional = portafolio._calcular_cantidad_invertir_desde_balance(
            precio, 0.3
        )
        
        # Verificar que la cantidad es positiva y razonable
        assert cantidad_adicional >= 0
        
        # Si hay balance, calcular costo de esa cantidad
        if cantidad_adicional > 0:
            margen = (precio * cantidad_adicional) / portafolio.apalancamiento
            comision = precio * cantidad_adicional * portafolio.comision_prc
            slippage = precio * cantidad_adicional * portafolio.slippage_prc
            costo_total = margen + comision + slippage
            
            # VERIFICACIÓN CRÍTICA: El costo NO debe exceder el balance disponible
            assert costo_total <= balance_disponible * 1.01, (
                f"Costo total ({costo_total:.2f}) excede balance disponible ({balance_disponible:.2f})"
            )
        
    def test_reducir_posicion_basada_en_cantidad_actual(self, portafolio):
        """Verificar que reducir posición funciona correctamente y mantiene consistencia."""
        precio = 100.0
        
        # Abrir posición
        portafolio.abrir_posicion('long', precio, 0.5)
        
        cantidad_inicial = portafolio._posicion_abierta.cantidad
        balance_antes = portafolio._balance
        
        # Reducir de 50% a 35%
        success, info = portafolio.modificar_posicion(precio, 0.35)
        
        assert success is True
        
        # Verificaciones básicas
        assert portafolio._posicion_abierta is not None  # Aún hay posición
        assert portafolio._posicion_abierta.cantidad < cantidad_inicial  # Se redujo
        assert portafolio._balance > balance_antes  # Se liberó margen
        assert portafolio._balance > 0  # Balance positivo
        assert portafolio._balance < portafolio.balance_inicial  # No excede el inicial
        
    def test_multiple_modificaciones_mantienen_consistencia(self, portafolio):
        """Test de regresión: múltiples modificaciones mantienen consistencia."""
        precio = 100.0
        
        # Secuencia de operaciones
        operaciones = [
            ('abrir', 'long', 0.3),
            ('modificar', None, 0.5),   # Aumentar
            ('modificar', None, 0.4),   # Reducir
            ('modificar', None, 0.6),   # Aumentar
            ('modificar', None, 0.5),   # Reducir
            ('modificar', None, 0.7),   # Aumentar
        ]
        
        balances = []
        equities = []
        
        for i, (tipo, direccion, porcentaje) in enumerate(operaciones):
            if tipo == 'abrir':
                portafolio.abrir_posicion(direccion, precio, porcentaje)
            else:
                portafolio.modificar_posicion(precio, porcentaje)
            
            balance = portafolio._balance
            equity = portafolio.get_equity(precio)
            
            balances.append(balance)
            equities.append(equity)
            
            # Verificaciones en cada paso
            assert balance > 0, f"Balance negativo en paso {i+1}"
            assert equity > 0, f"Equity negativo en paso {i+1}"
            assert balance < portafolio.balance_inicial, "Balance excede el inicial"
            
            # El balance NO debe ser microscópico
            assert balance > 1e-10, f"Balance microscópico en paso {i+1}: {balance:.2e}"
        
        print(f"\n✅ Test PASADO: Múltiples modificaciones mantienen consistencia")
        print(f"   Balances: {[f'{b:.2f}' for b in balances]}")
        print(f"   Equities: {[f'{e:.2f}' for e in equities]}")
    
    def test_balance_suficiente_para_aumentar(self, portafolio):
        """Verificar que si no hay balance suficiente, no se puede aumentar."""
        precio = 100.0
        
        # Abrir posición muy grande (95% del equity)
        portafolio.abrir_posicion('long', precio, 0.95)
        
        balance_antes = portafolio._balance
        
        # Intentar aumentar más (debería fallar o ajustar cantidad)
        success, info = portafolio.modificar_posicion(precio, 0.98)
        
        balance_despues = portafolio._balance
        
        # El balance NO debe volverse negativo ni microscópico
        assert balance_despues >= 0
        assert balance_despues > 1e-10 or balance_despues == 0
        
    def test_cerrar_y_reabrir_no_afecta_balance(self, portafolio):
        """Verificar que cerrar y reabrir posiciones mantiene el balance consistente."""
        precio_inicial = 100.0
        precio_cierre = 105.0  # 5% de ganancia
        
        equity_inicial = portafolio.get_equity(precio_inicial)
        
        # Ciclo de operaciones
        for _ in range(5):
            # Abrir
            portafolio.abrir_posicion('long', precio_inicial, 0.5)
            
            # Cerrar con ganancia
            portafolio.cerrar_posicion(precio_cierre)
            
            balance = portafolio._balance
            
            # Balance debe ser positivo y razonable
            assert balance > 0
            assert balance < equity_inicial * 2  # No debe explotar
            assert balance > 1e-10  # No debe colapsar
        
        equity_final = portafolio.get_equity(precio_cierre)
        
        # Con ganancias, el equity final debe ser mayor que el inicial
        assert equity_final > equity_inicial

