"""Orquestador del sistema de trading en producción (LIVE / TESTNET).

Este script integra todos los componentes y ejecuta el bucle principal de trading.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from binance import Client
from dotenv import load_dotenv

from src.utils.logger import setup_logger, configure_production_logging
from src.produccion.config.cli import parse_args
from src.produccion.config.config import ProductionConfig
from src.produccion.binance import BinanceConnector
from src.produccion.dataprovider import DataProviderFactory
from src.produccion.observacion import ObservacionBuilder
from src.produccion.agente_produccion import AgenteProduccion
from src.produccion.control_riesgo import ControlRiesgo
from src.produccion.Registro import RegistroProduccion

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logger
setup_logger()
log = logging.getLogger("AFML.live")


async def main() -> None:
    """Función principal del sistema de trading en producción."""
    
    # ============================================================================
    # FASE 0: CONFIGURACIÓN INICIAL DE LOGGING (TEMPORAL EN CONSOLA)
    # ============================================================================
    # Primero, logging básico en consola hasta crear el directorio de producción
    setup_logger()
    log = logging.getLogger("AFML.live")
    
    log.info("Iniciando sistema...")
    
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
        log.info("Cargando configuración...")
        config = ProductionConfig.load_config(args)
        
        # 1.3 Crear sistema de registro (esto crea el directorio de producción)
        log.info("Inicializando sistema de registro...")
        registro = RegistroProduccion(config.train_id)
        
        # ============================================================================
        # FASE 0.5: RECONFIGURAR LOGGING A ARCHIVO
        # ============================================================================
        log.info("Reconfigurando logging a archivo...")
        log_file_path = configure_production_logging(
            base_dir=str(registro.get_base_dir()),
            session_timestamp=registro.get_session_timestamp()
        )
        
        # IMPORTANTE: Recrear referencia al logger después de reconfiguración
        log = logging.getLogger("AFML.live")
        
        # A partir de AHORA todos los logs irán SOLO al archivo
        log.info("=" * 80)
        log.info("🚀 INICIANDO SISTEMA DE TRADING EN PRODUCCIÓN")
        log.info("=" * 80)
        log.info(f"📝 Logs centralizados en: {log_file_path}")
        log.info(f"Argumentos recibidos:")
        log.info(f"  - Train ID: {args.train_id}")
        log.info(f"  - Modo: {'LIVE ⚠️' if args.live else 'TESTNET ✅'}")
        
        # 1.4 Obtener credenciales de Binance desde variables de entorno
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
        
        # 1.5 Crear componentes
        log.info("\n📦 Creando componentes del sistema...")
        
        # Cliente de Binance (síncrono para operaciones)
        # Timeout aumentado a 60 segundos para evitar timeouts en redes lentas
        cliente_binance = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=not args.live,
            requests_params={'timeout': 60}  # Timeout de 60 segundos
        )
        binance = BinanceConnector(cliente_binance, config)
        log.info("✅ Conector de Binance creado")
        
        # CRÍTICO: Inicializar cuenta para obtener valores REALES
        # Esto debe hacerse ANTES de crear ControlRiesgo y ObservacionBuilder
        if not binance.initialize_account():
            raise RuntimeError("❌ Error al inicializar cuenta de Binance")
        log.info("✅ Cuenta de Binance inicializada con valores REALES")
        
        # DataProvider (selección automática entre WebSocket y Polling)
        if config.scaler is None:
            raise ValueError("Scaler no cargado en la configuración")
        
        data_provider = DataProviderFactory.create(config, config.scaler)
        await data_provider.inicializar(api_key, api_secret, testnet=not args.live)
        log.info("✅ DataProvider inicializado")
        
        # Constructor de observaciones (usa equity REAL de Binance)
        observacion_builder = ObservacionBuilder(
            config, 
            config.scaler, 
            binance.equity_inicial  # Valor REAL obtenido de Binance
        )
        log.info("✅ Constructor de observaciones inicializado")
        
        # Agente SAC
        agente = AgenteProduccion(config)
        log.info("✅ Agente SAC cargado")
        
        # Control de riesgo (usa equity REAL de Binance)
        control_riesgo = ControlRiesgo(config, binance)
        log.info("✅ Control de riesgo inicializado")
        
        # NOTA: Sistema de registro ya fue creado en FASE 0.5
        log.info("✅ Sistema de registro ya inicializado")
        
        log.info("\n✅ Todos los componentes inicializados correctamente")
        
    except Exception as e:
        log.critical(f"❌ Error durante la inicialización: {e}")
        log.critical("Detalles del error:", exc_info=True)
        return
    
    # ============================================================================
    # FASE 1.5: CONFIGURACIÓN DE MONITOREO CONTINUO
    # ============================================================================
    
    # Flag compartido para señalizar emergencia desde cualquier tarea
    emergencia_activa = {"activada": False, "razon": None, "resultado": None}
    
    async def monitor_drawdown_continuo(
        intervalo_segundos: int = 30
    ) -> None:
        """Monitorea continuamente el drawdown mientras el sistema está en espera.
        
        Esta tarea se ejecuta en paralelo al bucle principal y verifica cada X segundos
        si se ha alcanzado el máximo drawdown permitido. Si se detecta, activa el
        protocolo de emergencia inmediatamente sin esperar a la siguiente vela.
        
        Args:
            intervalo_segundos: Frecuencia de verificación (default: 30 segundos)
        """
        log.info(f"🔍 Monitor de drawdown continuo iniciado (cada {intervalo_segundos}s)")
        
        while not emergencia_activa["activada"]:
            try:
                await asyncio.sleep(intervalo_segundos)
                
                # Actualizar información de cuenta
                if not binance.get_account_info():
                    log.warning("Monitor: Error al actualizar cuenta, reintentando...")
                    continue
                
                # Verificar drawdown
                ok_drawdown, dd_actual = control_riesgo.verificar_drawdown()
                
                if not ok_drawdown:
                    # DRAWDOWN EXCESIVO DETECTADO
                    log.critical("=" * 80)
                    log.critical("🚨 MONITOR CONTINUO: MAX DRAWDOWN ALCANZADO")
                    log.critical(f"   Drawdown actual: {dd_actual*100:.2f}%")
                    log.critical(f"   Límite: {config.max_drawdown_permitido*100:.2f}%")
                    log.critical("   Activando protocolo de emergencia INMEDIATAMENTE...")
                    log.critical("=" * 80)
                    
                    # Activar protocolo de emergencia
                    resultado_emergencia = control_riesgo.activar_protocolo_emergencia(
                        f"Max drawdown alcanzado (monitor continuo): {dd_actual*100:.2f}%"
                    )
                    
                    # Registrar emergencia
                    registro.registrar_emergencia(
                        razon=f"Max drawdown detectado por monitor continuo: {dd_actual*100:.2f}%",
                        balance_final=resultado_emergencia['balance_final'],
                        equity_final=resultado_emergencia['equity_final'],
                        posiciones_cerradas=resultado_emergencia['posiciones_cerradas'],
                        detalles=str(resultado_emergencia['errores'])
                    )
                    
                    # Señalizar emergencia al bucle principal
                    emergencia_activa["activada"] = True
                    emergencia_activa["razon"] = f"Max drawdown: {dd_actual*100:.2f}%"
                    emergencia_activa["resultado"] = resultado_emergencia
                    
                    log.critical("Monitor: Señal de emergencia enviada al bucle principal")
                    break
                    
                else:
                    # Todo OK, log discreto cada N iteraciones
                    # (Para no saturar los logs, solo log si drawdown > 50% del límite)
                    if dd_actual > (config.max_drawdown_permitido * 0.5):
                        log.info(f"📊 Monitor: Drawdown actual {dd_actual*100:.1f}% "
                               f"(límite: {config.max_drawdown_permitido*100:.1f}%)")
                        
            except Exception as e:
                log.error(f"Monitor: Error en verificación de drawdown: {e}")
                # Continuar monitoreando a pesar del error
                continue
        
        log.info("🔍 Monitor de drawdown continuo finalizado")
    
    # ============================================================================
    # FASE 2: BUCLE PRINCIPAL DE TRADING
    # ============================================================================
    
    log.info("\n" + "=" * 80)
    log.info("📊 INICIANDO BUCLE PRINCIPAL DE TRADING")
    log.info("=" * 80 + "\n")
    
    # Iniciar tarea de monitoreo en paralelo
    monitor_task = asyncio.create_task(monitor_drawdown_continuo(intervalo_segundos=30))
    log.info("✅ Monitor de drawdown continuo activado")
    
    paso = 0
    
    try:
        # Stream de velas desde WebSocket
        async for nueva_vela in data_provider.stream_velas():
            
            # ----------------------------------------------------------------
            # 0. VERIFICAR SI MONITOR CONTINUO ACTIVÓ EMERGENCIA
            # ----------------------------------------------------------------
            if emergencia_activa["activada"]:
                log.critical("=" * 80)
                log.critical("🚨 EMERGENCIA DETECTADA POR MONITOR CONTINUO")
                log.critical(f"   Razón: {emergencia_activa['razon']}")
                log.critical("   Sistema detenido preventivamente")
                log.critical("=" * 80)
                break
            
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
            # NOTA: Esta verificación sigue siendo necesaria como doble check
            # en el momento exacto de recibir una nueva vela
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
                
                # Señalizar emergencia al monitor (para que también se detenga)
                emergencia_activa["activada"] = True
                emergencia_activa["razon"] = f"Max drawdown: {dd_actual*100:.2f}%"
                emergencia_activa["resultado"] = resultado_emergencia
                
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
                    
                    # Señalizar emergencia al monitor
                    emergencia_activa["activada"] = True
                    emergencia_activa["razon"] = "Ventana de observación inválida"
                    emergencia_activa["resultado"] = resultado_emergencia
                    
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
                    log.warning(f"⚠️  Acción rechazada por control de riesgo: {razon}")
                    # Registrar paso sin operación
                    resultado = {
                        'tipo_accion': 'rechazada',
                        'operacion': accion_interpretada['operacion'],
                        'resultado': False,
                        'error': razon
                    }
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
                        
                        # Logging diferenciado según resultado
                        if resultado['resultado']:
                            log.info(f"✅ Operación EXITOSA: {resultado['operacion']} | "
                                   f"Trade ID: {resultado.get('trade_id', 'N/A')} | "
                                   f"Cantidad: {resultado.get('cantidad', 0):.3f}")
                        else:
                            log.warning(f"❌ Operación FALLÓ: {resultado['operacion']} | "
                                      f"Error: {resultado.get('error', 'Desconocido')}")
                            
                    except Exception as e:
                        log.error(f"❌ Excepción inesperada al ejecutar operación: {e}")
                        resultado = {
                            'tipo_accion': accion_interpretada['tipo_accion'],
                            'operacion': accion_interpretada['operacion'],
                            'resultado': False,
                            'error': str(e)
                        }
            else:
                # No hay operación que ejecutar
                resultado = {
                    'tipo_accion': 'mantener',
                    'operacion': 'mantener',
                    'resultado': True
                }
            
            # ----------------------------------------------------------------
            # G. ACTUALIZAR ESTADO POST-EJECUCIÓN
            # ----------------------------------------------------------------
            # NOTA: Siempre actualizamos para tener el estado REAL de Binance
            # Esto es necesario incluso si la operación falló
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
        # Señalizar emergencia para detener el monitor
        emergencia_activa["activada"] = True
        emergencia_activa["razon"] = "Interrupción por usuario"
        
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
        
        # Señalizar emergencia al monitor
        emergencia_activa["activada"] = True
        emergencia_activa["razon"] = f"Error crítico: {type(e).__name__}"
        emergencia_activa["resultado"] = resultado_emergencia
    
    finally:
        # ============================================================================
        # FASE 3: LIMPIEZA Y CIERRE
        # ============================================================================
        
        # Cancelar tarea de monitoreo si aún está corriendo
        if not monitor_task.done():
            log.info("Cancelando monitor de drawdown continuo...")
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                log.info("✅ Monitor de drawdown cancelado")
        
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
    Verifica el estado real antes y después para confirmar la ejecución.
    
    IMPORTANTE: Esta función NO interpreta acciones, solo las ejecuta.
    La interpretación se hace en AgenteProduccion.interpretar_accion()
    
    Args:
        binance: Conector de Binance
        accion_interpretada: Diccionario con tipo de operación ya interpretada
        precio: Precio actual del activo
        
    Returns:
        Diccionario con el resultado de la operación
    """
    operacion = accion_interpretada['operacion']
    intensidad = accion_interpretada['intensidad']
    
    # Capturar estado ANTES de intentar ejecutar
    estado_previo = binance.get_position_info()
    
    try:
        order = None
        cantidad = 0.0  # Se calculará según el tipo de operación
        
        # ========================================================================
        # BIFURCACIÓN: Operaciones de CIERRE vs ABRIR/AUMENTAR
        # ========================================================================
        
        if 'cerrar' in operacion:
            # ====================================================================
            # CASO 1: CERRAR POSICIÓN
            # ====================================================================
            # Para cerrar NO necesitamos calcular nueva cantidad ni validar margen.
            # Simplemente cerramos la cantidad que está actualmente abierta.
            
            posicion_info = binance.get_position_info()
            
            # Validar que hay una posición abierta para cerrar
            if not posicion_info['posicion_abierta']:
                log.warning(f"⚠️ No hay posición abierta para cerrar")
                return {
                    'tipo_accion': accion_interpretada['tipo_accion'],
                    'operacion': operacion,
                    'resultado': False,
                    'error': 'No hay posición abierta para cerrar',
                    'trade_id': None,
                }
            
            # Usar la cantidad activa de la posición (NO calcular nueva)
            cantidad = posicion_info['cantidad_activa']
            side_cierre = 'SELL' if posicion_info['tipo_posicion_activa'] == 'LONG' else 'BUY'
            
            log.info(
                f"🔄 Cerrando posición {posicion_info['tipo_posicion_activa']}: "
                f"{cantidad} unidades @ ${precio:.2f}"
            )
            
            # Ejecutar orden de cierre
            order = binance.create_order(
                symbol=binance.simbolo,
                side=side_cierre,
                quantity=cantidad,
                order_type='MARKET',
                reduce_only=True
            )
            
            # Si es cerrar_y_abrir, abrir nueva posición después
            # (Esto requiere calcular cantidad para la nueva posición)
            if 'abrir' in operacion:
                # Ahora SÍ calcular cantidad para la nueva posición
                cantidad_nueva = binance.calculate_position_size(
                    action=intensidad if accion_interpretada['tipo_accion'] == 'long' else -intensidad,
                    precio_actual=precio
                )
                
                if cantidad_nueva == 0:
                    log.warning(
                        f"⚠️ Posición cerrada pero no se pudo abrir nueva: balance insuficiente"
                    )
                    # La posición se cerró, pero no se abrió la nueva
                    # Esto NO es un error total, el cierre fue exitoso
                else:
                    side_nueva = 'BUY' if 'long' in operacion else 'SELL'
                    log.info(
                        f"➕ Abriendo nueva posición {accion_interpretada['tipo_accion'].upper()}: "
                        f"{cantidad_nueva} unidades @ ${precio:.2f}"
                    )
                    order = binance.create_order(
                        symbol=binance.simbolo,
                        side=side_nueva,
                        quantity=cantidad_nueva,
                        order_type='MARKET'
                    )
                    cantidad = cantidad_nueva  # Actualizar cantidad para el retorno
        
        else:
            # ====================================================================
            # CASO 2: ABRIR o AUMENTAR POSICIÓN
            # ====================================================================
            # Aquí SÍ necesitamos calcular cantidad y validar margen disponible
            
            cantidad = binance.calculate_position_size(
                action=intensidad if accion_interpretada['tipo_accion'] == 'long' else -intensidad,
                precio_actual=precio
            )
            
            # Validar que hay suficiente balance para la operación
            if cantidad == 0:
                log.warning(
                    f"⚠️ No se puede ejecutar {operacion}: balance insuficiente para margen requerido"
                )
                return {
                    'tipo_accion': accion_interpretada['tipo_accion'],
                    'operacion': operacion,
                    'resultado': False,
                    'error': 'Cantidad calculada es 0 - Balance insuficiente para margen requerido',
                    'trade_id': None,
                }
            
            # Ejecutar según el tipo de operación
            if 'abrir_long' in operacion or 'aumentar_long' in operacion:
                log.info(
                    f"{'🆕 Abriendo' if 'abrir' in operacion else '📈 Aumentando'} posición LONG: "
                    f"{cantidad} unidades @ ${precio:.2f}"
                )
                order = binance.create_order(
                    symbol=binance.simbolo,
                    side='BUY',
                    quantity=cantidad,
                    order_type='MARKET'
                )
                
            elif 'abrir_short' in operacion or 'aumentar_short' in operacion:
                log.info(
                    f"{'🆕 Abriendo' if 'abrir' in operacion else '📉 Aumentando'} posición SHORT: "
                    f"{cantidad} unidades @ ${precio:.2f}"
                )
                order = binance.create_order(
                    symbol=binance.simbolo,
                    side='SELL',
                    quantity=cantidad,
                    order_type='MARKET'
                )
        
        # ========================================================================
        # VERIFICACIÓN CRÍTICA: ¿La orden se creó?
        # ========================================================================
        if order is None:
            # La API retornó None - la operación FALLÓ
            log.error(f"❌ create_order retornó None - Operación no ejecutada en Binance")
            return {
                'tipo_accion': accion_interpretada['tipo_accion'],
                'operacion': operacion,
                'resultado': False,
                'error': 'create_order retornó None - Operación no ejecutada en Binance',
                'trade_id': None,
                'cantidad': cantidad,
                'precio_entrada': precio,
            }
        
        # ========================================================================
        # VERIFICACIÓN POST-EJECUCIÓN
        # ========================================================================
        # Actualizar estado DESPUÉS de la operación
        binance.get_account_info()
        estado_posterior = binance.get_position_info()
        
        # Comparar estados para confirmar cambio
        cambio_detectado = False
        if 'abrir' in operacion or 'aumentar' in operacion:
            # Debería haber aumentado la cantidad
            cantidad_post = estado_posterior.get('cantidad_activa') or 0
            cantidad_prev = estado_previo.get('cantidad_activa') or 0
            if cantidad_post > cantidad_prev:
                cambio_detectado = True
        elif 'cerrar' in operacion:
            # Debería haber cerrado o cambiado
            cantidad_post = estado_posterior.get('cantidad_activa') or 0
            cantidad_prev = estado_previo.get('cantidad_activa') or 0
            if not estado_posterior['posicion_abierta'] or cantidad_post != cantidad_prev:
                cambio_detectado = True
        
        # Si tenemos trade_id pero no detectamos cambio, loguear advertencia
        if not cambio_detectado and order.get('orderId'):
            log.warning(
                f"⚠️ Orden {order['orderId']} reportada como exitosa pero no se detectó cambio en posición. "
                f"Cantidad previa: {estado_previo.get('cantidad_activa', 0)}, "
                f"Cantidad posterior: {estado_posterior['cantidad_activa']}"
            )
        
        # Operación exitosa
        log.info(
            f"✅ Operación ejecutada: {operacion} | "
            f"Cantidad: {cantidad} | Trade ID: {order.get('orderId')}"
        )
        return {
            'tipo_accion': accion_interpretada['tipo_accion'],
            'operacion': operacion,
            'resultado': True,
            'trade_id': order.get('orderId'),
            'cantidad': cantidad,
            'precio_entrada': precio,
            'cambio_verificado': cambio_detectado
        }
        
    except Exception as e:
        log.error(f"❌ Excepción al ejecutar operación: {e}")
        return {
            'tipo_accion': accion_interpretada['tipo_accion'],
            'operacion': operacion,
            'resultado': False,
            'error': str(e),
            'trade_id': None
        }


