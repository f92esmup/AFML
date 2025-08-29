"""Aqui defirnimos la función de línea de comandos y parseamos los argumentos."""

import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Descarga de datos históricos de Binance Futures.")
    
    parser.add_argument("--config", type=str, default="src/AdqusicionDatos/config/config.yaml", help="Ruta al archivo de configuración YAML.")
    
    parser.add_argument("--symbol", required=True, type=str, help="Símbolo del par de trading, e.g., 'BTCUSDT'.")
    parser.add_argument("--interval", required=True, type=str, help="Intervalo de tiempo para las velas, e.g., '1m', '5m', '1h'.")
    parser.add_argument("--start_date", required=True, type=str, help="Fecha de inicio en formato 'YYYY-MM-DD'.")
    parser.add_argument("--end_date", type=str, default="", help="Fecha de fin en formato 'YYYY-MM-DD'. Si no se proporciona, se usa la fecha actual.")
    
    return parser.parse_args()
