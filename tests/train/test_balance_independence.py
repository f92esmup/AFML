"""
Test de independencia del balance.

Verifica que el agente produce observaciones y recompensas equivalentes
independientemente del capital inicial usado.
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.train.config.config import UnifiedConfig
from src.train.Entrenamiento.entorno import TradingEnv, Portafolio


class TestBalanceIndependence:
    """Tests para verificar que el sistema es independiente del balance inicial."""
    
    @pytest.fixture
    def datos_mercado(self):
        """Crear datos de mercado sintéticos para testing."""
        np.random.seed(42)
        n_filas = 200
        
        # Generar datos OHLCV sintéticos
        base_price = 50000.0
        data = {
            'timestamp': pd.date_range('2023-01-01', periods=n_filas, freq='1h'),
            'open': base_price + np.random.randn(n_filas) * 100,
            'high': base_price + np.random.randn(n_filas) * 150,
            'low': base_price + np.random.randn(n_filas) * 50,
            'close': base_price + np.random.randn(n_filas) * 100,
            'volume': np.random.rand(n_filas) * 1000,
        }
        df = pd.DataFrame(data)
        
        # Agregar indicadores sintéticos
        df['sma_short'] = df['close'].rolling(10).mean()
        df['sma_long'] = df['close'].rolling(20).mean()
        df['rsi'] = 50 + np.random.randn(n_filas) * 20
        df['macd'] = np.random.randn(n_filas) * 50
        df['macd_signal'] = np.random.randn(n_filas) * 30
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['bb_upper'] = df['close'] + 100
        df['bb_middle'] = df['close']
        df['bb_lower'] = df['close'] - 100
        
        # Eliminar NaN iniciales
        df = df.dropna().reset_index(drop=True)
        
        return df
    
    @pytest.fixture
    def scaler_entrenado(self, datos_mercado):
        """Crear y entrenar un scaler con los datos sintéticos."""
        # Eliminar timestamp para normalización
        data_sin_timestamp = datos_mercado.drop(columns=['timestamp'])
        
        scaler = StandardScaler()
        scaler.fit(data_sin_timestamp)
        
        return scaler
    
    def crear_config(self, capital_inicial: float):
        """Crear configuración con un capital inicial específico."""
        from src.train.config.config import PortafolioConfig, EntornoConfig
        
        # Crear configuración mínima directamente (similar al demo)
        class MockConfig:
            def __init__(self, capital_inicial):
                self.portafolio = PortafolioConfig(
                    capital_inicial=capital_inicial,
                    apalancamiento=2.0,
                    comision=0.0004,
                    slippage=0.0001
                )
                self.entorno = EntornoConfig(
                    window_size=100,
                    max_drawdown_permitido=0.5,
                    factor_aversion_riesgo=2.0,
                    umbral_mantener_posicion=0.05,
                    penalizacion_no_operar=0.0,
                    total_timesteps=10000,
                    normalizar_portfolio=True,
                    normalizar_recompensa=True,
                    penalizacion_pct=0.00001,
                    factor_escala_recompensa=100.0,
                    peso_retorno_base=1.0,
                    peso_temporal=0.3,
                    peso_gestion=0.2,
                    peso_drawdown=0.15,
                    peso_inaccion=0.05,
                    umbral_perdida_pct=0.005,
                    factor_crecimiento_perdida=0.05,
                    umbral_ganancia_pct=0.005,
                    factor_moderacion_ganancia=0.3,
                    factor_crecimiento_ganancia=0.01,
                    bonus_cierre_ganador=0.02,
                    penalizacion_cierre_perdedor=-0.005,
                    umbral_drawdown=0.05,
                    factor_penalizacion_drawdown=2.0,
                    umbral_caida_equity=0.01,
                    penalizacion_inaccion=-0.01  # Debe ser negativo
                )
        
        return MockConfig(capital_inicial)
    
    def test_observacion_normalizada_identica(self, datos_mercado, scaler_entrenado):
        """
        Test crítico: Verifica que la observación de portfolio es idéntica
        independientemente del capital inicial.
        """
        # Crear dos entornos con diferentes capitales
        config_10k = self.crear_config(capital_inicial=10000.0)
        config_100 = self.crear_config(capital_inicial=100.0)
        
        # Crear portfolios
        portafolio_10k = Portafolio(config_10k)
        portafolio_100 = Portafolio(config_100)
        
        # Crear entornos
        env_10k = TradingEnv(config_10k, datos_mercado.copy(), portafolio_10k, scaler_entrenado)
        env_100 = TradingEnv(config_100, datos_mercado.copy(), portafolio_100, scaler_entrenado)
        
        # Reset inicial
        obs_10k, _ = env_10k.reset()
        obs_100, _ = env_100.reset()
        
        # VERIFICACIÓN 1: Portfolio observation debe ser idéntico
        # [equity_normalizado, pnl_pct, posicion_abierta]
        np.testing.assert_array_almost_equal(
            obs_10k['portfolio'], 
            obs_100['portfolio'],
            decimal=6,
            err_msg="Portfolio observation debe ser idéntico independientemente del capital inicial"
        )
        
        # VERIFICACIÓN 2: Equity normalizado debe ser 1.0 al inicio
        assert obs_10k['portfolio'][0] == pytest.approx(1.0, abs=1e-6), \
            "Equity normalizado inicial debe ser 1.0 (10k/10k)"
        assert obs_100['portfolio'][0] == pytest.approx(1.0, abs=1e-6), \
            "Equity normalizado inicial debe ser 1.0 (100/100)"
        
        # VERIFICACIÓN 3: PnL % debe ser 0.0 al inicio
        assert obs_10k['portfolio'][1] == pytest.approx(0.0, abs=1e-6), \
            "PnL % inicial debe ser 0.0"
        assert obs_100['portfolio'][1] == pytest.approx(0.0, abs=1e-6), \
            "PnL % inicial debe ser 0.0"
        
        # VERIFICACIÓN 4: Market observation debe ser idéntico (mismos datos + scaler)
        np.testing.assert_array_almost_equal(
            obs_10k['market'], 
            obs_100['market'],
            decimal=6,
            err_msg="Market observation debe ser idéntico (mismo scaler)"
        )
    
    def test_recompensa_porcentual_identica(self, datos_mercado, scaler_entrenado):
        """
        Test crítico: Verifica que la recompensa es idéntica cuando los
        retornos porcentuales son iguales.
        """
        # Crear dos entornos con diferentes capitales
        config_10k = self.crear_config(capital_inicial=10000.0)
        config_100 = self.crear_config(capital_inicial=100.0)
        
        portafolio_10k = Portafolio(config_10k)
        portafolio_100 = Portafolio(config_100)
        
        env_10k = TradingEnv(config_10k, datos_mercado.copy(), portafolio_10k, scaler_entrenado)
        env_100 = TradingEnv(config_100, datos_mercado.copy(), portafolio_100, scaler_entrenado)
        
        # Reset
        env_10k.reset()
        env_100.reset()
        
        # Ejecutar la MISMA acción (abrir LONG con 50% del equity)
        accion = np.array([0.5])
        
        obs1_10k, reward1_10k, done1_10k, truncated1_10k, info1_10k = env_10k.step(accion)
        obs1_100, reward1_100, done1_100, truncated1_100, info1_100 = env_100.step(accion)
        
        # VERIFICACIÓN 1: Recompensa debe ser idéntica
        assert reward1_10k == pytest.approx(reward1_100, abs=1e-6), \
            f"Recompensa debe ser idéntica: {reward1_10k:.6f} vs {reward1_100:.6f}"
        
        # VERIFICACIÓN 2: Portfolio observation debe seguir siendo proporcional
        # Después de abrir posición, equity puede haber cambiado ligeramente (comisiones)
        # pero el ratio debe ser similar
        np.testing.assert_array_almost_equal(
            obs1_10k['portfolio'], 
            obs1_100['portfolio'],
            decimal=5,  # Permitir ligeras diferencias por redondeo
            err_msg="Portfolio observation debe seguir siendo proporcional"
        )
    
    def test_accion_genera_mismo_porcentaje_equity(self, datos_mercado, scaler_entrenado):
        """
        Test crítico: Verifica que una acción genera el mismo % de uso del equity
        independientemente del capital inicial.
        """
        config_10k = self.crear_config(capital_inicial=10000.0)
        config_100 = self.crear_config(capital_inicial=100.0)
        
        portafolio_10k = Portafolio(config_10k)
        portafolio_100 = Portafolio(config_100)
        
        env_10k = TradingEnv(config_10k, datos_mercado.copy(), portafolio_10k, scaler_entrenado)
        env_100 = TradingEnv(config_100, datos_mercado.copy(), portafolio_100, scaler_entrenado)
        
        env_10k.reset()
        env_100.reset()
        
        # Ejecutar acción: LONG con intensidad 0.7 (70% del equity)
        accion = np.array([0.7])
        
        env_10k.step(accion)
        env_100.step(accion)
        
        # Obtener información de las posiciones abiertas
        precio = float(datos_mercado.iloc[env_10k.paso_actual]['close'])
        
        # VERIFICACIÓN: Porcentaje del equity usado debe ser similar
        # (considerando comisiones y slippage proporcionales)
        
        if portafolio_10k.posicion_abierta:
            margen_usado_10k = portafolio_10k.posicion_abierta.margen
            equity_10k = portafolio_10k.get_equity(precio)
            pct_usado_10k = margen_usado_10k / 10000.0  # Respecto al inicial
        
        if portafolio_100.posicion_abierta:
            margen_usado_100 = portafolio_100.posicion_abierta.margen
            equity_100 = portafolio_100.get_equity(precio)
            pct_usado_100 = margen_usado_100 / 100.0  # Respecto al inicial
        
        # Los porcentajes deben ser muy similares
        assert pct_usado_10k == pytest.approx(pct_usado_100, rel=0.01), \
            f"Porcentaje de equity usado debe ser similar: {pct_usado_10k:.4f} vs {pct_usado_100:.4f}"
    
    def test_secuencia_acciones_consistente(self, datos_mercado, scaler_entrenado):
        """
        Test de integración: Verifica que una secuencia de acciones produce
        comportamiento consistente independientemente del capital inicial.
        """
        config_10k = self.crear_config(capital_inicial=10000.0)
        config_100 = self.crear_config(capital_inicial=100.0)
        
        portafolio_10k = Portafolio(config_10k)
        portafolio_100 = Portafolio(config_100)
        
        env_10k = TradingEnv(config_10k, datos_mercado.copy(), portafolio_10k, scaler_entrenado)
        env_100 = TradingEnv(config_100, datos_mercado.copy(), portafolio_100, scaler_entrenado)
        
        env_10k.reset()
        env_100.reset()
        
        # Secuencia de acciones
        acciones = [
            np.array([0.6]),   # LONG 60%
            np.array([0.3]),   # LONG 30% (aumentar)
            np.array([0.1]),   # LONG 10% (mantener/reducir)
            np.array([-0.5]),  # SHORT 50% (cerrar LONG)
        ]
        
        rewards_10k = []
        rewards_100 = []
        
        for accion in acciones:
            _, r1, done1, _, _ = env_10k.step(accion)
            _, r2, done2, _, _ = env_100.step(accion)
            
            rewards_10k.append(r1)
            rewards_100.append(r2)
            
            if done1 or done2:
                break
        
        # VERIFICACIÓN: Las recompensas deben ser muy similares
        for i, (r1, r2) in enumerate(zip(rewards_10k, rewards_100)):
            assert r1 == pytest.approx(r2, abs=1e-4), \
                f"Paso {i}: Recompensa debe ser similar: {r1:.6f} vs {r2:.6f}"
    
    def test_normalizacion_desactivada_rompe_independencia(self, datos_mercado, scaler_entrenado):
        """
        Test negativo: Verifica que al desactivar la normalización,
        la independencia se ROMPE (como debe ser).
        """
        config_10k = self.crear_config(capital_inicial=10000.0)
        config_100 = self.crear_config(capital_inicial=100.0)
        
        # DESACTIVAR normalización
        config_10k.entorno.normalizar_portfolio = False
        config_100.entorno.normalizar_portfolio = False
        
        portafolio_10k = Portafolio(config_10k)
        portafolio_100 = Portafolio(config_100)
        
        env_10k = TradingEnv(config_10k, datos_mercado.copy(), portafolio_10k, scaler_entrenado)
        env_100 = TradingEnv(config_100, datos_mercado.copy(), portafolio_100, scaler_entrenado)
        
        obs_10k, _ = env_10k.reset()
        obs_100, _ = env_100.reset()
        
        # VERIFICACIÓN: Portfolio observation debe ser DIFERENTE
        # equity sin normalizar: 10000 vs 100
        assert obs_10k['portfolio'][0] != pytest.approx(obs_100['portfolio'][0]), \
            "Sin normalización, equity debe ser diferente (10000 vs 100)"
        
        # Valores absolutos
        assert obs_10k['portfolio'][0] == pytest.approx(10000.0), \
            "Equity sin normalizar debe ser 10000"
        assert obs_100['portfolio'][0] == pytest.approx(100.0), \
            "Equity sin normalizar debe ser 100"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
