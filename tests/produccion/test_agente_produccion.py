"""Tests para el agente de producción."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.produccion.agente_produccion import AgenteProduccion
from src.produccion.config.config import ProductionConfig


class TestAgenteProduccion:
    """Tests para la clase AgenteProduccion."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/fake/path/modelo.zip",
            scaler_path="/fake/path/scaler.pkl",
            is_live=False
        )
        return config
    
    def test_init_loads_model(self, production_config, mock_sac_model):
        """Test de inicialización y carga del modelo."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            
            agente = AgenteProduccion(production_config)
            
            # Verificar que se cargó el modelo
            mock_load.assert_called_once_with("/fake/path/modelo.zip")
            assert agente.model is not None
            assert agente.umbral_mantener == 0.1
            
    def test_init_model_not_found(self, production_config):
        """Test de error cuando no se encuentra el modelo."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.side_effect = FileNotFoundError("Model not found")
            
            with pytest.raises(FileNotFoundError):
                AgenteProduccion(production_config)
                
    def test_predict(self, production_config, mock_sac_model):
        """Test de predicción del agente."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            
            agente = AgenteProduccion(production_config)
            
            # Crear observación mock
            observacion = {
                "market": np.random.randn(30, 14).astype(np.float32),
                "portfolio": np.array([1.0, 0.0, 0.0], dtype=np.float32)
            }
            
            accion = agente.predict(observacion)
            
            # Verificar que se llamó al modelo
            mock_sac_model.predict.assert_called_once()
            
            # Verificar que retorna un float
            assert isinstance(accion, float)
            assert -1.0 <= accion <= 1.0
            
    def test_predict_deterministic(self, production_config, mock_sac_model):
        """Test que predict usa deterministic=True."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            
            agente = AgenteProduccion(production_config)
            
            observacion = {
                "market": np.random.randn(30, 14).astype(np.float32),
                "portfolio": np.array([1.0, 0.0, 0.0], dtype=np.float32)
            }
            
            agente.predict(observacion)
            
            # Verificar que se usó deterministic=True
            call_kwargs = mock_sac_model.predict.call_args[1]
            assert call_kwargs.get("deterministic") is True
            
    def test_predict_error_handling(self, production_config, mock_sac_model):
        """Test de manejo de errores en predicción."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            
            agente = AgenteProduccion(production_config)
            
            # Hacer que predict lance excepción
            mock_sac_model.predict.side_effect = Exception("Model error")
            
            observacion = {
                "market": np.random.randn(30, 14).astype(np.float32),
                "portfolio": np.array([1.0, 0.0, 0.0], dtype=np.float32)
            }
            
            accion = agente.predict(observacion)
            
            # Debe retornar acción neutra en caso de error
            assert accion == 0.0


class TestInterpretarAccion:
    """Tests para la interpretación de acciones."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/fake/path/modelo.zip",
            scaler_path="/fake/path/scaler.pkl",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def agente(self, production_config, mock_sac_model):
        """Fixture del agente."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            return AgenteProduccion(production_config)
    
    def test_interpretar_accion_mantener(self, agente):
        """Test de acción mantener (dentro del umbral)."""
        resultado = agente.interpretar_accion(
            accion=0.05,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "mantener"
        assert resultado["operacion"] == "mantener"
        assert resultado["debe_ejecutar"] is False
        
    def test_interpretar_accion_abrir_long(self, agente):
        """Test de abrir posición LONG."""
        resultado = agente.interpretar_accion(
            accion=0.8,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "long"
        assert resultado["operacion"] == "abrir_long"
        assert resultado["debe_ejecutar"] is True
        assert resultado["intensidad"] == 0.8
        
    def test_interpretar_accion_abrir_short(self, agente):
        """Test de abrir posición SHORT."""
        resultado = agente.interpretar_accion(
            accion=-0.8,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "short"
        assert resultado["operacion"] == "abrir_short"
        assert resultado["debe_ejecutar"] is True
        assert resultado["intensidad"] == 0.8
        
    def test_interpretar_accion_aumentar_long(self, agente):
        """Test de aumentar posición LONG existente."""
        resultado = agente.interpretar_accion(
            accion=0.7,
            tiene_posicion_abierta=True,
            tipo_posicion_activa="LONG"
        )
        
        assert resultado["tipo_accion"] == "long"
        assert resultado["operacion"] == "aumentar_long"
        assert resultado["debe_ejecutar"] is True
        
    def test_interpretar_accion_aumentar_short(self, agente):
        """Test de aumentar posición SHORT existente."""
        resultado = agente.interpretar_accion(
            accion=-0.7,
            tiene_posicion_abierta=True,
            tipo_posicion_activa="SHORT"
        )
        
        assert resultado["tipo_accion"] == "short"
        assert resultado["operacion"] == "aumentar_short"
        assert resultado["debe_ejecutar"] is True
        
    def test_interpretar_accion_cerrar_short_abrir_long(self, agente):
        """Test de cerrar SHORT cuando la acción indica LONG (solo cierra, no reabre)."""
        resultado = agente.interpretar_accion(
            accion=0.8,
            tiene_posicion_abierta=True,
            tipo_posicion_activa="SHORT"
        )
        
        # Solo debe cerrar, NO abrir nueva posición (una acción por paso)
        assert resultado["tipo_accion"] == "long"
        assert resultado["operacion"] == "cerrar_short"
        assert resultado["debe_ejecutar"] is True
        
    def test_interpretar_accion_cerrar_long_abrir_short(self, agente):
        """Test de cerrar LONG cuando la acción indica SHORT (solo cierra, no reabre)."""
        resultado = agente.interpretar_accion(
            accion=-0.8,
            tiene_posicion_abierta=True,
            tipo_posicion_activa="LONG"
        )
        
        # Solo debe cerrar, NO abrir nueva posición (una acción por paso)
        assert resultado["tipo_accion"] == "short"
        assert resultado["operacion"] == "cerrar_long"
        assert resultado["debe_ejecutar"] is True
        
    def test_interpretar_accion_umbral_exacto_positivo(self, agente):
        """Test con acción exactamente en el umbral positivo."""
        # Exactamente en el umbral (0.1)
        resultado = agente.interpretar_accion(
            accion=0.1,
            tiene_posicion_abierta=False
        )
        
        # Debe ser mantener (< no es <=)
        assert resultado["tipo_accion"] == "mantener"
        
    def test_interpretar_accion_umbral_exacto_negativo(self, agente):
        """Test con acción exactamente en el umbral negativo."""
        resultado = agente.interpretar_accion(
            accion=-0.1,
            tiene_posicion_abierta=False
        )
        
        # Debe ser mantener
        assert resultado["tipo_accion"] == "mantener"
        
    def test_interpretar_accion_justo_por_encima_umbral(self, agente):
        """Test con acción justo por encima del umbral."""
        resultado = agente.interpretar_accion(
            accion=0.11,
            tiene_posicion_abierta=False
        )
        
        # Debe ejecutar LONG
        assert resultado["tipo_accion"] == "long"
        assert resultado["debe_ejecutar"] is True
        
    def test_interpretar_accion_justo_por_debajo_umbral(self, agente):
        """Test con acción justo por debajo del umbral."""
        resultado = agente.interpretar_accion(
            accion=-0.11,
            tiene_posicion_abierta=False
        )
        
        # Debe ejecutar SHORT
        assert resultado["tipo_accion"] == "short"
        assert resultado["debe_ejecutar"] is True


class TestInterpretarAccionEdgeCases:
    """Tests de casos extremos en interpretación."""
    
    @pytest.fixture
    def production_config(self, config_metadata_dict):
        """Fixture de configuración de producción."""
        from src.produccion.config.config import ProductionConfig
        config = ProductionConfig(
            **config_metadata_dict,
            train_id="test_train",
            model_path="/fake/path/modelo.zip",
            scaler_path="/fake/path/scaler.pkl",
            is_live=False
        )
        return config
    
    @pytest.fixture
    def agente(self, production_config, mock_sac_model):
        """Fixture del agente."""
        with patch("src.produccion.agente_produccion.SAC.load") as mock_load:
            mock_load.return_value = mock_sac_model
            return AgenteProduccion(production_config)
    
    def test_accion_maxima_long(self, agente):
        """Test con acción máxima (1.0)."""
        resultado = agente.interpretar_accion(
            accion=1.0,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "long"
        assert resultado["intensidad"] == 1.0
        
    def test_accion_maxima_short(self, agente):
        """Test con acción mínima (-1.0)."""
        resultado = agente.interpretar_accion(
            accion=-1.0,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "short"
        assert resultado["intensidad"] == 1.0
        
    def test_accion_cero(self, agente):
        """Test con acción exactamente cero."""
        resultado = agente.interpretar_accion(
            accion=0.0,
            tiene_posicion_abierta=False
        )
        
        assert resultado["tipo_accion"] == "mantener"
        assert resultado["intensidad"] == 0.0
        
    def test_posicion_sin_tipo(self, agente):
        """Test con posición abierta pero sin tipo especificado."""
        resultado = agente.interpretar_accion(
            accion=0.8,
            tiene_posicion_abierta=True,
            tipo_posicion_activa=None
        )
        
        # Debe manejar el caso (probablemente como si no hubiera posición)
        assert resultado is not None
        assert "tipo_accion" in resultado
