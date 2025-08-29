""" Función para configurar el logger """
import logging
import sys

def setup_logger(log_level=logging.INFO) -> None:
    """
    Configura y devuelve un logger.
    Los logs se mostrarán en la consola.
    """
    # El nombre 'AFML' es un nombre raíz para tu aplicación.
    logger = logging.getLogger("AFML")
    logger.setLevel(log_level)

    # Evita añadir múltiples handlers si la función se llama más de una vez.
    if not logger.handlers:
        # Crea un handler para la salida estándar (consola).
        handler = logging.StreamHandler(sys.stdout)
        
        # Crea un formato para los mensajes de log.
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Asigna el formato al handler.
        handler.setFormatter(formatter)
        
        # Añade el handler al logger.
        logger.addHandler(handler)
