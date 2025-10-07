"""Script para entrenar y evaluar el sistema de Trading con flujo unificado.
Implementa un paso completo de walk-forward: descarga de datos → entrenamiento → evaluación.
"""

import sys
import logging
import gc
from typing import TYPE_CHECKING, Optional, Tuple
from argparse import Namespace
import pandas as pd
import yaml
import os
import joblib
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from binance.client import Client

from src.utils.logger import (
    setup_logger,
    configure_file_logging,
    redirect_stdout_to_file,
)
from src.train.AdquisicionDatos.adquisicion import DataDownloader
from src.train.AdquisicionDatos.preprocesamiento import Preprocesamiento
from src.train.config import parse_args_training
from src.train.Entrenamiento.entorno import TradingEnv, Portafolio
from src.train.Entrenamiento.agente import AgenteSac

if TYPE_CHECKING:
    from src.train.config import UnifiedConfig

# Configurar el logger inicial (a consola, temporalmente)
# Se reconfigurará a archivo una vez que se conozca el train_id
setup_logger()
log: logging.Logger = logging.getLogger("AFML.train")


class Entrenamiento:
    def __init__(self, args: Namespace) -> None:
        """Inicializa el entrenamiento con flujo unificado (descarga + entrenamiento + evaluación)."""
        log.info("Inicializando flujo unificado de entrenamiento...")

        self.config: "UnifiedConfig"
        self.portafolio: Portafolio
        self.agente: Optional[AgenteSac]
        self.client: Client

        try:
            # Cargar configuración unificada
            log.debug("Cargando configuración unificada...")
            from src.train.config import UnifiedConfig

            self.config = UnifiedConfig.load_for_unified_training(args)
            log.debug("Configuración unificada cargada exitosamente.")

            # Guardar parámetros de fechas para entrenamiento y evaluación
            self.train_start = args.train_start_date
            self.train_end = args.train_end_date
            self.eval_start = args.eval_start_date
            self.eval_end = args.eval_end_date
            self.episodios_eval = args.episodios_eval

            # Inicializar cliente de Binance para descarga de datos
            log.info("Inicializando cliente de Binance...")
            self.client = Client()  # Cliente público (sin API keys)

            # Crear componentes del entrenamiento
            log.debug("Creando portafolio...")
            self.portafolio = Portafolio(self.config)
            log.debug("Portafolio creado exitosamente.")

            # El agente se creará después de descargar los datos de entrenamiento
            self.agente = None

            # Crear directorios de salida
            log.debug("Creando estructura de directorios...")
            self._crear_directorios()

            # Reconfigurar logger para guardar en archivo dentro del train_id
            if self.config.Output is None:
                raise ValueError("La configuración de salida (Output) no está definida")
            
            log_file_path = configure_file_logging(self.config.Output.base_dir)
            log.info(f"Logger reconfigurado. Logs guardados en: {log_file_path}")
            
            # Redirigir stdout/stderr al archivo de log (captura salidas de SB3)
            redirect_stdout_to_file(log_file_path)
            log.info("stdout/stderr redirigidos al archivo de log")
            log.info("=" * 80)

            log.info("Inicialización completada correctamente.")
            log.info(f"Periodo de entrenamiento: {self.train_start} a {self.train_end}")
            log.info(f"Periodo de evaluación: {self.eval_start} a {self.eval_end}")

        except Exception as e:
            log.error(f"Error durante la inicialización: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _descargar_y_preprocesar(
        self, start_date: str, end_date: str
    ) -> Tuple[pd.DataFrame, StandardScaler]:
        """Descarga y preprocesa datos para un rango de fechas específico.
        
        Args:
            start_date: Fecha de inicio en formato 'YYYY-MM-DD'
            end_date: Fecha de fin en formato 'YYYY-MM-DD'
            
        Returns:
            Tupla (datos_preprocesados, scaler_ajustado)
        """
        log.info(f"Descargando y preprocesando datos: {start_date} a {end_date}")

        try:
            # Actualizar temporalmente la configuración con las fechas específicas
            self.config.data_downloader.start_date = start_date
            self.config.data_downloader.end_date = end_date

            # 1. Descargar datos
            log.info("Paso 1: Descargando datos desde Binance...")
            downloader = DataDownloader(self.client, self.config)
            data_raw = downloader.run()
            log.info(f"Datos descargados: {len(data_raw)} registros.")

            # 2. Preprocesar datos
            log.info("Paso 2: Preprocesando datos (indicadores + normalización)...")
            preprocesador = Preprocesamiento(self.config)
            data_procesado, scaler = preprocesador.run(data_raw)
            log.info(f"Preprocesamiento completado. Datos finales: {len(data_procesado)} registros.")

            return data_procesado, scaler

        except Exception as e:
            log.error(f"Error en descarga/preprocesamiento de datos: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _guardar_scaler(self, scaler: StandardScaler, filepath: str) -> None:
        """Guarda el scaler en la ruta especificada."""
        try:
            log.info(f"Guardando scaler en: {filepath}")
            joblib.dump(scaler, filepath)
            log.debug(f"✅ Scaler guardado exitosamente.")

        except Exception as e:
            log.error(f"Error al guardar scaler: {e}")
            raise

    def _crear_directorios(self) -> None:
        """Crea la estructura de directorios necesaria para guardar los resultados."""
        try:
            if self.config.Output is None:
                raise ValueError("La configuración de salida (Output) no está definida")

            base_dir: str = self.config.Output.base_dir

            # Crear directorios
            directorios: list[str] = [
                base_dir,
                f"{base_dir}/modelos",
                f"{base_dir}/tensorboard",
                f"{base_dir}/evaluacion",
            ]

            for directorio in directorios:
                os.makedirs(directorio, exist_ok=True)
                log.debug(f"Directorio creado/verificado: {directorio}")

            log.info(f"Estructura de directorios creada en: {base_dir}")

        except Exception as e:
            log.error(f"Error al crear directorios: {e}")
            raise

    def entrenar(self) -> None:
        """Ejecuta el proceso de entrenamiento con descarga integrada de datos."""
        log.info("=" * 80)
        log.info("FASE 1: ENTRENAMIENTO")
        log.info("=" * 80)

        try:
            # 1. Descargar y preprocesar datos de entrenamiento
            log.info("Descargando datos de entrenamiento...")
            train_data, train_scaler = self._descargar_y_preprocesar(
                self.train_start, self.train_end
            )

            # 2. Guardar scaler de entrenamiento
            if self.config.Output is None:
                raise ValueError("La configuración de salida no está definida")
            
            scaler_train_path = self.config.Output.scaler_train_path
            self._guardar_scaler(train_scaler, scaler_train_path)

            # 3. Crear entorno de entrenamiento
            log.info("Creando entorno de trading para entrenamiento...")
            entorno_train = TradingEnv(
                self.config,
                train_data,
                self.portafolio,
                scaler=train_scaler  # Usar scaler de train
            )
            log.debug("Entorno de trading creado exitosamente.")

            # 4. Obtener timesteps totales de la configuración
            total_timesteps: int = self.config.entorno.total_timesteps
            log.info(f"Timesteps totales configurados: {total_timesteps}")

            # 5. Crear y entrenar agente SAC
            log.info("Creando agente SAC...")
            self.agente = AgenteSac(self.config, total_timesteps)
            self.agente.CrearModelo(entorno_train)

            log.info("Iniciando entrenamiento del agente...")
            self.agente.train()

            # 6. Guardar modelo entrenado
            log.info("Guardando modelo entrenado...")
            self.agente.GuardarModelo()

            log.info("✅ Entrenamiento completado exitosamente.")

            # 7. LIBERAR MEMORIA - CRÍTICO
            log.info("Liberando memoria de datos de entrenamiento...")
            del train_data
            del entorno_train
            del train_scaler
            gc.collect()
            log.debug("Memoria liberada exitosamente.")

        except Exception as e:
            log.error(f"Error durante el entrenamiento: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def evaluar(self) -> None:
        """Ejecuta la evaluación del agente entrenado con datos de evaluación."""
        log.info("=" * 80)
        log.info("FASE 2: EVALUACIÓN")
        log.info("=" * 80)

        try:
            # Verificar que el agente existe
            if self.agente is None:
                raise RuntimeError(
                    "El agente no ha sido inicializado. Debe ejecutar entrenar() primero."
                )

            # 1. Descargar y preprocesar datos de evaluación
            log.info("Descargando datos de evaluación...")
            eval_data, eval_scaler = self._descargar_y_preprocesar(
                self.eval_start, self.eval_end
            )

            # 2. Guardar scaler de evaluación (opcional, para trazabilidad)
            if self.config.Output is None:
                raise ValueError("La configuración de salida no está definida")
            
            if self.config.Output.scaler_eval_path:
                self._guardar_scaler(eval_scaler, self.config.Output.scaler_eval_path)

            # 3. Crear entorno de evaluación
            # IMPORTANTE: Usar train_scaler para consistencia con producción
            # (en producción se usaría el scaler del entrenamiento)
            log.info("Creando entorno de trading para evaluación...")
            
            # Cargar el scaler de entrenamiento
            train_scaler = joblib.load(self.config.Output.scaler_train_path)
            
            self.portafolio.reset()  # Resetear portafolio antes de evaluación
            
            eval_env = TradingEnv(
                self.config,
                eval_data,
                self.portafolio,
                scaler=train_scaler  # ✅ USAR SCALER DE TRAIN (consistencia con producción)
            )
            log.debug("Entorno de evaluación creado exitosamente.")

            # 4. Evaluar el agente
            log.info(f"Evaluando agente con {self.episodios_eval} episodios...")
            max_steps_per_episode_eval: int = (
                len(eval_data) - self.config.entorno.window_size
            )

            self.agente.EvaluarEnv(
                env=eval_env,
                n_episodes=self.episodios_eval,
                max_steps_per_episode=max_steps_per_episode_eval,
                save_dir=f"{self.config.Output.base_dir}/evaluacion",
            )

            log.info(
                f"✅ Evaluación completada. Resultados guardados en: {self.config.Output.base_dir}/evaluacion"
            )

            # 5. LIBERAR MEMORIA - CRÍTICO
            log.info("Liberando memoria de datos de evaluación...")
            del eval_data
            del eval_env
            del eval_scaler
            del train_scaler
            gc.collect()
            log.debug("Memoria liberada exitosamente.")

        except Exception as e:
            log.error(f"Error durante la evaluación: {e}")
            log.error("Detalles del error:", exc_info=True)
            raise

    def _guardar_metadata(self) -> None:
        """Guarda TODA la configuración de UnifiedConfig más metadata adicional en YAML."""
        try:
            if self.config.Output is None:
                raise ValueError("La configuración de salida no está definida")

            metadata_path = os.path.join(
                self.config.Output.base_dir,
                self.config.Output.metadata_filename,
            )

            log.info("Guardando metadata completa del entrenamiento...")

            # Serializar TODO el objeto UnifiedConfig usando model_dump()
            config_dict = self.config.model_dump()

            # Añadir metadata adicional sobre la ejecución
            config_dict["metadata_execution"] = {
                "fecha_ejecucion": datetime.now().isoformat(),
                "train_date_range": f"{self.train_start} to {self.train_end}",
                "eval_date_range": f"{self.eval_start} to {self.eval_end}",
                "total_timesteps": self.config.entorno.total_timesteps,
                "episodios_evaluacion": self.episodios_eval,
                "train_id": os.path.basename(self.config.Output.base_dir),
            }

            # Convertir train_freq de tupla a lista (compatible con yaml.safe_load)
            if "SACmodel" in config_dict and "train_freq" in config_dict["SACmodel"]:
                config_dict["SACmodel"]["train_freq"] = list(config_dict["SACmodel"]["train_freq"])

            # Guardar en archivo YAML
            with open(metadata_path, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

            log.info(f"✅ Metadata completa guardada en: {metadata_path}")

        except Exception as e:
            log.error(f"Error al guardar metadata: {e}")
            raise

    def main(self) -> None:
        """Flujo principal unificado: entrenar → evaluar → guardar metadata."""
        try:
            log.info("=" * 80)
            log.info("INICIANDO FLUJO UNIFICADO DE ENTRENAMIENTO")
            log.info("=" * 80)

            # 1. Entrenar
            self.entrenar()

            # 2. Evaluar
            self.evaluar()

            # 3. Guardar metadata completa
            self._guardar_metadata()

            log.info("=" * 80)
            log.info("✅ PROCESO COMPLETO FINALIZADO EXITOSAMENTE")
            log.info("=" * 80)

        except KeyboardInterrupt:
            log.warning("Proceso interrumpido por el usuario (Ctrl+C)")
            log.info("Intentando guardar progreso parcial...")
            try:
                self._guardar_metadata()
                log.info("Metadata guardada exitosamente.")
            except Exception:
                log.error("No se pudo guardar la metadata parcial.")
            sys.exit(130)

        except MemoryError as e:
            log.error("!!! Error de memoria insuficiente !!!")
            log.error(f"Detalles: {e}")
            log.error("Sugerencias: Reduce batch_size, window_size o el número de episodios.")
            sys.exit(137)

        except Exception as e:
            log.error("!!! Error durante el proceso de entrenamiento !!!")
            log.error(f"Error: {e}", exc_info=True)
            sys.exit(1)


def main() -> None:
    """Punto de entrada principal del script."""
    log.info("--- Iniciando script de entrenamiento unificado ---")

    try:
        # Parsear argumentos de línea de comandos
        log.debug("Parseando argumentos de línea de comandos...")
        args: Namespace = parse_args_training()
        log.debug(f"Argumentos recibidos: {args}")

        # Validar argumentos básicos
        if not hasattr(args, "symbol") or not args.symbol:
            raise ValueError("El argumento --symbol es requerido")

        if not hasattr(args, "interval") or not args.interval:
            raise ValueError("El argumento --interval es requerido")

        log.info(
            f"Configuración: {args.symbol} {args.interval} | "
            f"Train: {args.train_start_date} - {args.train_end_date} | "
            f"Eval: {args.eval_start_date} - {args.eval_end_date}"
        )

        # Crear y ejecutar entrenamiento unificado
        log.debug("Creando instancia de entrenamiento unificado...")
        entrenamiento: Entrenamiento = Entrenamiento(args)
        entrenamiento.main()

        log.info("--- Script de entrenamiento unificado finalizado exitosamente ---")

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
