"""Orquestador del sistema de trading en producción (LIVE / TESTNET).

Este script integra todos los componentes y ejecuta el bucle principal de trading.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
from binance import Client
from dotenv import load_dotenv

from src.utils.logger import setup_logger
from src.produccion.config.cli import parse_args
from src.produccion.config.config import ProductionConfig
from src.produccion.binance import BinanceConnector
from src.produccion.dataprovider import DataProvider
from src.produccion.observacion import ObservacionBuilder
from src.produccion.agente_produccion import AgenteProduccion
from src.produccion.control_riesgo import ControlRiesgo
from src.produccion.Registro import RegistroProduccion
from src.train.Entrenamiento.entorno.info_builder import build_info_dict

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logger
setup_logger()
log = logging.getLogger("AFML.live")


async def main() -> None:
    """Función principal del sistema de trading en producción."""
    
    log.info("=" * 80)
    log.info("🚀 INICIANDO SISTEMA DE TRADING EN PRODUCCIÓN")
    log.info("=" * 80)
    
    # ============================================================================
    # FASE 1: INICIALIZACIÓN DE COMPONENTES
    # ============================================================================
    
    try:
        # 1.1 Parsear argumentos
        args = parse_args()
        log.info(f"Argumentos recibidos:")
        log.info(f"  - Train ID: {args.train_id}")
        log.info(f"  - Modo: {'LIVE ⚠️' if args.live else 'TESTNET ✅'}")
        
        # 1.2 Cargar configuración
        log.info("\nCargando configuración...")
        config = ProductionConfig.load_config(args)
        
        # 1.3 Obtener credenciales de Binance desde variables de entorno
        if args.live:
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            log.warning("⚠️  MODO PRODUCCIÓN REAL - Usando credenciales reales")
        else:
            api_key = os.getenv('BINANCE_TESTNET_API_KEY')
            api_secret = os.getenv('BINANCE_TESTNET_API_SECRET')
            log.info("✅ MODO TESTNET - Usando credenciales de testnet")
        
        if not api_key or not api_secret:
            raise ValueError(
                "Credenciales de Binance no encontradas en variables de entorno. "
                "Define BINANCE_API_KEY y BINANCE_API_SECRET (o versiones TESTNET)"
            )
        
        # 1.4 Crear componentes
        log.info("\n📦 Creando componentes del sistema...")
        
        # Cliente de Binance (síncrono para operaciones)
        cliente_binance = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=not args.live
        )
        binance = BinanceConnector(cliente_binance, config)
        log.info("✅ Conector de Binance inicializado")
        
        # DataProvider (asíncrono para WebSocket)
        if config.scaler is None:
            raise ValueError("Scaler no cargado en la configuración")
        
        data_provider = DataProvider(config, config.scaler)
        await data_provider.inicializar(api_key, api_secret, testnet=not args.live)
        log.info("✅ DataProvider inicializado")
        
        # Constructor de observaciones
        observacion_builder = ObservacionBuilder(config, config.scaler)
        log.info("✅ Constructor de observaciones inicializado")
        
        # Agente SAC
        agente = AgenteProduccion(config)
        log.info("✅ Agente SAC cargado")
        
        # Control de riesgo
        control_riesgo = ControlRiesgo(config, binance)
        log.info("✅ Control de riesgo inicializado")
        
        # Sistema de registro
        registro = RegistroProduccion(config.train_id)
        log.info("✅ Sistema de registro inicializado")
        
        log.info("\n✅ Todos los componentes inicializados correctamente")
        
    except Exception as e:
        log.critical(f"❌ Error durante la inicialización: {e}")
        log.critical("Detalles del error:", exc_info=True)
        return
    
    # ============================================================================
    # FASE 2: BUCLE PRINCIPAL DE TRADING
    # ============================================================================
    
    log.info("\n" + "=" * 80)
    log.info("📊 INICIANDO BUCLE PRINCIPAL DE TRADING")
    log.info("=" * 80 + "\n")
    
    paso = 0
    
    try:
        # Stream de velas desde WebSocket
        async for nueva_vela in data_provider.stream_velas():
            
            log.info(f"\n{'='*60}")
            log.info(f"PASO {paso} - {nueva_vela['timestamp']}")
            log.info(f"{'='*60}")
            
            # ----------------------------------------------------------------
            # A. ACTUALIZAR ESTADO DE LA CUENTA
            # ----------------------------------------------------------------
            log.debug("Actualizando estado de la cuenta...")
            if not binance.get_account_info():
                log.error("Error al actualizar información de cuenta")
                continue
            
            # ----------------------------------------------------------------
            # B. VERIFICAR RIESGO PREVIO (MAX DRAWDOWN)
            # ----------------------------------------------------------------
            ok_drawdown, dd_actual = control_riesgo.verificar_drawdown()
            if not ok_drawdown:
                log.critical("🚨 MAX DRAWDOWN ALCANZADO - Activando protocolo de emergencia")
                resultado_emergencia = control_riesgo.activar_protocolo_emergencia(
                    f"Max drawdown alcanzado: {dd_actual*100:.2f}%"
                )
                
                # Registrar emergencia
                registro.registrar_emergencia(
                    razon=f"Max drawdown: {dd_actual*100:.2f}%",
                    balance_final=resultado_emergencia['balance_final'],
                    equity_final=resultado_emergencia['equity_final'],
                    posiciones_cerradas=resultado_emergencia['posiciones_cerradas'],
                    detalles=str(resultado_emergencia['errores'])
                )
                
                log.critical("Sistema detenido por max drawdown")
                break
            
            # ----------------------------------------------------------------
            # C. CONSTRUIR OBSERVACIÓN
            # ----------------------------------------------------------------
            try:
                ventana = data_provider.get_ventana_normalizada()
                binance_state = binance.get_position_info()
                obs = observacion_builder.construir_observacion(ventana, binance_state)
                log.debug("✅ Observación construida")
                
            except ValueError as e:
                # ValueError específico de NaN en ventana u otros problemas críticos
                error_msg = str(e)
                if "NaN" in error_msg or "ventana" in error_msg.lower():
                    log.critical(f"🚨 ERROR CRÍTICO en observación: {e}")
                    log.critical("Ventana de observación inválida - Activando protocolo de emergencia")
                    
                    resultado_emergencia = control_riesgo.activar_protocolo_emergencia(
                        f"Observación inválida: {e}"
                    )
                    
                    # Registrar emergencia
                    registro.registrar_emergencia(
                        razon="Ventana de observación con NaN",
                        balance_final=resultado_emergencia['balance_final'],
                        equity_final=resultado_emergencia['equity_final'],
                        posiciones_cerradas=resultado_emergencia['posiciones_cerradas'],
                        detalles=error_msg
                    )
                    
                    log.critical("Sistema detenido por ventana inválida")
                    break
                else:
                    # Otro tipo de ValueError, continuar
                    log.error(f"Error de validación al construir observación: {e}")
                    continue
                    
            except Exception as e:
                log.error(f"Error inesperado al construir observación: {e}")
                continue
            
            # ----------------------------------------------------------------
            # D. DECISIÓN DEL AGENTE
            # ----------------------------------------------------------------
            try:
                accion = agente.predict(obs)
                tipo_pos = binance_state.get('tipo_posicion_activa', None)
                accion_interpretada = agente.interpretar_accion(
                    accion, 
                    binance_state['posicion_abierta'],
                    tipo_pos if tipo_pos else 'NONE'
                )
                log.info(f"🤖 Acción del agente: {accion:.4f} → {accion_interpretada['operacion']}")
            except Exception as e:
                log.error(f"Error en decisión del agente: {e}")
                continue
            
            # ----------------------------------------------------------------
            # E. VALIDACIÓN PRE-EJECUCIÓN
            # ----------------------------------------------------------------
            if accion_interpretada['debe_ejecutar']:
                valida, razon = control_riesgo.validar_accion_pre(accion_interpretada)
                if not valida:
                    log.warning(f"⚠️  Acción rechazada: {razon}")
                    # Registrar paso sin operación
                    resultado = {'tipo_accion': 'rechazada', 'resultado': False, 'error': razon}
                else:
                    # ----------------------------------------------------------------
                    # F. EJECUCIÓN DE LA OPERACIÓN
                    # ----------------------------------------------------------------
                    try:
                        resultado = ejecutar_operacion(
                            binance, 
                            accion_interpretada, 
                            nueva_vela['close']
                        )
                        log.info(f"✅ Operación ejecutada: {resultado}")
                    except Exception as e:
                        log.error(f"Error al ejecutar operación: {e}")
                        resultado = {'tipo_accion': accion_interpretada['tipo_accion'], 
                                   'resultado': False, 'error': str(e)}
            else:
                # No hay operación que ejecutar
                resultado = {'tipo_accion': 'mantener', 'resultado': True}
            
            # ----------------------------------------------------------------
            # G. ACTUALIZAR ESTADO POST-EJECUCIÓN
            # ----------------------------------------------------------------
            binance.get_account_info()
            binance_state_final = binance.get_position_info()
            
            # ----------------------------------------------------------------
            # H. REGISTRO
            # ----------------------------------------------------------------
            try:
                info = construir_info_dict(
                    paso=paso,
                    accion=accion,
                    vela=nueva_vela,
                    binance_state=binance_state_final,
                    resultado=resultado
                )
                registro.registrar_paso(info)
                log.debug("✅ Paso registrado")
            except Exception as e:
                log.error(f"Error al registrar paso: {e}")
            
            # Incrementar paso
            paso += 1
            
            # Log resumen del paso
            log.info(f"💰 Equity: {binance_state_final['equity']:.2f} | "
                    f"Drawdown: {dd_actual*100:.1f}% | "
                    f"Posición: {binance_state_final['posicion_abierta']}")
            
    except KeyboardInterrupt:
        log.warning("\n⚠️  Interrupción por usuario (Ctrl+C)")
        
    except Exception as e:
        log.critical(f"\n❌ ERROR CRÍTICO en bucle principal: {e}")
        log.critical("Detalles del error:", exc_info=True)
        
        # Activar protocolo de emergencia
        log.critical("Activando protocolo de emergencia...")
        resultado_emergencia = control_riesgo.activar_protocolo_emergencia(
            f"Excepción crítica: {type(e).__name__} - {e}"
        )
        
        # Registrar emergencia
        registro.registrar_emergencia(
            razon=f"Error crítico: {type(e).__name__}",
            balance_final=resultado_emergencia['balance_final'],
            equity_final=resultado_emergencia['equity_final'],
            posiciones_cerradas=resultado_emergencia['posiciones_cerradas'],
            detalles=str(e)
        )
    
    finally:
        # ============================================================================
        # FASE 3: LIMPIEZA Y CIERRE
        # ============================================================================
        log.info("\n" + "=" * 80)
        log.info("🔄 FINALIZANDO SISTEMA")
        log.info("=" * 80)
        
        # Mostrar estadísticas finales
        try:
            stats = registro.get_estadisticas_sesion()
            log.info("\n📊 Estadísticas de la sesión:")
            log.info(f"  - Pasos totales: {stats.get('pasos_totales', 0)}")
            log.info(f"  - Operaciones: {stats.get('operaciones_realizadas', 0)}")
            if stats.get('equity_inicial') and stats.get('equity_final'):
                rendimiento = ((stats['equity_final'] - stats['equity_inicial']) / stats['equity_inicial']) * 100
                log.info(f"  - Rendimiento: {rendimiento:.2f}%")
        except:
            pass
        
        # Cerrar DataProvider
        await data_provider.cerrar()
        
        log.info("\n✅ Sistema finalizado correctamente")


def ejecutar_operacion(
    binance: BinanceConnector,
    accion_interpretada: Dict[str, Any],
    precio: float
) -> Dict[str, Any]:
    """
    Ejecuta la operación en Binance basada en la acción interpretada.
    Incluye sistema de reintentos.
    
    Args:
        binance: Conector de Binance
        accion_interpretada: Diccionario con tipo de operación
        precio: Precio actual del activo
        
    Returns:
        Diccionario con el resultado de la operación
    """
    max_intentos = 3
    operacion = accion_interpretada['operacion']
    intensidad = accion_interpretada['intensidad']
    order = None  # Inicializar para evitar warning
    
    for intento in range(max_intentos):
        try:
            # Calcular tamaño de posición
            cantidad = binance.calculate_position_size(
                action=intensidad if accion_interpretada['tipo_accion'] == 'long' else -intensidad,
                precio_actual=precio
            )
            
            if cantidad == 0:
                return {
                    'tipo_accion': accion_interpretada['tipo_accion'],
                    'operacion': operacion,
                    'resultado': False,
                    'error': 'Cantidad calculada es 0'
                }
            
            # Ejecutar según el tipo de operación
            if 'abrir_long' in operacion or 'aumentar_long' in operacion:
                order = binance.create_order(
                    symbol=binance.simbolo,
                    side='BUY',
                    quantity=cantidad,
                    order_type='MARKET'
                )
                
            elif 'abrir_short' in operacion or 'aumentar_short' in operacion:
                order = binance.create_order(
                    symbol=binance.simbolo,
                    side='SELL',
                    quantity=cantidad,
                    order_type='MARKET'
                )
                
            elif 'cerrar' in operacion:
                # Primero cerrar la posición actual
                posicion_info = binance.get_position_info()
                if posicion_info['posicion_abierta']:
                    side_cierre = 'SELL' if posicion_info['tipo_posicion_activa'] == 'LONG' else 'BUY'
                    order = binance.create_order(
                        symbol=binance.simbolo,
                        side=side_cierre,
                        quantity=posicion_info['cantidad_activa'],
                        order_type='MARKET',
                        reduce_only=True
                    )
                    
                    # Si es cerrar_y_abrir, abrir nueva posición
                    if 'abrir' in operacion:
                        side_nueva = 'BUY' if 'long' in operacion else 'SELL'
                        order = binance.create_order(
                            symbol=binance.simbolo,
                            side=side_nueva,
                            quantity=cantidad,
                            order_type='MARKET'
                        )
            
            # Operación exitosa
            return {
                'tipo_accion': accion_interpretada['tipo_accion'],
                'operacion': operacion,
                'resultado': True,
                'trade_id': order.get('orderId') if order else None,
                'cantidad': cantidad,
                'precio_entrada': precio,
            }
            
        except Exception as e:
            if intento < max_intentos - 1:
                log.warning(f"Intento {intento + 1} falló: {e}. Reintentando...")
                import time
                time.sleep(1)  # Usar time.sleep en lugar de asyncio.sleep
            else:
                log.error(f"Error tras {max_intentos} intentos: {e}")
                return {
                    'tipo_accion': accion_interpretada['tipo_accion'],
                    'operacion': operacion,
                    'resultado': False,
                    'error': str(e)
                }
    
    # Por si acaso no retorna en ningún caso anterior
    return {
        'tipo_accion': accion_interpretada['tipo_accion'],
        'operacion': operacion,
        'resultado': False,
        'error': 'Error desconocido en ejecución'
    }


def construir_info_dict(
    paso: int,
    accion: float,
    vela: Dict[str, Any],
    binance_state: Dict[str, Any],
    resultado: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Construye el diccionario de información compatible con info_builder.
    
    Args:
        paso: Número del paso actual
        accion: Acción del agente
        vela: Información de la vela actual
        binance_state: Estado del portfolio de Binance
        resultado: Resultado de la operación
        
    Returns:
        Diccionario estructurado según info_builder
    """
    entorno_info = {
        'paso': paso,
        'episodio': 0,  # En producción no hay episodios
        'timestamp': vela['timestamp'].isoformat(),
        'action': accion,
        'precio': vela['close'],
        'recompensa': None,  # No calculamos recompensa en producción
        'terminated': False,
        'truncated': False,
        'status': 'running',
    }
    
    portafolio_info = {
        'balance': binance_state.get('balance'),
        'equity': binance_state.get('equity'),
        'max_drawdown': binance_state.get('max_drawdown'),
        'operaciones_total': None,
        'pnl_total': binance_state.get('pnl_total'),
        'posicion_abierta': binance_state.get('posicion_abierta'),
        'trade_id_activo': None,
        'tipo_posicion_activa': binance_state.get('tipo_posicion_activa'),
        'precio_entrada_activa': binance_state.get('precio_entrada_activa'),
        'cantidad_activa': binance_state.get('cantidad_activa'),
        'velas_activa': None,
        'pnl_no_realizado': binance_state.get('pnl_no_realizado'),
    }
    
    operacion_info = {
        'tipo_accion': resultado.get('tipo_accion'),
        'operacion': resultado.get('operacion'),
        'resultado': resultado.get('resultado'),
        'error': resultado.get('error'),
        'trade_id': resultado.get('trade_id'),
        'tipo_posicion': None,
        'precio_entrada': resultado.get('precio_entrada'),
        'precio_salida': None,
        'cantidad': resultado.get('cantidad'),
    }
    
    return build_info_dict(
        entorno=entorno_info,
        portafolio=portafolio_info,
        operacion=operacion_info
    )


if __name__ == "__main__":
    # Ejecutar el bucle asíncrono
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("\n👋 Sistema detenido por el usuario")
    except Exception as e:
        log.critical(f"\n❌ Error fatal: {e}")
        sys.exit(1)
