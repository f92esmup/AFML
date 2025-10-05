"""Sistema de registro de operaciones en producción.

Este módulo gestiona el logging estructurado de cada paso del sistema de trading,
compatible con la estructura de info_builder del entrenamiento.
"""

import csv
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

log = logging.getLogger("AFML.Registro")


class RegistroProduccion:
    """Registra todas las operaciones y estados del sistema en archivos CSV."""
    
    def __init__(self, train_id: str) -> None:
        """
        Inicializa el sistema de registro.
        
        Args:
            train_id: Identificador del entrenamiento usado en producción
        """
        self.train_id = train_id
        
        # Crear directorio de producción (crea toda la ruta si no existe)
        self.base_dir = Path(f"entrenamientos/{train_id}/produccion")
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"📁 Directorio de producción: {self.base_dir}")
        except Exception as e:
            log.error(f"❌ Error al crear directorio de producción: {e}")
            raise RuntimeError(f"No se pudo crear el directorio de producción: {e}")
        
        # Timestamp del inicio de la sesión
        self.session_start = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Paths de archivos (convertir a Path objects para mejor manejo)
        self.registro_path = self.base_dir / f"registro_{self.session_start}.csv"
        self.emergencia_path = self.base_dir / f"emergencias_{self.session_start}.csv"
        
        # Campos del registro principal (optimizados para producción)
        # Se eliminaron campos heredados del entrenamiento que siempre eran None
        self.campos_principales = [
            # ENTORNO (5 campos)
            'timestamp',
            'paso',
            'action',
            'precio',
            'status',
            
            # PORTAFOLIO (9 campos)
            'balance',
            'equity',
            'max_drawdown',
            'pnl_total',
            'posicion_abierta',
            'tipo_posicion_activa',
            'precio_entrada_activa',
            'cantidad_activa',
            'pnl_no_realizado',
            
            # OPERACION (7 campos)
            'tipo_accion',
            'operacion',
            'resultado',
            'error',
            'trade_id',
            'precio_entrada',
            'cantidad',
            
            # VERIFICACION (3 campos opcionales para detectar inconsistencias)
            'cambio_verificado',
            'equity_previa',
            'equity_posterior',
        ]
        
        # Campos para registro de emergencias
        self.campos_emergencia = [
            'timestamp',
            'razon',
            'balance_final',
            'equity_final',
            'posiciones_cerradas',
            'detalles',
        ]
        
        # Inicializar archivos CSV
        self._inicializar_csv_principal()
        self._inicializar_csv_emergencia()
        
        log.info(f"✅ Sistema de registro inicializado")
        log.info(f"   Registro principal: {self.registro_path}")
        log.info(f"   Registro emergencias: {self.emergencia_path}")
    
    def get_session_timestamp(self) -> str:
        """
        Retorna el timestamp de inicio de sesión.
        
        Returns:
            Timestamp en formato YYYYMMDD_HHMMSS
        """
        return self.session_start
    
    def get_base_dir(self) -> Path:
        """
        Retorna el directorio base de producción.
        
        Returns:
            Path del directorio de producción
        """
        return self.base_dir
    
    def _inicializar_csv_principal(self) -> None:
        """Crea el archivo CSV principal con encabezados."""
        try:
            with open(self.registro_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos_principales)
                writer.writeheader()
            log.debug("Archivo CSV principal inicializado")
        except Exception as e:
            log.error(f"Error al inicializar CSV principal: {e}")
            raise
    
    def _inicializar_csv_emergencia(self) -> None:
        """Crea el archivo CSV de emergencias con encabezados."""
        try:
            with open(self.emergencia_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos_emergencia)
                writer.writeheader()
            log.debug("Archivo CSV de emergencias inicializado")
        except Exception as e:
            log.error(f"Error al inicializar CSV de emergencias: {e}")
            raise
    
    def registrar_paso(self, info_dict: Dict[str, Dict[str, Any]]) -> None:
        """
        Registra un paso completo del bucle principal.
        
        Args:
            info_dict: Diccionario con estructura de info_builder:
                {
                    'entorno': {...},
                    'portafolio': {...},
                    'operacion': {...},
                    'verificacion': {...}  # Opcional
                }
        """
        try:
            # Aplanar el diccionario anidado
            fila = {}
            
            # Extraer datos del entorno (solo campos relevantes)
            if 'entorno' in info_dict:
                for key in ['timestamp', 'paso', 'action', 'precio', 'status']:
                    fila[key] = info_dict['entorno'].get(key)
            
            # Extraer datos del portafolio (solo campos útiles)
            if 'portafolio' in info_dict:
                for key in ['balance', 'equity', 'max_drawdown', 'pnl_total',
                           'posicion_abierta', 'tipo_posicion_activa', 
                           'precio_entrada_activa', 'cantidad_activa', 'pnl_no_realizado']:
                    fila[key] = info_dict['portafolio'].get(key)
            
            # Extraer datos de la operación (solo lo que se usa)
            if 'operacion' in info_dict:
                for key in ['tipo_accion', 'operacion', 'resultado', 'error',
                           'trade_id', 'precio_entrada', 'cantidad']:
                    fila[key] = info_dict['operacion'].get(key)
            
            # Extraer datos de verificación (opcionales)
            if 'verificacion' in info_dict:
                for key in ['cambio_verificado', 'equity_previa', 'equity_posterior']:
                    fila[key] = info_dict['verificacion'].get(key)
            
            # Escribir fila
            with open(self.registro_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos_principales)
                writer.writerow(fila)
            
            log.debug(f"Paso {fila.get('paso')} registrado exitosamente")
            
        except Exception as e:
            log.error(f"Error al registrar paso: {e}")
            # No lanzamos excepción para no interrumpir el flujo
    
    def registrar_emergencia(
        self, 
        razon: str, 
        balance_final: float,
        equity_final: float,
        posiciones_cerradas: int,
        detalles: Optional[str] = None
    ) -> None:
        """
        Registra un evento de emergencia (cierre forzado, max drawdown, etc).
        
        Args:
            razon: Razón de la emergencia
            balance_final: Balance final tras cerrar posiciones
            equity_final: Equity final
            posiciones_cerradas: Número de posiciones cerradas
            detalles: Información adicional opcional
        """
        try:
            fila = {
                'timestamp': datetime.now().isoformat(),
                'razon': razon,
                'balance_final': balance_final,
                'equity_final': equity_final,
                'posiciones_cerradas': posiciones_cerradas,
                'detalles': detalles or '',
            }
            
            with open(self.emergencia_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos_emergencia)
                writer.writerow(fila)
            
            log.critical(f"🚨 EMERGENCIA REGISTRADA: {razon}")
            log.critical(f"   Balance final: {balance_final}")
            log.critical(f"   Equity final: {equity_final}")
            log.critical(f"   Posiciones cerradas: {posiciones_cerradas}")
            
        except Exception as e:
            log.error(f"Error al registrar emergencia: {e}")
            # Intentar al menos loggear en archivo de texto plano
            try:
                error_log = self.base_dir / f"error_emergencia_{self.session_start}.txt"
                with open(error_log, 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - {razon}\n")
                    f.write(f"Balance: {balance_final}, Equity: {equity_final}\n")
                    f.write(f"Error al escribir CSV: {e}\n\n")
            except:
                pass  # Si incluso esto falla, ya no podemos hacer nada
    
    def get_estadisticas_sesion(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la sesión actual leyendo el CSV.
        
        Returns:
            Diccionario con estadísticas básicas
        """
        try:
            import pandas as pd
            df = pd.read_csv(self.registro_path)
            
            if df.empty:
                return {
                    'pasos_totales': 0,
                    'operaciones_realizadas': 0,
                }
            
            return {
                'pasos_totales': len(df),
                'operaciones_realizadas': df['tipo_accion'].notna().sum(),
                'equity_inicial': df['equity'].iloc[0] if 'equity' in df.columns else None,
                'equity_final': df['equity'].iloc[-1] if 'equity' in df.columns else None,
                'max_drawdown': df['max_drawdown'].max() if 'max_drawdown' in df.columns else None,
            }
        except Exception as e:
            log.warning(f"No se pudieron obtener estadísticas: {e}")
            return {}