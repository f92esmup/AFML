#!/bin/bash

# Script para configurar variables de entorno para el sistema de trading en producción
# Copiar este archivo a .env.sh y completar con tus credenciales

# ============================================================================
# BINANCE TESTNET (Recomendado para pruebas)
# ============================================================================
# Obtener credenciales en: https://testnet.binancefuture.com/

export BINANCE_TESTNET_API_KEY="tu_api_key_testnet_aqui"
export BINANCE_TESTNET_API_SECRET="tu_api_secret_testnet_aqui"

# ============================================================================
# BINANCE PRODUCCIÓN REAL (⚠️ USAR CON EXTREMA PRECAUCIÓN)
# ============================================================================
# Obtener credenciales en: https://www.binance.com/

export BINANCE_API_KEY="tu_api_key_real_aqui"
export BINANCE_API_SECRET="tu_api_secret_real_aqui"

# ============================================================================
# INSTRUCCIONES DE USO
# ============================================================================
# 
# 1. Copiar este archivo:
#    cp .env.example.sh .env.sh
#
# 2. Editar .env.sh y completar las credenciales
#
# 3. Cargar las variables de entorno:
#    source .env.sh
#
# 4. Verificar que se cargaron correctamente:
#    echo $BINANCE_TESTNET_API_KEY
#
# 5. Ejecutar el sistema en modo testnet:
#    python live.py --train-id <train_id>
#
# 6. Para producción real (⚠️ CUIDADO):
#    python live.py --train-id <train_id> --live
#
# ============================================================================

echo "✅ Variables de entorno configuradas"
echo ""
echo "Modo TESTNET:"
echo "  API Key: ${BINANCE_TESTNET_API_KEY:0:10}..."
echo ""
echo "Modo PRODUCCIÓN:"
echo "  API Key: ${BINANCE_API_KEY:0:10}..."