def construir_info_dict(
    paso: int,
    accion: float,
    vela: Dict[str, Any],
    binance_state: Dict[str, Any],
    resultado: Dict[str, Any],
    equity_previa: Optional[float] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Construye el diccionario de información para el registro en producción.
    
    Versión optimizada: Solo incluye campos que realmente se usan en producción,
    eliminando campos heredados del entrenamiento que siempre serían None.
    
    Args:
        paso: Número del paso actual
        accion: Acción del agente
        vela: Información de la vela actual
        binance_state: Estado del portfolio de Binance
        resultado: Resultado de la operación
        equity_previa: Equity antes de la operación (opcional, para verificación)
        
    Returns:
        Diccionario estructurado para el registro
    """
    entorno_info = {
        'timestamp': vela['timestamp'].isoformat(),
        'paso': paso,
        'action': accion,
        'precio': vela['close'],
        'status': 'running',
    }
    
    portafolio_info = {
        'balance': binance_state.get('balance'),
        'equity': binance_state.get('equity'),
        'max_drawdown': binance_state.get('max_drawdown'),
        'pnl_total': binance_state.get('pnl_total'),
        'posicion_abierta': binance_state.get('posicion_abierta'),
        'tipo_posicion_activa': binance_state.get('tipo_posicion_activa'),
        'precio_entrada_activa': binance_state.get('precio_entrada_activa'),
        'cantidad_activa': binance_state.get('cantidad_activa'),
        'pnl_no_realizado': binance_state.get('pnl_no_realizado'),
    }
    
    operacion_info = {
        'tipo_accion': resultado.get('tipo_accion'),
        'operacion': resultado.get('operacion'),
        'resultado': resultado.get('resultado'),
        'error': resultado.get('error'),
        'trade_id': resultado.get('trade_id'),
        'precio_entrada': resultado.get('precio_entrada'),
        'cantidad': resultado.get('cantidad'),
    }
    
    # Información de verificación (opcional)
    verificacion_info = {}
    if 'cambio_verificado' in resultado:
        verificacion_info['cambio_verificado'] = resultado.get('cambio_verificado')
    if equity_previa is not None:
        verificacion_info['equity_previa'] = equity_previa
        verificacion_info['equity_posterior'] = binance_state.get('equity')
    
    info_dict = {
        'entorno': entorno_info,
        'portafolio': portafolio_info,
        'operacion': operacion_info,
    }
    
    # Solo añadir verificacion si tiene datos
    if verificacion_info:
        info_dict['verificacion'] = verificacion_info
    
    return info_dict


if __name__ == "__main__":
    # Ejecutar el bucle asíncrono
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("\n👋 Sistema detenido por el usuario")
    except Exception as e:
        log.critical(f"\n❌ Error fatal: {e}")
        sys.exit(1)
