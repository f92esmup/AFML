""" Script para entrenar y evaluar el sistema de Trading. Equivale a un paso de walk-forward."""
import sys
import logging
from typing import TYPE_CHECKING
from argparse import Namespace
import pandas as pd
import yaml
import os

from src.AdqusicionDatos.utils.logger import setup_logger
from src.Entrenamiento.config.cli import parse_args
from src.Entrenamiento.entorno import TradingEnv, Portafolio
from src.Entrenamiento.agente import AgenteSac
from src.Entrenamiento.utils.utils import calcular_steps

if TYPE_CHECKING:
    from src.Entrenamiento.config import Config

# Configurar el logger
setup_logger()
log: logging.Logger = logging.getLogger("AFML.train")

class Entrenamiento:
    def __init__(self, args: Namespace) -> None:
        """Inicializa el entrenamiento con la configuración proporcionada."""
        log.info("Inicializando entrenamiento...")
        
        self.config: 'Config'
        self.data: pd.DataFrame
        self.portafolio: Portafolio
        self.entorno: TradingEnv
        self.agente: AgenteSac
        
        try:
            # Cargar configuración
            log.debug("Cargando configuración...")
            from src.Entrenamiento.config import Config
            self.config = Config.load_config(args)
            log.debug("Configuración cargada exitosamente.")
            
            # Cargar datos del dataset
            log.info(f"Cargando datos del dataset: {args.data_id}")
            self.data = self._cargar_datos(args.data_id)
            log.info(f"Datos cargados: {len(self.data)} registros.")
            
            # Guardar args para uso posterior (evaluación)
            self.data_eval_id = args.data_eval_id
            self.episodios_eval = args.episodios_eval

            # Crear componentes del entrenamiento
            log.debug("Creando portafolio...")
            self.portafolio = Portafolio(self.config)
            log.debug("Portafolio creado exitosamente.")
            
            log.debug("Creando entorno de trading...")
            self.entorno = TradingEnv(self.config, self.data, self.portafolio)
            log.debug("Entorno de trading creado exitosamente.")
            
            # Calcular timesteps totales
            log.debug("Calculando timesteps totales...")
            max_steps_per_episode: int = len(self.data) - self.config.entorno.window_size
            total_timesteps: int = calcular_steps(self.config.entorno.episodios, max_steps_per_episode)
            log.info(f"Timesteps totales calculados: {total_timesteps}")
            
            log.debug("Creando agente SAC...")
            self.agente = AgenteSac(self.config, total_timesteps)
            log.info("Entrenamiento inicializado correctamente.")
            
        except Exception as e:
            log.error(f"Error durante la inicialización del entrenamiento: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _cargar_datos(self, data_id: str) -> pd.DataFrame:
        """Carga los datos procesados desde el dataset."""
        try:
            log.debug(f"Intentando cargar datos desde dataset: {data_id}")
            # Cargar datos
            data_path: str = f"datasets/{data_id}/data.csv"
            log.debug(f"Ruta del archivo: {data_path}")
            
            data: pd.DataFrame = pd.read_csv(data_path, index_col=0, parse_dates=True)
            
            # Validar datos cargados
            if data.empty:
                raise ValueError(f"El dataset {data_id} está vacío")
            
            log.info(f"Datos cargados exitosamente desde: {data_path}")
            log.debug(f"Shape de los datos: {data.shape}")
            log.debug(f"Columnas disponibles: {list(data.columns)}")
            
            return data
            
        except FileNotFoundError as e:
            log.error(f"No se encontró el archivo del dataset {data_id}: {e}")
            log.error(f"Verifique que existe el archivo: datasets/{data_id}/data.csv")
            raise
        except pd.errors.EmptyDataError as e:
            log.error(f"El archivo del dataset {data_id} está vacío: {e}")
            raise
        except pd.errors.ParserError as e:
            log.error(f"Error al parsear el archivo CSV del dataset {data_id}: {e}")
            raise
        except Exception as e:
            log.error(f"Error inesperado al cargar datos del dataset {data_id}: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def entrenar(self) -> None:
        """Ejecuta el proceso de entrenamiento."""
        log.info("Iniciando entrenamiento del agente...")
        
        try:
            # Crear el modelo del agente
            log.info("Creando modelo SAC...")
            self.agente.CrearModelo(self.entorno)
            log.info("Modelo SAC creado exitosamente.")
            
            # Entrenar el agente
            log.info("Comenzando entrenamiento...")
            log.info(f"Episodios configurados: {self.config.entorno.episodios}")
            self.agente.train()
            log.info("Entrenamiento del agente completado.")
            
            # Guardar el modelo entrenado
            log.info("Guardando modelo entrenado...")
            self.agente.GuardarModelo()
            log.info("Modelo guardado exitosamente.")
            
            # --- Evaluación automática si se proporcionó data_eval_id en CLI ---

            if self.data_eval_id:
                try:
                    log.info(f"Iniciando evaluación con dataset: {self.data_eval_id}")
                    eval_data = self._cargar_datos(self.data_eval_id)
                    eval_portafolio = Portafolio(self.config)
                    eval_env = TradingEnv(self.config, eval_data, eval_portafolio)

                    max_steps_eval = len(eval_data) - self.config.entorno.window_size
                    # Ejecutar evaluación (esto guardará los 3 CSVs en Output.base_dir/evaluacion)
                    results = self.agente.EvaluarEnv(eval_env, n_episodes=self.episodios_eval, max_steps_per_episode=max_steps_eval, save_dir=self.config.Output.base_dir)
                    log.info(f"Evaluación completada. CSVs guardados en: {self.config.Output.base_dir}/evaluacion")
                except Exception as e:
                    log.error(f"Error durante la evaluación: {e}")
                    log.error("Detalles:", exc_info=True)
            else:
                log.info("No se proporcionó dataset de evaluación. Se omite la evaluación.")
            
            log.info("¡Entrenamiento completado exitosamente!")
            
        except Exception as e:
            log.error(f"Error durante el entrenamiento: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _guardar_metadata(self) -> None:
        """Guarda la configuración completa en un archivo YAML como metadata."""
        try:
            log.info("Guardando metadata de configuración...")
            
            # Convertir config a diccionario usando Pydantic
            config_dict = self.config.model_dump()
            
            # Crear ruta del archivo metadata
            metadata_path = os.path.join(self.config.Output.base_dir, "config_metadata.yaml")
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            # Guardar en YAML
            with open(metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            log.info(f"Metadata guardada en: {metadata_path}")
            
        except Exception as e:
            log.error(f"Error al guardar metadata: {e}")
            raise

    def main(self) -> None:
        """Función con el flujo principal del entrenamiento."""
        try:
            log.info("Ejecutando flujo principal de entrenamiento...")
            self.entrenar()
            
            # Guardar metadata al final del entrenamiento
            log.info("---- Guardado de metadata ----")
            self._guardar_metadata()
            
            log.info("--- Entrenamiento finalizado con éxito ---")
            
        except KeyboardInterrupt:
            log.warning("Entrenamiento interrumpido por el usuario (Ctrl+C)")
            log.info("Limpiando recursos...")
            sys.exit(130)  # Exit code for Ctrl+C
        except MemoryError as e:
            log.error("Error de memoria durante el entrenamiento")
            log.error(f"Detalles: {e}")
            log.error("Considere reducir el tamaño del batch o el window_size")
            sys.exit(1)
        except Exception as e:
            log.error("!!! El entrenamiento ha fallado !!!")
            log.error(f"Error: {e}", exc_info=True)
            sys.exit(1)

def main() -> None:
    """Punto de entrada principal del script."""
    log.info("--- Iniciando script de entrenamiento ---")
    
    try:
        # Parsear argumentos de línea de comandos
        log.debug("Parseando argumentos de línea de comandos...")
        args: Namespace = parse_args()
        log.debug(f"Argumentos recibidos: {args}")
        
        # Validar argumentos básicos
        if not hasattr(args, 'data_id') or not args.data_id:
            raise ValueError("El argumento 'data_id' es requerido")
        
        log.info(f"Iniciando entrenamiento con dataset: {args.data_id}")
        
        # Crear y ejecutar entrenamiento
        log.debug("Creando instancia de entrenamiento...")
        entrenamiento: Entrenamiento = Entrenamiento(args)
        entrenamiento.main()
        
        log.info("--- Script de entrenamiento finalizado exitosamente ---")
        
    except KeyboardInterrupt:
        log.warning("Script interrumpido por el usuario (Ctrl+C)")
        sys.exit(130)
    except ValueError as e:
        log.error(f"Error en los argumentos proporcionados: {e}")
        sys.exit(2)
    except Exception as e:
        log.error("!!! Fallo crítico en la inicialización !!!")
        log.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

