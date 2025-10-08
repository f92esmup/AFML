#!/usr/bin/env python3
"""
Script de prueba para el módulo DataProvider.

Prueba la selección automática de providers y muestra qué provider
se usaría para cada intervalo sin necesidad de conectarse a Binance.
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.produccion.dataprovider.factory import DataProviderFactory


def test_provider_selection():
    """Prueba la lógica de selección de providers."""
    
    print("=" * 80)
    print("PRUEBA DE SELECCIÓN AUTOMÁTICA DE DATA PROVIDER")
    print("=" * 80)
    print()
    
    # Lista de intervalos a probar
    intervalos_test = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']
    
    print(f"{'Intervalo':<12} | {'Segundos':<10} | {'Provider':<12} | Razón")
    print("-" * 80)
    
    for intervalo in intervalos_test:
        info = DataProviderFactory.get_provider_info(intervalo)
        segundos = info['segundos'] if info['segundos'] else 'N/A'
        print(f"{intervalo:<12} | {str(segundos):<10} | {info['provider']:<12} | {info['razon']}")
    
    print()
    print("=" * 80)
    print("RESUMEN POR TIPO DE PROVIDER")
    print("=" * 80)
    print()
    
    # Agrupar por tipo de provider
    intervals_by_provider = DataProviderFactory.list_intervals()
    
    websocket_intervals = [k for k, v in intervals_by_provider.items() if v == 'WebSocket']
    polling_intervals = [k for k, v in intervals_by_provider.items() if v == 'Polling']
    
    print(f"📡 WebSocket (alta frecuencia): {', '.join(sorted(websocket_intervals))}")
    print(f"🔄 Polling (baja frecuencia): {', '.join(sorted(polling_intervals))}")
    print()
    
    print("=" * 80)
    print("CONFIGURACIÓN")
    print("=" * 80)
    print()
    print(f"Umbral de decisión: {DataProviderFactory.THRESHOLD_SECONDS}s (15 minutos)")
    print(f"Criterio: < 15min = WebSocket | >= 15min = Polling")
    print()
    print("✅ Prueba completada exitosamente")
    print()


if __name__ == '__main__':
    test_provider_selection()
