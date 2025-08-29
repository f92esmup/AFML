""" Este script orquesta la creación del dataset completo."""


from src.AdqusicionDatos import DataPipeline, parse_args

def main():
    """Función principal para ejecutar el pipeline de datos."""
    # Parsear argumentos de configuración
    args = parse_args()

    # Inicializar el pipeline de datos
    pipeline = DataPipeline(args)

    # Ejecutar el pipeline
    pipeline.run()
    
if __name__ == "__main__":
    main()