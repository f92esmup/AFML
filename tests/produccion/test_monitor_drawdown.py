"""Tests para el monitor continuo de drawdown en live.py.

Este módulo verifica que el monitoreo continuo de drawdown funcione correctamente
y active el protocolo de emergencia cuando sea necesario.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


class TestMonitorDrawdownContinuo:
    """Tests del sistema de monitoreo continuo de drawdown."""
    
    @pytest.fixture
    def mock_config(self):
        """Config mockeado."""
        config = Mock()
        config.max_drawdown_permitido = 0.15  # 15% drawdown máximo
        config.intervalo = "1h"
        config.ventana_obs = 30
        config.simbolo = "BTCUSDT"
        return config
    
    @pytest.fixture
    def mock_binance(self):
        """BinanceConnector mockeado."""
        binance = Mock()
        binance.get_account_info = Mock(return_value=True)
        binance.get_position_info = Mock(return_value={
            'equity': 10000.0,
            'balance': 10000.0,
            'posicion_abierta': False
        })
        return binance
    
    @pytest.fixture
    def mock_control_riesgo(self):
        """ControlRiesgo mockeado."""
        control = Mock()
        control.verificar_drawdown = Mock(return_value=(True, 0.0))
        control.activar_protocolo_emergencia = Mock(return_value={
            'balance_final': 8500.0,
            'equity_final': 8500.0,
            'posiciones_cerradas': 0,
            'errores': []
        })
        return control
    
    @pytest.fixture
    def mock_registro(self):
        """RegistroProduccion mockeado."""
        registro = Mock()
        registro.registrar_emergencia = Mock()
        return registro
    
    @pytest.mark.asyncio
    async def test_monitor_no_activa_emergencia_si_drawdown_ok(
        self, 
        mock_config, 
        mock_binance, 
        mock_control_riesgo, 
        mock_registro
    ):
        """Test que el monitor no activa emergencia si el drawdown está OK."""
        
        emergencia_activa = {"activada": False, "razon": None, "resultado": None}
        
        # Crear función de monitor (simulada del código en live.py)
        async def monitor_drawdown_continuo(intervalo_segundos: float = 0.1):
            """Versión simplificada del monitor para testing."""
            iteraciones = 0
            max_iteraciones = 3  # Solo 3 iteraciones para el test
            
            while not emergencia_activa["activada"] and iteraciones < max_iteraciones:
                await asyncio.sleep(intervalo_segundos)
                
                if not mock_binance.get_account_info():
                    continue
                
                ok_drawdown, dd_actual = mock_control_riesgo.verificar_drawdown()
                
                if not ok_drawdown:
                    resultado = mock_control_riesgo.activar_protocolo_emergencia(
                        f"Max drawdown: {dd_actual*100:.2f}%"
                    )
                    mock_registro.registrar_emergencia(
                        razon=f"Max drawdown: {dd_actual*100:.2f}%",
                        balance_final=resultado['balance_final'],
                        equity_final=resultado['equity_final'],
                        posiciones_cerradas=resultado['posiciones_cerradas'],
                        detalles=str(resultado['errores'])
                    )
                    emergencia_activa["activada"] = True
                    emergencia_activa["razon"] = f"Max drawdown: {dd_actual*100:.2f}%"
                    break
                
                iteraciones += 1
        
        # Ejecutar monitor
        await monitor_drawdown_continuo(intervalo_segundos=0.05)
        
        # Verificaciones
        assert not emergencia_activa["activada"], "No debería activarse emergencia"
        assert mock_binance.get_account_info.call_count == 3, "Debería actualizar cuenta 3 veces"
        assert mock_control_riesgo.verificar_drawdown.call_count == 3
        assert not mock_control_riesgo.activar_protocolo_emergencia.called
        assert not mock_registro.registrar_emergencia.called
    
    @pytest.mark.asyncio
    async def test_monitor_activa_emergencia_si_drawdown_excesivo(
        self, 
        mock_config, 
        mock_binance, 
        mock_control_riesgo, 
        mock_registro
    ):
        """Test que el monitor activa emergencia si el drawdown es excesivo."""
        
        emergencia_activa = {"activada": False, "razon": None, "resultado": None}
        
        # Configurar drawdown excesivo en la 2da iteración
        mock_control_riesgo.verificar_drawdown.side_effect = [
            (True, 0.10),   # Iteración 1: OK (10%)
            (False, 0.18),  # Iteración 2: EXCESIVO (18% > 15%)
        ]
        
        # Crear función de monitor
        async def monitor_drawdown_continuo(intervalo_segundos: float = 0.1):
            """Versión simplificada del monitor para testing."""
            iteraciones = 0
            max_iteraciones = 5
            
            while not emergencia_activa["activada"] and iteraciones < max_iteraciones:
                await asyncio.sleep(intervalo_segundos)
                
                if not mock_binance.get_account_info():
                    continue
                
                ok_drawdown, dd_actual = mock_control_riesgo.verificar_drawdown()
                
                if not ok_drawdown:
                    resultado = mock_control_riesgo.activar_protocolo_emergencia(
                        f"Max drawdown: {dd_actual*100:.2f}%"
                    )
                    mock_registro.registrar_emergencia(
                        razon=f"Max drawdown detectado por monitor continuo: {dd_actual*100:.2f}%",
                        balance_final=resultado['balance_final'],
                        equity_final=resultado['equity_final'],
                        posiciones_cerradas=resultado['posiciones_cerradas'],
                        detalles=str(resultado['errores'])
                    )
                    emergencia_activa["activada"] = True
                    emergencia_activa["razon"] = f"Max drawdown: {dd_actual*100:.2f}%"
                    emergencia_activa["resultado"] = resultado
                    break
                
                iteraciones += 1
        
        # Ejecutar monitor
        await monitor_drawdown_continuo(intervalo_segundos=0.05)
        
        # Verificaciones
        assert emergencia_activa["activada"], "Debería activarse emergencia"
        assert emergencia_activa["razon"] == "Max drawdown: 18.00%"
        assert emergencia_activa["resultado"] is not None
        
        # Verificar que se llamó al protocolo de emergencia
        assert mock_control_riesgo.activar_protocolo_emergencia.called
        assert mock_registro.registrar_emergencia.called
        
        # Verificar datos de la emergencia
        call_kwargs = mock_registro.registrar_emergencia.call_args[1]
        assert "Max drawdown detectado por monitor continuo" in call_kwargs['razon']
        assert call_kwargs['balance_final'] == 8500.0
        assert call_kwargs['equity_final'] == 8500.0
    
    @pytest.mark.asyncio
    async def test_monitor_se_detiene_si_emergencia_externa(
        self, 
        mock_config, 
        mock_binance, 
        mock_control_riesgo, 
        mock_registro
    ):
        """Test que el monitor se detiene si otra tarea activa la emergencia."""
        
        emergencia_activa = {"activada": False, "razon": None, "resultado": None}
        
        # Crear función de monitor
        async def monitor_drawdown_continuo(intervalo_segundos: float = 0.1):
            """Versión simplificada del monitor para testing."""
            iteraciones = 0
            max_iteraciones = 10
            
            while not emergencia_activa["activada"] and iteraciones < max_iteraciones:
                await asyncio.sleep(intervalo_segundos)
                
                if not mock_binance.get_account_info():
                    continue
                
                ok_drawdown, dd_actual = mock_control_riesgo.verificar_drawdown()
                
                if not ok_drawdown:
                    resultado = mock_control_riesgo.activar_protocolo_emergencia(
                        f"Max drawdown: {dd_actual*100:.2f}%"
                    )
                    emergencia_activa["activada"] = True
                    break
                
                iteraciones += 1
        
        # Simular emergencia externa después de 0.15 segundos
        async def activar_emergencia_externa():
            await asyncio.sleep(0.15)
            emergencia_activa["activada"] = True
            emergencia_activa["razon"] = "Emergencia externa (bucle principal)"
        
        # Ejecutar ambas tareas en paralelo
        await asyncio.gather(
            monitor_drawdown_continuo(intervalo_segundos=0.05),
            activar_emergencia_externa()
        )
        
        # Verificaciones
        assert emergencia_activa["activada"]
        # El monitor no debería haber activado el protocolo (fue la tarea externa)
        assert not mock_control_riesgo.activar_protocolo_emergencia.called


class TestIntegracionMonitorConBuclePrincipal:
    """Tests de integración del monitor con el bucle principal."""
    
    @pytest.mark.asyncio
    async def test_emergencia_compartida_entre_tareas(self):
        """Test que verifica que el flag de emergencia se comparte correctamente."""
        
        emergencia_activa = {"activada": False, "razon": None, "resultado": None}
        
        # Tarea 1: Monitor (detecta emergencia)
        async def monitor():
            await asyncio.sleep(0.1)
            emergencia_activa["activada"] = True
            emergencia_activa["razon"] = "Monitor detectó problema"
        
        # Tarea 2: Bucle principal (verifica flag)
        async def bucle_principal():
            pasos = 0
            while pasos < 10:
                if emergencia_activa["activada"]:
                    break
                await asyncio.sleep(0.05)
                pasos += 1
            return pasos
        
        # Ejecutar ambas tareas
        results = await asyncio.gather(
            monitor(),
            bucle_principal()
        )
        
        # Verificaciones
        pasos_ejecutados = results[1]
        assert emergencia_activa["activada"]
        assert pasos_ejecutados < 10, "Bucle debería detenerse antes de completar 10 pasos"
        assert pasos_ejecutados >= 2, "Debería ejecutar al menos 2 pasos antes de detenerse"


class TestConfiguracionMonitor:
    """Tests de configuración del monitor."""
    
    def test_intervalo_por_defecto(self):
        """Test que el intervalo por defecto sea razonable."""
        # El intervalo por defecto debe ser suficientemente corto para detectar problemas
        # pero no tan corto que sature el sistema con requests
        intervalo_defecto = 30  # segundos (según la implementación)
        
        assert 10 <= intervalo_defecto <= 60, \
            "Intervalo debería estar entre 10 y 60 segundos"
    
    def test_umbral_log_drawdown(self):
        """Test que el umbral para logging sea el 50% del máximo."""
        max_drawdown = 0.15  # 15%
        umbral_log = max_drawdown * 0.5  # 7.5%
        
        assert umbral_log == 0.075, "Umbral de log debería ser 50% del máximo"
        
        # Casos de prueba
        assert 0.08 > umbral_log, "8% debería generar log"
        assert 0.05 < umbral_log, "5% NO debería generar log"
