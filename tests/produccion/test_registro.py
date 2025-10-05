"""Tests para el sistema de registro."""

import pytest
import os
import csv
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.produccion.Registro import RegistroProduccion


class TestRegistroProduccion:
    """Tests para la clase RegistroProduccion."""
    
    @pytest.fixture
    def temp_train_dir(self, tmp_path):
        """Fixture de directorio temporal de entrenamiento."""
        train_id = "test_train_id"
        train_dir = tmp_path / "entrenamientos" / train_id
        train_dir.mkdir(parents=True, exist_ok=True)
        
        # Cambiar al directorio temporal
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        yield train_id, str(tmp_path)
        
        # Restaurar directorio original
        os.chdir(original_cwd)
        
    def test_init_creates_directories(self, temp_train_dir):
        """Test que init crea los directorios necesarios."""
        train_id, base_path = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        # Verificar que se creó el directorio de producción
        prod_dir = Path(base_path) / "entrenamientos" / train_id / "produccion"
        assert prod_dir.exists()
        assert prod_dir.is_dir()
        
    def test_init_creates_csv_files(self, temp_train_dir):
        """Test que init crea los archivos CSV."""
        train_id, base_path = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        # Verificar que existen los archivos CSV
        registro_path = Path(registro.registro_path)
        emergencia_path = Path(registro.emergencia_path)
        
        assert registro_path.exists()
        assert emergencia_path.exists()
        
    def test_csv_headers_principal(self, temp_train_dir):
        """Test que el CSV principal tiene los encabezados correctos."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        # Leer headers
        with open(registro.registro_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
        # Verificar algunos campos clave
        assert "timestamp" in headers
        assert "paso" in headers
        assert "action" in headers
        assert "balance" in headers
        assert "equity" in headers
        assert "tipo_accion" in headers
        assert "operacion" in headers
        
    def test_csv_headers_emergencia(self, temp_train_dir):
        """Test que el CSV de emergencias tiene los encabezados correctos."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        with open(registro.emergencia_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
        assert "timestamp" in headers
        assert "razon" in headers
        assert "balance_final" in headers
        assert "equity_final" in headers
        
    def test_registrar_paso(self, temp_train_dir):
        """Test de registro de un paso completo."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        info_dict = {
            "entorno": {
                "timestamp": "2023-01-01T12:00:00",
                "paso": 1,
                "episodio": 0,
                "action": 0.5,
                "precio": 50000.0,
                "recompensa": None,
                "terminated": False,
                "truncated": False,
                "status": "running",
            },
            "portafolio": {
                "balance": 10000.0,
                "equity": 10500.0,
                "max_drawdown": 0.05,
                "pnl_total": 500.0,
                "posicion_abierta": True,
                "tipo_posicion_activa": "LONG",
            },
            "operacion": {
                "tipo_accion": "long",
                "operacion": "abrir_long",
                "resultado": True,
            }
        }
        
        registro.registrar_paso(info_dict)
        
        # Verificar que se escribió el registro
        with open(registro.registro_path, 'r') as f:
            lines = f.readlines()
            
        # Debe haber header + 1 fila de datos
        assert len(lines) == 2
        
    def test_registrar_paso_multiple(self, temp_train_dir):
        """Test de registro de múltiples pasos."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        # Registrar 5 pasos
        for i in range(5):
            info_dict = {
                "entorno": {
                    "timestamp": f"2023-01-01T12:0{i}:00",
                    "paso": i,
                    "action": 0.5,
                    "precio": 50000.0 + i * 100,
                },
                "portafolio": {
                    "balance": 10000.0 + i * 100,
                    "equity": 10000.0 + i * 100,
                },
                "operacion": {
                    "tipo_accion": "mantener",
                }
            }
            
            registro.registrar_paso(info_dict)
            
        # Verificar que se escribieron todos
        with open(registro.registro_path, 'r') as f:
            lines = f.readlines()
            
        # Header + 5 filas
        assert len(lines) == 6
        
    def test_registrar_emergencia(self, temp_train_dir):
        """Test de registro de emergencia."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        registro.registrar_emergencia(
            razon="Max drawdown excedido",
            balance_final=8000.0,
            equity_final=8000.0,
            posiciones_cerradas=1,
            detalles="Se cerró posición LONG"
        )
        
        # Verificar que se escribió
        with open(registro.emergencia_path, 'r') as f:
            lines = f.readlines()
            
        # Header + 1 fila
        assert len(lines) == 2
        
        # Verificar contenido
        reader = csv.DictReader(open(registro.emergencia_path))
        row = next(reader)
        
        assert row["razon"] == "Max drawdown excedido"
        assert float(row["balance_final"]) == 8000.0
        assert float(row["equity_final"]) == 8000.0
        assert int(row["posiciones_cerradas"]) == 1
        
    def test_registrar_emergencia_multiple(self, temp_train_dir):
        """Test de registro de múltiples emergencias."""
        train_id, _ = temp_train_dir
        
        registro = RegistroProduccion(train_id)
        
        # Registrar 3 emergencias
        for i in range(3):
            registro.registrar_emergencia(
                razon=f"Emergencia {i}",
                balance_final=8000.0 - i * 100,
                equity_final=8000.0 - i * 100,
                posiciones_cerradas=i
            )
            
        with open(registro.emergencia_path, 'r') as f:
            lines = f.readlines()
            
        # Header + 3 filas
        assert len(lines) == 4


class TestEstadisticasSesion:
    """Tests para obtención de estadísticas de sesión."""
    
    @pytest.fixture
    def temp_train_dir(self, tmp_path):
        """Fixture de directorio temporal de entrenamiento."""
        train_id = "test_train_id"
        train_dir = tmp_path / "entrenamientos" / train_id
        train_dir.mkdir(parents=True, exist_ok=True)
        
        # Cambiar al directorio temporal
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        yield train_id, str(tmp_path)
        
        # Restaurar directorio original
        os.chdir(original_cwd)
    
    @pytest.fixture
    def registro_con_datos(self, temp_train_dir):
        """Fixture de registro con datos."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        # Agregar algunos registros
        for i in range(10):
            info_dict = {
                "entorno": {
                    "timestamp": f"2023-01-01T12:0{i % 6}:00",
                    "paso": i,
                    "action": 0.5 if i % 2 == 0 else -0.5,
                    "precio": 50000.0 + i * 100,
                },
                "portafolio": {
                    "balance": 10000.0 + i * 100,
                    "equity": 10000.0 + i * 150,
                },
                "operacion": {
                    "tipo_accion": "long" if i % 2 == 0 else "short",
                }
            }
            registro.registrar_paso(info_dict)
            
        return registro
        
    def test_get_estadisticas_sesion(self, registro_con_datos):
        """Test de obtención de estadísticas."""
        stats = registro_con_datos.get_estadisticas_sesion()
        
        # Verificar estructura (el método retorna pasos_totales, no total_pasos)
        assert "pasos_totales" in stats
        assert "equity_final" in stats
        assert "equity_inicial" in stats
        assert "operaciones_realizadas" in stats
        
        # Verificar valores
        assert stats["pasos_totales"] == 10
        
    def test_get_estadisticas_sesion_vacia(self, temp_train_dir):
        """Test de estadísticas con sesión vacía."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        stats = registro.get_estadisticas_sesion()
        
        # Debe retornar estadísticas con valores por defecto o cero
        assert isinstance(stats, dict)
        assert stats.get("pasos_totales", 0) == 0  # Cambiar de total_pasos a pasos_totales


class TestRegistroProduccionEdgeCases:
    """Tests de casos extremos."""
    
    @pytest.fixture
    def temp_train_dir(self, tmp_path):
        """Fixture de directorio temporal de entrenamiento."""
        train_id = "test_train_id"
        train_dir = tmp_path / "entrenamientos" / train_id
        train_dir.mkdir(parents=True, exist_ok=True)
        
        # Cambiar al directorio temporal
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        yield train_id, str(tmp_path)
        
        # Restaurar directorio original
        os.chdir(original_cwd)
    
    def test_valores_none_en_info_dict(self, temp_train_dir):
        """Test con valores None en info_dict."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        info_dict = {
            "entorno": {
                "timestamp": "2023-01-01T12:00:00",
                "paso": 1,
                "action": None,
                "precio": None,
            },
            "portafolio": {
                "balance": None,
                "equity": None,
            },
            "operacion": {
                "tipo_accion": None,
            }
        }
        
        # No debe lanzar excepción
        registro.registrar_paso(info_dict)
        
    def test_campos_faltantes_en_info_dict(self, temp_train_dir):
        """Test con campos faltantes en info_dict."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        info_dict = {
            "entorno": {
                "timestamp": "2023-01-01T12:00:00",
                # Faltan muchos campos
            },
            "portafolio": {},
            "operacion": {}
        }
        
        # No debe lanzar excepción
        registro.registrar_paso(info_dict)
        
    def test_emergencia_sin_detalles(self, temp_train_dir):
        """Test de emergencia sin detalles opcionales."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        # Sin especificar detalles
        registro.registrar_emergencia(
            razon="Error",
            balance_final=8000.0,
            equity_final=8000.0,
            posiciones_cerradas=0
        )
        
        # Verificar que se registró
        with open(registro.emergencia_path, 'r') as f:
            lines = f.readlines()
            
        assert len(lines) == 2
        
    def test_session_start_timestamp_format(self, temp_train_dir):
        """Test del formato del timestamp de sesión."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        # Verificar formato YYYYMMDD_HHMMSS
        assert len(registro.session_start) == 15
        assert registro.session_start[8] == "_"
        
        # Debe ser parseable como timestamp
        datetime.strptime(registro.session_start, "%Y%m%d_%H%M%S")

    def test_get_session_timestamp(self, temp_train_dir):
        """Test del método get_session_timestamp."""
        train_id, _ = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        timestamp = registro.get_session_timestamp()
        
        # Debe retornar el mismo timestamp que session_start
        assert timestamp == registro.session_start
        
        # Debe ser un string válido
        assert isinstance(timestamp, str)
        assert len(timestamp) == 15
        
        # Formato correcto
        datetime.strptime(timestamp, "%Y%m%d_%H%M%S")

    def test_get_base_dir(self, temp_train_dir):
        """Test del método get_base_dir."""
        train_id, base_path = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        base_dir = registro.get_base_dir()
        
        # Debe retornar el mismo directorio base
        assert base_dir == registro.base_dir
        
        # Debe ser un Path
        assert isinstance(base_dir, Path)
        
        # Debe existir
        assert base_dir.exists()
        assert base_dir.is_dir()
        
        # Debe terminar en /produccion
        assert base_dir.name == "produccion"

    def test_get_base_dir_string_path(self, temp_train_dir):
        """Test que get_base_dir retorna un Path válido."""
        train_id, base_path = temp_train_dir
        registro = RegistroProduccion(train_id)
        
        base_dir = registro.get_base_dir()
        
        # Debe poder convertirse a string
        base_dir_str = str(base_dir)
        assert isinstance(base_dir_str, str)
        assert "produccion" in base_dir_str
