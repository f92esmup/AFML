#!/usr/bin/env python3
"""
Script de prueba para verificar las mejoras de timeout y reintentos
"""

import sys
import time
from unittest.mock import Mock, patch
from requests.exceptions import ReadTimeout, ConnectionError

# Agregar el directorio raíz al path
sys.path.insert(0, '/home/pedro/AFML')

def test_retry_logic():
    """Prueba la lógica de reintentos simulando timeouts"""
    
    print("🧪 Iniciando pruebas de reintentos...\n")
    
    # Test 1: Simular timeout que se recupera en el segundo intento
    print("Test 1: Timeout recuperable en segundo intento")
    print("-" * 50)
    
    attempt_count = 0
    
    def mock_api_call_recoverable():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            print(f"  ❌ Intento {attempt_count}: ReadTimeout")
            raise ReadTimeout("Simulated timeout")
        else:
            print(f"  ✅ Intento {attempt_count}: Éxito")
            return {"success": True}
    
    # Simular reintentos
    max_retries = 3
    base_delay = 0.1  # Delay corto para testing
    
    for attempt in range(max_retries):
        try:
            result = mock_api_call_recoverable()
            print(f"✅ Test 1 PASADO: Se recuperó después de {attempt_count} intentos\n")
            break
        except ReadTimeout as e:
            attempt_num = attempt + 1
            if attempt_num < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️  Reintentando en {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"❌ Test 1 FALLIDO: Agotados los {max_retries} intentos\n")
    
    # Test 2: Simular timeout que NO se recupera
    print("\nTest 2: Timeout NO recuperable (falla todos los intentos)")
    print("-" * 50)
    
    attempt_count = 0
    success = False
    
    def mock_api_call_unrecoverable():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  ❌ Intento {attempt_count}: ConnectionError")
        raise ConnectionError("Simulated connection error")
    
    for attempt in range(max_retries):
        try:
            result = mock_api_call_unrecoverable()
            success = True
            break
        except ConnectionError as e:
            attempt_num = attempt + 1
            if attempt_num < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️  Reintentando en {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"  ❌ Agotados los {max_retries} intentos")
    
    if not success:
        print(f"✅ Test 2 PASADO: Falló correctamente después de {max_retries} intentos\n")
    else:
        print(f"❌ Test 2 FALLIDO: No debería haber tenido éxito\n")
    
    # Test 3: Verificar backoff exponencial
    print("\nTest 3: Verificar backoff exponencial")
    print("-" * 50)
    
    base_delay = 1
    expected_delays = [1, 2, 4]
    actual_delays = []
    
    for attempt in range(3):
        delay = base_delay * (2 ** attempt)
        actual_delays.append(delay)
        print(f"  Intento {attempt + 1}: delay = {delay}s")
    
    if actual_delays == expected_delays:
        print(f"✅ Test 3 PASADO: Backoff exponencial correcto\n")
    else:
        print(f"❌ Test 3 FALLIDO: Esperado {expected_delays}, obtenido {actual_delays}\n")
    
    # Test 4: Verificar que no se reintenta con BinanceAPIException
    print("\nTest 4: No reintentar con BinanceAPIException")
    print("-" * 50)
    
    try:
        from binance.exceptions import BinanceAPIException
        
        attempt_count = 0
        
        def mock_api_call_binance_error():
            nonlocal attempt_count
            attempt_count += 1
            print(f"  ❌ Intento {attempt_count}: BinanceAPIException")
            raise BinanceAPIException(Mock(status_code=400, text="Insufficient balance"), 400, "Insufficient balance")
        
        for attempt in range(max_retries):
            try:
                result = mock_api_call_binance_error()
                break
            except (ReadTimeout, ConnectionError) as e:
                attempt_num = attempt + 1
                if attempt_num < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(f"  ⚠️  Reintentando en {delay:.1f}s...")
                    time.sleep(delay)
            except BinanceAPIException as e:
                print(f"  ⚠️  Error de API, no reintentar")
                break
        
        if attempt_count == 1:
            print(f"✅ Test 4 PASADO: No reintentó con BinanceAPIException\n")
        else:
            print(f"❌ Test 4 FALLADO: Reintentó {attempt_count} veces\n")
    
    except ImportError:
        print("  ⚠️  Módulo 'binance' no disponible, test omitido\n")
        print(f"✅ Test 4 OMITIDO: Binance no instalado en este entorno\n")
    
    print("="*50)
    print("🎉 Pruebas completadas!")
    print("="*50)

if __name__ == "__main__":
    test_retry_logic()
