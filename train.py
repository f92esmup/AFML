""" Script para entrenar el sistema de Trading."""
import sys
import logging
import pandas as pd

from src.AdqusicionDatos.utils.logger import setup_logger
from src.Entrenamiento.config import Config
from src.Entrenamiento.config.cli import parse_args
from src.Entrenamiento.entorno import TradingEnv, Portafolio
from src.Entrenamiento.agente import AgenteSac
from src.Entrenamiento.utils.utils import calcular_steps

# Configurar el logger
setup_logger()
log = logging.getLogger("AFML.train")

class Entrenamiento:
    def __init__(self, args):
        """Inicializa el entrenamiento con la configuración proporcionada."""
        log.info("Inicializando entrenamiento...")
        
        # Cargar configuración
        self.config = Config.load_config(args)
        log.debug("Configuración cargada exitosamente.")
        
        # Cargar datos del dataset
        self.data = self._cargar_datos(args.data_id)
        log.info(f"Datos cargados: {len(self.data)} registros.")
        
        # Crear componentes del entrenamiento
        self.portafolio = Portafolio(self.config)
        self.entorno = TradingEnv(self.config, self.data, self.portafolio)
        
        # Calcular timesteps totales
        max_steps_per_episode = len(self.data) - self.config.entorno.window_size
        total_timesteps = calcular_steps(self.config.entorno.episodios, max_steps_per_episode)
        
        self.agente = AgenteSac(self.config, total_timesteps)
        log.info("Entrenamiento inicializado correctamente.")

    def _cargar_datos(self, data_id: str) -> pd.DataFrame:
        """Carga los datos procesados desde el dataset."""
        try:
            # Cargar datos
            data_path = f"datasets/{data_id}/data.csv"
            data = pd.read_csv(data_path, index_col=0, parse_dates=True)
            
            
            log.info(f"Datos cargados desde: datasets/{data_id}/")
            return data
            
        except FileNotFoundError as e:
            log.error(f"No se encontró el dataset {data_id}: {e}")
            raise
        except Exception as e:
            log.error(f"Error al cargar datos: {e}")
            raise

    def entrenar(self):
        """Ejecuta el proceso de entrenamiento."""
        log.info("Iniciando entrenamiento del agente...")
        
        try:
            # Crear el modelo del agente
            log.info("Creando modelo SAC...")
            self.agente.CrearModelo(self.entorno)
            
            # Entrenar el agente
            log.info("Comenzando entrenamiento...")
            self.agente.train()
            
            # Guardar el modelo entrenado
            log.info("Guardando modelo entrenado...")
            self.agente.GuardarModelo()
            
            log.info("¡Entrenamiento completado exitosamente!")
            
        except Exception as e:
            log.error(f"Error durante el entrenamiento: {e}")
            raise


    def main(self):
        """Función con el flujo principal del entrenamiento."""
        try:
            self.entrenar()
            log.info("--- Entrenamiento finalizado con éxito ---")
            
        except Exception as e:
            log.error("!!! El entrenamiento ha fallado !!!")
            log.error(f"Error: {e}", exc_info=True)
            sys.exit(1)

def main():
    """Punto de entrada principal del script."""
    log.info("--- Iniciando script de entrenamiento ---")
    
    try:
        # Parsear argumentos de línea de comandos
        args = parse_args()
        log.debug(f"Argumentos recibidos: {args}")
        
        # Crear y ejecutar entrenamiento
        entrenamiento = Entrenamiento(args)
        entrenamiento.main()
        
    except Exception as e:
        log.error("!!! Fallo crítico en la inicialización !!!")
        log.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

