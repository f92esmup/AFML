""" Función para configurar el logger """
import logging
import os
import sys
from typing import Optional


def setup_logger(log_level=logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Configura el logger de la aplicación.
    
    Args:
        log_level: Nivel de logging (por defecto INFO)
        log_file: Ruta completa del archivo donde guardar los logs.
                  Si es None, los logs se muestran en consola.
                  Si se proporciona, los logs se guardan SOLO en el archivo.
    """
    # El nombre 'AFML' es un nombre raíz para tu aplicación.
    logger = logging.getLogger("AFML")
    logger.setLevel(log_level)

    # Limpiar handlers existentes para evitar duplicados
    logger.handlers.clear()

    # Crea un formato para los mensajes de log.
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if log_file:
        # Modo archivo: guardar logs SOLO en archivo
        # Crear directorio si no existe
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Crear handler de archivo
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # Modo consola: mostrar logs en terminal (fallback inicial)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def configure_file_logging(base_dir: str, log_filename: str = "training.log") -> str:
    """
    Reconfigura el logger para guardar en archivo dentro del directorio de entrenamiento.
    También configura stable-baselines3 para usar el mismo sistema de logging.
    
    Args:
        base_dir: Directorio base del entrenamiento (ej: entrenamientos/train_BTCUSDT_...)
        log_filename: Nombre del archivo de log (por defecto 'training.log')
        
    Returns:
        Ruta completa del archivo de log
    """
    log_path = os.path.join(base_dir, log_filename)
    
    # Reconfigurar logger principal con archivo
    setup_logger(log_level=logging.INFO, log_file=log_path)
    
    # Configurar también el logger de stable-baselines3
    configure_sb3_logger(log_path)
    
    return log_path


def configure_sb3_logger(log_file: str) -> None:
    """
    Configura el logger de Stable-Baselines3 para escribir en el mismo archivo.
    
    Args:
        log_file: Ruta del archivo de log
    """
    # Configurar el logger de SB3
    sb3_logger = logging.getLogger("stable_baselines3")
    sb3_logger.setLevel(logging.INFO)
    sb3_logger.handlers.clear()
    
    # Usar el mismo formato que AFML
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    sb3_logger.addHandler(file_handler)
    
    # Evitar propagación al root logger
    sb3_logger.propagate = False


class StreamToLogger:
    """
    Clase para redirigir stdout/stderr a un logger.
    Útil para capturar prints y salidas de librerías que no usan logging.
    """
    def __init__(self, logger: logging.Logger, log_level: int = logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf: str) -> None:
        """Escribe en el logger."""
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self) -> None:
        """Flush (requerido para compatibilidad con file-like objects)."""
        pass


def redirect_stdout_to_file(log_file: str) -> None:
    """
    Redirige stdout y stderr al archivo de log.
    Esto captura TODAS las salidas incluyendo prints y mensajes de SB3.
    
    Args:
        log_file: Ruta del archivo de log
    """
    # Crear un logger específico para stdout/stderr
    stdout_logger = logging.getLogger("AFML.stdout")
    stdout_logger.setLevel(logging.INFO)
    stdout_logger.handlers.clear()
    
    # Formato simple para salidas estándar
    formatter = logging.Formatter('%(message)s')
    
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    stdout_logger.addHandler(file_handler)
    stdout_logger.propagate = False
    
    # Redirigir stdout y stderr
    sys.stdout = StreamToLogger(stdout_logger, logging.INFO)
    sys.stderr = StreamToLogger(stdout_logger, logging.ERROR)
