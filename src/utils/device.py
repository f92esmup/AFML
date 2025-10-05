"""Detección automática de dispositivo (GPU/CPU) para PyTorch.

Este módulo proporciona utilidades para detectar automáticamente el mejor
dispositivo disponible (GPU/CPU) para entrenar e inferir modelos de PyTorch.
"""

import logging
import torch

log = logging.getLogger("AFML.device")


def get_device(force_cpu: bool = False) -> str:
    """
    Detecta y retorna el mejor dispositivo disponible para PyTorch.
    
    Prioridad:
    1. GPU (CUDA) si está disponible y no se fuerza CPU
    2. CPU como fallback
    
    Args:
        force_cpu: Si True, fuerza el uso de CPU ignorando GPU disponible.
                   Útil para debugging o testing.
        
    Returns:
        String con el nombre del dispositivo: 'cuda' o 'cpu'
        
    Examples:
        >>> device = get_device()
        >>> # Retorna 'cuda' si hay GPU, 'cpu' en caso contrario
        
        >>> device = get_device(force_cpu=True)
        >>> # Siempre retorna 'cpu'
    """
    if force_cpu:
        log.info("=" * 70)
        log.info("🖥️  DISPOSITIVO FORZADO: CPU")
        log.info("=" * 70)
        log.info("   El parámetro force_cpu=True está activo")
        log.info("   GPU ignorada (si está disponible)")
        log.info("=" * 70)
        return 'cpu'
    
    if torch.cuda.is_available():
        device = 'cuda'
        gpu_name = torch.cuda.get_device_name(0)
        gpu_count = torch.cuda.device_count()
        
        log.info("=" * 70)
        log.info("🚀 GPU DETECTADA - Entrenamiento/Inferencia Acelerada Habilitada")
        log.info("=" * 70)
        log.info(f"   Dispositivo seleccionado: {device.upper()}")
        log.info(f"   GPU: {gpu_name}")
        log.info(f"   Cantidad de GPUs disponibles: {gpu_count}")
        
        # CUDA version (safe check)
        try:
            cuda_version = torch.version.cuda  # type: ignore
            if cuda_version:
                log.info(f"   CUDA Version: {cuda_version}")
        except AttributeError:
            pass
        
        # Información de memoria de la GPU principal
        try:
            total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            log.info(f"   Memoria GPU total: {total_memory:.2f} GB")
        except Exception:
            pass
        
        log.info("=" * 70)
        log.info("   ✅ Los modelos se entrenarán/ejecutarán en GPU")
        log.info("   ⚡ Esperado: 5-10x más rápido que CPU")
        log.info("=" * 70)
        
        return device
    else:
        log.info("=" * 70)
        log.info("🖥️  GPU NO DISPONIBLE - Usando CPU")
        log.info("=" * 70)
        log.warning("   No se detectó GPU con CUDA disponible")
        log.warning("   El entrenamiento será más lento en CPU")
        log.info("=" * 70)
        log.info("   💡 Sugerencias para habilitar GPU:")
        log.info("      1. Verificar que tienes una GPU NVIDIA")
        log.info("      2. Instalar drivers CUDA correctamente")
        log.info("      3. Instalar PyTorch con soporte CUDA:")
        log.info("         pip install torch --index-url https://download.pytorch.org/whl/cu118")
        log.info("=" * 70)
        
        return 'cpu'


def log_device_info() -> None:
    """
    Muestra información detallada sobre PyTorch y dispositivos disponibles.
    
    Útil para debugging y verificar la configuración del entorno.
    Incluye versiones de PyTorch, CUDA, cuDNN y detalles de GPUs.
    """
    log.info("=" * 70)
    log.info("📊 INFORMACIÓN DE PYTORCH Y DISPOSITIVOS")
    log.info("=" * 70)
    
    log.info(f"PyTorch version: {torch.__version__}")
    log.info(f"CUDA disponible: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        # CUDA version (safe check)
        try:
            cuda_version = torch.version.cuda  # type: ignore
            log.info(f"CUDA version: {cuda_version}")
        except AttributeError:
            log.info("CUDA version: No disponible")
        
        # cuDNN
        if torch.backends.cudnn.is_available():
            log.info(f"cuDNN disponible: True")
            log.info(f"cuDNN version: {torch.backends.cudnn.version()}")
            log.info(f"cuDNN enabled: {torch.backends.cudnn.enabled}")
        
        # Información de cada GPU
        num_gpus = torch.cuda.device_count()
        log.info(f"Número de GPUs: {num_gpus}")
        
        for i in range(num_gpus):
            log.info(f"\n  GPU {i}:")
            log.info(f"    Nombre: {torch.cuda.get_device_name(i)}")
            
            # Propiedades del dispositivo
            props = torch.cuda.get_device_properties(i)
            total_mem_gb = props.total_memory / (1024**3)
            log.info(f"    Memoria total: {total_mem_gb:.2f} GB")
            log.info(f"    Compute capability: {props.major}.{props.minor}")
            log.info(f"    Multi-processors: {props.multi_processor_count}")
            
            # Memoria actual
            if i == torch.cuda.current_device():
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                reserved = torch.cuda.memory_reserved(i) / (1024**3)
                log.info(f"    Memoria asignada: {allocated:.2f} GB")
                log.info(f"    Memoria reservada: {reserved:.2f} GB")
    else:
        log.info("No hay GPUs NVIDIA con CUDA disponibles")
        log.info("\nDispositivos disponibles:")
        log.info(f"  - CPU: {torch.get_num_threads()} threads")
    
    log.info("=" * 70)


def is_gpu_available() -> bool:
    """
    Verifica si hay GPU disponible.
    
    Returns:
        True si CUDA está disponible, False en caso contrario
    """
    return torch.cuda.is_available()


def get_device_memory_info(device_id: int = 0) -> dict:
    """
    Obtiene información sobre el uso de memoria de una GPU específica.
    
    Args:
        device_id: ID de la GPU (default: 0)
        
    Returns:
        Diccionario con información de memoria en GB:
        {
            'total': float,
            'allocated': float,
            'reserved': float,
            'free': float
        }
        
    Raises:
        RuntimeError: Si no hay GPU disponible
    """
    if not torch.cuda.is_available():
        raise RuntimeError("No hay GPU disponible para obtener información de memoria")
    
    total = torch.cuda.get_device_properties(device_id).total_memory / (1024**3)
    allocated = torch.cuda.memory_allocated(device_id) / (1024**3)
    reserved = torch.cuda.memory_reserved(device_id) / (1024**3)
    free = total - reserved
    
    return {
        'total': round(total, 2),
        'allocated': round(allocated, 2),
        'reserved': round(reserved, 2),
        'free': round(free, 2)
    }
