""" Función para parsear los argumentos de la línea de comandos. """
import argparse

def parse_args() -> argparse.Namespace:
    """ Parsea los argumentos de la línea de comandos para el entrenamiento del agente. """
    parser = argparse.ArgumentParser(
        description="Entrena un agente de aprendizaje por refuerzo usando SAC",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Argumentos obligatorios
    parser.add_argument(
        "--data-id",
        type=str,
        required=True,
        help="ID del dataset a usar para el entrenamiento (ej: BTCUSDT_20250904_133047)"
    )
    
    parser.add_argument(
        "--episodios",
        type=int,
        default=2,
        required=False,
        help="Número total de episodios para entrenar el agente"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="src/Entrenamiento/config/config.yaml",
        required=False,
        help="Ruta al archivo de configuración YAML"
    )
    
    return parser.parse_args()
    