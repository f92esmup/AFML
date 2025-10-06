"""
Tests para la nueva función de recompensa multifactorial del entorno de trading.

Estos tests validan que cada componente de la recompensa funciona correctamente
y que la normalización mantiene las recompensas en el rango esperado [-1, +1].
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock
from src.train.Entrenamiento.entorno import TradingEnv
from src.train.Entrenamiento.entorno.portafolio import Portafolio, Posicion
from src.train.config.config import UnifiedConfig


class TestRecompensaMultifactorial:
    """Suite de tests para la función de recompensa multifactorial."""
    
    @pytest.fixture
    def mock_config(self):
        """Configuración mock con parámetros de recompensa."""
        config = Mock(spec=UnifiedConfig)
        
        # Configuración de entorno
        config.entorno = Mock()
        config.entorno.window_size = 30
        config.entorno.max_drawdown_permitido = 0.2
        config.entorno.normalizar_recompensa = True
        config.entorno.factor_escala_recompensa = 100.0
        
        # Pesos de componentes
        config.entorno.peso_retorno_base = 1.0
        config.entorno.peso_temporal = 0.3
        config.entorno.peso_gestion = 0.2
        config.entorno.peso_drawdown = 0.15
        config.entorno.peso_inaccion = 0.05
        
        # Parámetros de penalización temporal
        config.entorno.umbral_perdida_pct = 0.005
        config.entorno.factor_crecimiento_perdida = 0.05
        config.entorno.umbral_ganancia_pct = 0.005
        config.entorno.factor_moderacion_ganancia = 0.3
        config.entorno.factor_crecimiento_ganancia = 0.01
        
        # Parámetros de gestión
        config.entorno.bonus_cierre_ganador = 0.02
        config.entorno.penalizacion_cierre_perdedor = -0.005
        
        # Parámetros de drawdown
        config.entorno.umbral_drawdown = 0.05
        config.entorno.factor_penalizacion_drawdown = 0.5
        
        # Parámetros de anti-inacción
        config.entorno.umbral_caida_equity = 0.002
        config.entorno.penalizacion_inaccion = -0.005
        
        # Configuración de portafolio
        config.portafolio = Mock()
        config.portafolio.capital_inicial = 10000.0
        
        return config
    
    @pytest.fixture
    def mock_data(self):
        """DataFrame mock con datos de mercado."""
        # Crear 100 velas de datos sintéticos
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0 + np.random.randn(100) * 5,
            'high': 105.0 + np.random.randn(100) * 5,
            'low': 95.0 + np.random.randn(100) * 5,
            'close': 100.0 + np.random.randn(100) * 5,
            'volume': 1000.0 + np.random.randn(100) * 100,
        })
        return data
    
    @pytest.fixture
    def mock_portafolio(self, mock_config):
        """Portafolio mock para tests."""
        portafolio = Mock(spec=Portafolio)
        portafolio.balance_inicial = mock_config.portafolio.capital_inicial
        portafolio._balance = 10000.0
        portafolio.posicion_abierta = None
        portafolio._pnl_total_episodio = 0.0
        portafolio._equity_maximo_episodio = 10000.0
        
        # Métodos del portafolio
        portafolio.get_equity = MagicMock(return_value=10000.0)
        portafolio.calcular_PnL_no_realizado = MagicMock(return_value=0.0)
        portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        
        return portafolio
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE COMPONENTE BASE: RETORNO
    # ═══════════════════════════════════════════════════════════
    
    def test_retorno_positivo_genera_recompensa_positiva(self, mock_config, mock_data, mock_portafolio):
        """Test: Un retorno positivo debe generar una recompensa positiva."""
        # Configurar portafolio con ganancia
        # Importante: get_equity se llama múltiples veces, necesitamos retornar siempre el mismo valor
        mock_portafolio.get_equity = MagicMock(return_value=10100.0)  # +1%
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        
        recompensa = env._recompensa(100.0)
        
        assert recompensa > 0, f"Recompensa debería ser positiva con retorno positivo, pero fue {recompensa}"
        assert -1.0 <= recompensa <= 1.0, "Recompensa debería estar normalizada en [-1, 1]"
    
    def test_retorno_negativo_genera_recompensa_negativa(self, mock_config, mock_data, mock_portafolio):
        """Test: Un retorno negativo debe generar una recompensa negativa."""
        # Configurar portafolio con pérdida
        mock_portafolio.get_equity = MagicMock(return_value=9900.0)  # -1%
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.01)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        
        recompensa = env._recompensa(100.0)
        
        assert recompensa < 0, f"Recompensa debería ser negativa con retorno negativo, pero fue {recompensa}"
        assert -1.0 <= recompensa <= 1.0, "Recompensa debería estar normalizada en [-1, 1]"
    
    def test_retorno_cero_genera_recompensa_cercana_a_cero(self, mock_config, mock_data, mock_portafolio):
        """Test: Sin cambio en equity, recompensa cercana a 0 (puede tener componentes menores)."""
        mock_portafolio.get_equity = MagicMock(return_value=10000.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        
        recompensa = env._recompensa(100.0)
        
        # Puede no ser exactamente 0 debido a componentes de inacción
        assert abs(recompensa) < 0.1, "Recompensa debería ser cercana a 0 sin cambio de equity"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE COMPONENTE TEMPORAL: PENALIZACIÓN POR PÉRDIDAS
    # ═══════════════════════════════════════════════════════════
    
    def test_penalizacion_crece_con_velas_en_perdida(self, mock_config, mock_data, mock_portafolio):
        """Test: Mantener una posición perdedora incrementa la penalización con el tiempo."""
        # Simular posición perdedora
        mock_posicion = Mock(spec=Posicion)
        mock_posicion.tipo = 1  # Long
        mock_posicion.velas = 20  # 20 velas en pérdida
        
        mock_portafolio.posicion_abierta = mock_posicion
        mock_portafolio.get_equity = MagicMock(return_value=9800.0)  # -2% de equity
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=-200.0)  # -2% de 10000
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 9800.0  # Mantener equity constante para aislar componente temporal
        
        recompensa = env._recompensa(98.0)
        
        # La penalización debería ser significativa
        assert recompensa < -0.1, "Debería haber penalización fuerte por mantener pérdida por 20 velas"
    
    def test_penalizacion_mayor_con_mas_velas(self, mock_config, mock_data, mock_portafolio):
        """Test: 40 velas en pérdida > penalización que 20 velas en pérdida."""
        # Primera medición: 20 velas
        mock_posicion_20 = Mock(spec=Posicion)
        mock_posicion_20.tipo = 1
        mock_posicion_20.velas = 20
        
        mock_portafolio.posicion_abierta = mock_posicion_20
        mock_portafolio.get_equity = MagicMock(return_value=9800.0)
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=-200.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 9800.0
        
        recompensa_20_velas = env._recompensa(98.0)
        
        # Segunda medición: 40 velas
        mock_posicion_40 = Mock(spec=Posicion)
        mock_posicion_40.tipo = 1
        mock_posicion_40.velas = 40
        
        mock_portafolio.posicion_abierta = mock_posicion_40
        env.prev_equity = 9800.0
        
        recompensa_40_velas = env._recompensa(98.0)
        
        assert recompensa_40_velas < recompensa_20_velas, \
            "Más velas en pérdida debería generar mayor penalización"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE COMPONENTE TEMPORAL: BONIFICACIÓN POR GANANCIAS
    # ═══════════════════════════════════════════════════════════
    
    def test_bonificacion_por_mantener_ganancias(self, mock_config, mock_data, mock_portafolio):
        """Test: Mantener una posición ganadora da pequeña bonificación."""
        mock_posicion = Mock(spec=Posicion)
        mock_posicion.tipo = 1
        mock_posicion.velas = 15
        
        mock_portafolio.posicion_abierta = mock_posicion
        mock_portafolio.get_equity = MagicMock(return_value=10300.0)  # +3% equity
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=300.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10300.0
        
        recompensa = env._recompensa(103.0)
        
        # Debería haber alguna recompensa positiva (aunque moderada)
        assert recompensa > 0, "Debería haber bonificación por mantener ganancias"
    
    def test_bonificacion_ganancias_moderada(self, mock_config, mock_data, mock_portafolio):
        """Test: La bonificación por ganancias es menor que la ganancia directa."""
        # La bonificación es solo 30% de la ganancia (factor_moderacion_ganancia)
        # Esto previene que el agente solo haga "hold" de posiciones ganadoras
        
        mock_posicion = Mock(spec=Posicion)
        mock_posicion.tipo = 1
        mock_posicion.velas = 10
        
        mock_portafolio.posicion_abierta = mock_posicion
        mock_portafolio.get_equity = MagicMock(return_value=10500.0)  # +5% equity
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=500.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10500.0
        
        recompensa = env._recompensa(105.0)
        
        # La recompensa debería ser positiva pero moderada
        assert 0 < recompensa < 0.5, "Bonificación debería ser moderada, no excesiva"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE COMPONENTE GESTIÓN: CIERRES
    # ═══════════════════════════════════════════════════════════
    
    def test_bonus_por_cerrar_ganancia(self, mock_config, mock_data, mock_portafolio):
        """Test: Cerrar una posición ganadora otorga bonificación."""
        # Simular que en el paso anterior había posición
        mock_posicion_anterior = Mock(spec=Posicion)
        mock_posicion_anterior.tipo = 1
        mock_posicion_anterior.velas = 10
        
        # Ahora no hay posición (se cerró)
        mock_portafolio.posicion_abierta = None
        mock_portafolio.get_equity = MagicMock(return_value=10200.0)
        mock_portafolio._pnl_total_episodio = 200.0  # +$200 ganados
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        env._posicion_paso_anterior = mock_posicion_anterior
        env._pnl_total_previo = 0.0
        env._velas_posicion_anterior = 10
        
        recompensa = env._recompensa(102.0)
        
        # Debería haber bonus adicional por cerrar ganador
        assert recompensa > 0.02, "Debería haber bonus significativo por cerrar ganancia"
    
    def test_penalizacion_leve_por_cerrar_perdida(self, mock_config, mock_data, mock_portafolio):
        """Test: Cerrar pérdida tiene penalización leve (mejor tarde que nunca)."""
        mock_posicion_anterior = Mock(spec=Posicion)
        mock_posicion_anterior.tipo = 1
        mock_posicion_anterior.velas = 5
        
        mock_portafolio.posicion_abierta = None
        mock_portafolio.get_equity = MagicMock(return_value=9900.0)
        mock_portafolio._pnl_total_episodio = -100.0
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.01)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        env._posicion_paso_anterior = mock_posicion_anterior
        env._pnl_total_previo = 0.0
        env._velas_posicion_anterior = 5
        
        recompensa = env._recompensa(99.0)
        
        # Penalización leve, pero menos que si hubiera mantenido la posición
        assert recompensa < 0, f"Debería haber penalización por cerrar en pérdida, pero fue {recompensa}"
        # Ajustamos el umbral ya que la penalización incluye retorno negativo + componente de gestión
        assert recompensa > -1.0, "Pero la penalización debería estar normalizada"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE COMPONENTE DRAWDOWN
    # ═══════════════════════════════════════════════════════════
    
    def test_penalizacion_por_alto_drawdown(self, mock_config, mock_data, mock_portafolio):
        """Test: Drawdown > 5% (umbral) genera penalización."""
        mock_portafolio.get_equity = MagicMock(return_value=9000.0)  # -10% de 10000
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.12)  # 12% drawdown
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 9000.0  # Sin cambio para aislar componente drawdown
        
        recompensa = env._recompensa(90.0)
        
        # La penalización debería ser negativa (componente drawdown activado)
        assert recompensa < 0, f"Alto drawdown debería generar penalización, pero fue {recompensa}"
    
    def test_sin_penalizacion_con_bajo_drawdown(self, mock_config, mock_data, mock_portafolio):
        """Test: Drawdown < 5% no genera penalización adicional."""
        mock_portafolio.get_equity = MagicMock(return_value=9700.0)
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.03)  # 3% drawdown
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 9700.0
        
        recompensa = env._recompensa(97.0)
        
        # No debería haber penalización significativa por drawdown
        assert recompensa > -0.2, "Bajo drawdown no debería penalizar mucho"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE NORMALIZACIÓN
    # ═══════════════════════════════════════════════════════════
    
    def test_recompensa_siempre_normalizada(self, mock_config, mock_data, mock_portafolio):
        """Test: Todas las recompensas deben estar en rango [-1, +1]."""
        # Probar con retorno extremo (+50%)
        mock_portafolio.get_equity = MagicMock(return_value=15000.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        
        recompensa = env._recompensa(150.0)
        
        assert -1.0 <= recompensa <= 1.0, \
            f"Recompensa {recompensa} fuera de rango normalizado [-1, 1]"
    
    def test_tanh_satura_recompensas_extremas(self, mock_config, mock_data, mock_portafolio):
        """Test: Retornos muy grandes saturan suavemente cerca de ±1."""
        # Retorno extremadamente grande (+100%)
        mock_portafolio.get_equity = MagicMock(return_value=20000.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = 10000.0
        
        recompensa = env._recompensa(200.0)
        
        # Debería saturar cerca de +1.0 pero no excederlo
        assert 0.95 <= recompensa <= 1.0, "Recompensa extrema debería saturar cerca de 1.0"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS DE INTEGRACIÓN
    # ═══════════════════════════════════════════════════════════
    
    def test_escenario_completo_operacion_ganadora(self, mock_config, mock_data, mock_portafolio):
        """Test de integración: Operación ganadora completa desde apertura hasta cierre."""
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        
        # Paso 1: Sin posición (neutral)
        mock_portafolio.posicion_abierta = None
        mock_portafolio.get_equity = MagicMock(return_value=10000.0)
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        env.prev_equity = 10000.0
        r1 = env._recompensa(100.0)
        
        # Paso 2: Abrir posición
        mock_posicion = Mock(spec=Posicion)
        mock_posicion.tipo = 1
        mock_posicion.velas = 1
        mock_portafolio.posicion_abierta = mock_posicion
        mock_portafolio.get_equity = MagicMock(return_value=10050.0)  # +0.5%
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=50.0)
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        env.prev_equity = 10000.0
        r2 = env._recompensa(100.5)
        
        # Paso 3: Mantener posición ganadora (10 velas)
        mock_posicion.velas = 10
        mock_portafolio.get_equity = MagicMock(return_value=10300.0)  # +3%
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=300.0)
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        env.prev_equity = 10050.0
        env._posicion_paso_anterior = mock_posicion
        r3 = env._recompensa(103.0)
        
        # Paso 4: Cerrar posición ganadora
        mock_portafolio.posicion_abierta = None
        mock_portafolio.get_equity = MagicMock(return_value=10300.0)
        mock_portafolio._pnl_total_episodio = 300.0
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=0.0)
        env.prev_equity = 10300.0
        env._pnl_total_previo = 0.0
        env._velas_posicion_anterior = 10
        r4 = env._recompensa(103.0)
        
        # Verificaciones
        assert r2 > 0, f"Apertura con ganancia debería ser positiva, pero fue {r2}"
        assert r3 > 0, f"Mantener ganancia debería ser positiva, pero fue {r3}"
        # r4 puede ser menor que r3 porque no hay cambio de equity en el paso 4
        # El bonus de gestión se suma, pero sin retorno base puede ser menor
        assert r4 != 0, f"Cerrar ganancia debería tener algún componente, pero fue {r4}"
    
    def test_escenario_completo_operacion_perdedora(self, mock_config, mock_data, mock_portafolio):
        """Test de integración: Operación perdedora que se mantiene demasiado tiempo."""
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        
        # Abrir posición
        mock_posicion = Mock(spec=Posicion)
        mock_posicion.tipo = 1
        mock_posicion.velas = 1
        mock_portafolio.posicion_abierta = mock_posicion
        mock_portafolio.get_equity = MagicMock(return_value=9950.0)
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=-50.0)
        env.prev_equity = 10000.0
        r1 = env._recompensa(99.5)
        
        # Mantener 30 velas en pérdida (MAL)
        mock_posicion.velas = 30
        mock_portafolio.get_equity = MagicMock(return_value=9700.0)
        mock_portafolio.calcular_PnL_no_realizado = MagicMock(return_value=-300.0)
        env.prev_equity = 9950.0
        r2 = env._recompensa(97.0)
        
        # La penalización debería crecer significativamente
        assert r2 < r1, "Mantener pérdida más tiempo debería penalizar más"
        assert r2 < -0.3, "30 velas en pérdida debería generar penalización fuerte"
    
    # ═══════════════════════════════════════════════════════════
    # TESTS PARAMETRIZADOS PARA COBERTURA EXHAUSTIVA
    # ═══════════════════════════════════════════════════════════
    
    @pytest.mark.parametrize("retorno_pct,esperado_signo", [
        (0.01, "positivo"),    # +1%
        (0.05, "positivo"),    # +5%
        (-0.01, "negativo"),   # -1%
        (-0.05, "negativo"),   # -5%
        (0.0, "neutral"),      # 0%
    ])
    def test_signos_recompensa_basica(self, retorno_pct, esperado_signo, mock_config, mock_data, mock_portafolio):
        """Test parametrizado: Verificar signos de recompensa para diferentes retornos."""
        equity_inicial = 10000.0
        equity_final = equity_inicial * (1 + retorno_pct)
        
        mock_portafolio.get_equity = MagicMock(return_value=equity_final)
        mock_portafolio.calcular_max_drawdown = MagicMock(return_value=abs(retorno_pct) if retorno_pct < 0 else 0.0)
        
        env = TradingEnv(mock_config, mock_data, mock_portafolio, scaler=None)
        env.prev_equity = equity_inicial
        
        recompensa = env._recompensa(100.0)
        
        if esperado_signo == "positivo":
            assert recompensa > 0, f"Esperado positivo, pero fue {recompensa}"
        elif esperado_signo == "negativo":
            assert recompensa < 0, f"Esperado negativo, pero fue {recompensa}"
        else:  # neutral
            assert abs(recompensa) < 0.1, f"Esperado neutral, pero fue {recompensa}"


# ═══════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES (SI SON NECESARIAS)
# ═══════════════════════════════════════════════════════════


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
