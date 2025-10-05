"""Tests para el módulo logger.py."""

import pytest
import logging
import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

from src.utils.logger import (
    setup_logger,
    configure_file_logging,
    configure_sb3_logger,
    StreamToLogger,
    redirect_stdout_to_file,
    configure_production_logging,
    configure_external_loggers
)


class TestSetupLogger:
    """Tests para la función setup_logger."""

    def test_setup_logger_consola_por_defecto(self, clean_logger):
        """Verifica que por defecto se configura el logger para consola."""
        setup_logger()
        logger = logging.getLogger("AFML")
        
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.level == logging.INFO

    def test_setup_logger_nivel_personalizado(self, clean_logger):
        """Verifica que se puede configurar el nivel de logging."""
        setup_logger(log_level=logging.DEBUG)
        logger = logging.getLogger("AFML")
        
        assert logger.level == logging.DEBUG

    def test_setup_logger_con_archivo(self, clean_logger, temp_log_file):
        """Verifica que se puede configurar el logger para escribir en archivo."""
        setup_logger(log_level=logging.INFO, log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        assert logger.handlers[0].baseFilename == temp_log_file

    def test_setup_logger_crea_directorio_si_no_existe(self, clean_logger, temp_log_dir):
        """Verifica que se crea el directorio del archivo de log si no existe."""
        nested_dir = os.path.join(temp_log_dir, "nested", "path")
        log_file = os.path.join(nested_dir, "test.log")
        
        setup_logger(log_file=log_file)
        
        assert os.path.exists(nested_dir)
        assert os.path.exists(log_file)

    def test_setup_logger_limpia_handlers_existentes(self, clean_logger):
        """Verifica que se limpian los handlers existentes."""
        logger = logging.getLogger("AFML")
        
        # Agregar un handler manual
        logger.addHandler(logging.StreamHandler())
        assert len(logger.handlers) == 1
        
        # Configurar nuevamente
        setup_logger()
        
        # Debe haber solo 1 handler (el nuevo)
        assert len(logger.handlers) == 1

    def test_setup_logger_escribe_en_archivo(self, clean_logger, temp_log_file):
        """Verifica que los logs se escriben correctamente en el archivo."""
        setup_logger(log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        
        test_message = "Test log message"
        logger.info(test_message)
        
        # Forzar flush del handler
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert test_message in content
            assert "INFO" in content

    def test_setup_logger_formato_correcto(self, clean_logger, temp_log_file):
        """Verifica que el formato de los logs es correcto."""
        setup_logger(log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        
        logger.info("Test message")
        
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            # Formato: YYYY-MM-DD HH:MM:SS - AFML - INFO - Test message
            assert " - AFML - INFO - Test message" in line


class TestConfigureFileLogging:
    """Tests para la función configure_file_logging."""

    def test_configure_file_logging_retorna_path_correcto(self, clean_logger, training_base_dir):
        """Verifica que retorna el path correcto del archivo de log."""
        log_path = configure_file_logging(training_base_dir)
        
        expected_path = os.path.join(training_base_dir, "training.log")
        assert log_path == expected_path

    def test_configure_file_logging_nombre_personalizado(self, clean_logger, training_base_dir):
        """Verifica que se puede usar un nombre personalizado para el archivo."""
        custom_name = "custom.log"
        log_path = configure_file_logging(training_base_dir, log_filename=custom_name)
        
        expected_path = os.path.join(training_base_dir, custom_name)
        assert log_path == expected_path

    def test_configure_file_logging_configura_logger_principal(self, clean_logger, training_base_dir):
        """Verifica que configura el logger principal correctamente."""
        log_path = configure_file_logging(training_base_dir)
        logger = logging.getLogger("AFML")
        
        assert len(logger.handlers) >= 1
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_configure_file_logging_configura_sb3_logger(self, clean_logger, clean_sb3_logger, training_base_dir):
        """Verifica que también configura el logger de stable-baselines3."""
        configure_file_logging(training_base_dir)
        sb3_logger = logging.getLogger("stable_baselines3")
        
        assert len(sb3_logger.handlers) >= 1
        assert any(isinstance(h, logging.FileHandler) for h in sb3_logger.handlers)

    def test_configure_file_logging_escribe_en_archivo(self, clean_logger, training_base_dir):
        """Verifica que los logs se escriben en el archivo configurado."""
        log_path = configure_file_logging(training_base_dir)
        logger = logging.getLogger("AFML")
        
        test_message = "Training started"
        logger.info(test_message)
        
        for handler in logger.handlers:
            handler.flush()
        
        assert os.path.exists(log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert test_message in content


class TestConfigureSb3Logger:
    """Tests para la función configure_sb3_logger."""

    def test_configure_sb3_logger_crea_handler(self, clean_sb3_logger, temp_log_file):
        """Verifica que se crea un handler para el archivo."""
        configure_sb3_logger(temp_log_file)
        logger = logging.getLogger("stable_baselines3")
        
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

    def test_configure_sb3_logger_nivel_info(self, clean_sb3_logger, temp_log_file):
        """Verifica que el nivel de logging es INFO."""
        configure_sb3_logger(temp_log_file)
        logger = logging.getLogger("stable_baselines3")
        
        assert logger.level == logging.INFO

    def test_configure_sb3_logger_no_propaga(self, clean_sb3_logger, temp_log_file):
        """Verifica que el logger no propaga al root logger."""
        configure_sb3_logger(temp_log_file)
        logger = logging.getLogger("stable_baselines3")
        
        assert logger.propagate is False

    def test_configure_sb3_logger_escribe_en_archivo(self, clean_sb3_logger, temp_log_file):
        """Verifica que los logs de SB3 se escriben en el archivo."""
        configure_sb3_logger(temp_log_file)
        logger = logging.getLogger("stable_baselines3")
        
        test_message = "SB3 training update"
        logger.info(test_message)
        
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert test_message in content

    def test_configure_sb3_logger_limpia_handlers_existentes(self, clean_sb3_logger, temp_log_file):
        """Verifica que limpia handlers existentes antes de configurar."""
        logger = logging.getLogger("stable_baselines3")
        logger.addHandler(logging.StreamHandler())
        assert len(logger.handlers) == 1
        
        configure_sb3_logger(temp_log_file)
        
        # Debe tener solo el nuevo handler
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)


class TestStreamToLogger:
    """Tests para la clase StreamToLogger."""

    def test_stream_to_logger_escribe_al_logger(self, clean_logger, temp_log_file):
        """Verifica que StreamToLogger escribe correctamente al logger."""
        setup_logger(log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        
        stream = StreamToLogger(logger, logging.INFO)
        stream.write("Test message from stream\n")
        
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test message from stream" in content

    def test_stream_to_logger_multiples_lineas(self, clean_logger, temp_log_file):
        """Verifica que maneja múltiples líneas correctamente."""
        setup_logger(log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        
        stream = StreamToLogger(logger, logging.INFO)
        stream.write("Line 1\nLine 2\nLine 3\n")
        
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Line 1" in content
            assert "Line 2" in content
            assert "Line 3" in content

    def test_stream_to_logger_flush_no_error(self):
        """Verifica que el método flush no causa errores."""
        logger = logging.getLogger("AFML")
        stream = StreamToLogger(logger)
        
        # No debe lanzar excepción
        stream.flush()

    def test_stream_to_logger_nivel_personalizado(self, clean_logger, temp_log_file):
        """Verifica que se puede usar un nivel de log personalizado."""
        setup_logger(log_file=temp_log_file, log_level=logging.DEBUG)
        logger = logging.getLogger("AFML")
        
        stream = StreamToLogger(logger, logging.WARNING)
        stream.write("Warning message\n")
        
        for handler in logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "WARNING" in content
            assert "Warning message" in content


class TestRedirectStdoutToFile:
    """Tests para la función redirect_stdout_to_file."""

    def test_redirect_stdout_to_file_captura_print(self, temp_log_file):
        """Verifica que captura los prints en el archivo."""
        redirect_stdout_to_file(temp_log_file)
        
        print("Test print statement")
        sys.stdout.flush()
        
        # Esperar un poco para que se escriba
        import time
        time.sleep(0.1)
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test print statement" in content

    def test_redirect_stdout_to_file_captura_stderr(self, temp_log_file):
        """Verifica que captura stderr en el archivo."""
        redirect_stdout_to_file(temp_log_file)
        
        print("Error message", file=sys.stderr)
        sys.stderr.flush()
        
        import time
        time.sleep(0.1)
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Error message" in content

    def test_redirect_stdout_to_file_crea_logger(self, temp_log_file):
        """Verifica que crea el logger AFML.stdout."""
        redirect_stdout_to_file(temp_log_file)
        
        logger = logging.getLogger("AFML.stdout")
        assert logger is not None
        assert len(logger.handlers) > 0

    def test_redirect_stdout_to_file_no_propaga(self, temp_log_file):
        """Verifica que el logger stdout no propaga."""
        redirect_stdout_to_file(temp_log_file)
        
        logger = logging.getLogger("AFML.stdout")
        assert logger.propagate is False


class TestIntegration:
    """Tests de integración del sistema de logging."""

    def test_flujo_completo_entrenamiento(self, clean_logger, clean_sb3_logger, training_base_dir):
        """Simula el flujo completo de configuración de logging para entrenamiento."""
        # 1. Configurar logging para archivo
        log_path = configure_file_logging(training_base_dir)
        
        # 2. Hacer algunos logs
        logger = logging.getLogger("AFML")
        logger.info("Iniciando entrenamiento")
        logger.info("Configuración cargada")
        
        sb3_logger = logging.getLogger("stable_baselines3")
        sb3_logger.info("Modelo creado")
        
        # Flush
        for handler in logger.handlers:
            handler.flush()
        for handler in sb3_logger.handlers:
            handler.flush()
        
        # 3. Verificar que todo se escribió en el mismo archivo
        assert os.path.exists(log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Iniciando entrenamiento" in content
            assert "Configuración cargada" in content
            assert "Modelo creado" in content

    def test_cambio_de_consola_a_archivo(self, clean_logger, temp_log_file):
        """Verifica que se puede cambiar de logging en consola a archivo."""
        # Iniciar con consola
        setup_logger()
        logger = logging.getLogger("AFML")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        
        # Cambiar a archivo
        setup_logger(log_file=temp_log_file)
        logger = logging.getLogger("AFML")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)


class TestConfigureProductionLogging:
    """Tests para la función configure_production_logging."""

    def test_configure_production_logging_crea_archivo(self, clean_logger, temp_log_dir):
        """Verifica que se crea el archivo de log de producción."""
        session_timestamp = "20250105_143022"
        
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        expected_path = os.path.join(temp_log_dir, f"produccion_{session_timestamp}.log")
        assert log_path == expected_path
        assert os.path.exists(log_path)

    def test_configure_production_logging_configura_logger_principal(self, clean_logger, temp_log_dir):
        """Verifica que configura el logger principal AFML."""
        session_timestamp = "20250105_143022"
        
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        logger = logging.getLogger("AFML")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        assert logger.handlers[0].baseFilename == log_path

    def test_configure_production_logging_escribe_logs(self, clean_logger, temp_log_dir):
        """Verifica que los logs se escriben correctamente."""
        session_timestamp = "20250105_143022"
        
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        logger = logging.getLogger("AFML.test")
        logger.info("Test production log")
        
        # Flush
        for handler in logger.handlers:
            handler.flush()
        
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test production log" in content

    def test_configure_production_logging_configura_external_loggers(self, clean_logger, temp_log_dir):
        """Verifica que configura loggers externos."""
        session_timestamp = "20250105_143022"
        
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        # Verificar que los loggers externos están configurados
        binance_logger = logging.getLogger("binance")
        assert len(binance_logger.handlers) == 1
        assert binance_logger.level == logging.WARNING
        assert binance_logger.propagate is False

    def test_configure_production_logging_redirige_stdout(self, clean_logger, temp_log_dir):
        """Verifica que redirige stdout al archivo."""
        session_timestamp = "20250105_143022"
        
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        # Verificar que stdout fue redirigido
        from src.utils.logger import StreamToLogger
        assert isinstance(sys.stdout, StreamToLogger)


class TestConfigureExternalLoggers:
    """Tests para la función configure_external_loggers."""

    def test_configure_external_loggers_crea_handlers(self, clean_logger, temp_log_file):
        """Verifica que crea handlers para loggers externos."""
        configure_external_loggers(temp_log_file)
        
        # Verificar algunos loggers externos
        loggers_to_check = ['binance', 'websockets', 'asyncio']
        
        for logger_name in loggers_to_check:
            logger = logging.getLogger(logger_name)
            assert len(logger.handlers) >= 1
            assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_configure_external_loggers_nivel_warning(self, clean_logger, temp_log_file):
        """Verifica que el nivel es WARNING para loggers externos."""
        configure_external_loggers(temp_log_file)
        
        binance_logger = logging.getLogger("binance")
        assert binance_logger.level == logging.WARNING

    def test_configure_external_loggers_no_propagacion(self, clean_logger, temp_log_file):
        """Verifica que los loggers externos no propagan."""
        configure_external_loggers(temp_log_file)
        
        for logger_name in ['binance', 'websockets', 'asyncio']:
            logger = logging.getLogger(logger_name)
            assert logger.propagate is False

    def test_configure_external_loggers_escribe_warnings(self, clean_logger, temp_log_file):
        """Verifica que escribe warnings de loggers externos."""
        configure_external_loggers(temp_log_file)
        
        binance_logger = logging.getLogger("binance")
        binance_logger.warning("Test warning from binance")
        
        # Flush
        for handler in binance_logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test warning from binance" in content
            assert "WARNING" in content

    def test_configure_external_loggers_no_escribe_info(self, clean_logger, temp_log_file):
        """Verifica que NO escribe INFO de loggers externos (solo WARNING+)."""
        configure_external_loggers(temp_log_file)
        
        binance_logger = logging.getLogger("binance")
        binance_logger.info("Info message should not appear")
        binance_logger.warning("Warning message should appear")
        
        # Flush
        for handler in binance_logger.handlers:
            handler.flush()
        
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Info message should not appear" not in content
            assert "Warning message should appear" in content


class TestProductionIntegration:
    """Tests de integración para el flujo de producción."""

    def test_flujo_completo_produccion(self, clean_logger, temp_log_dir):
        """Simula el flujo completo de configuración de logging para producción."""
        session_timestamp = "20250105_143022"
        
        # 1. Configurar logging de producción
        log_path = configure_production_logging(temp_log_dir, session_timestamp)
        
        # 2. Hacer logs desde diferentes fuentes
        afml_logger = logging.getLogger("AFML.live")
        afml_logger.info("Sistema iniciado")
        
        binance_logger = logging.getLogger("binance")
        binance_logger.warning("API warning")
        
        # 3. Simular un print (stdout)
        print("Console output")
        
        # Flush todos
        for handler in afml_logger.handlers:
            handler.flush()
        for handler in binance_logger.handlers:
            handler.flush()
        sys.stdout.flush()
        
        import time
        time.sleep(0.1)
        
        # 4. Verificar que todo está en el archivo
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Sistema iniciado" in content
            assert "API warning" in content
            assert "Console output" in content
