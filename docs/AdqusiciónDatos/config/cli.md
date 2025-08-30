# Creación de cli.py

> **Resumen:** Este archivo consta únicamente de una función que devuelve los argumentos introducidos por la terminal usando argparse.

## FUnción parse_args

Esta función simplemente define los argumentos que debemos añadir al objetro parser creado. De ellos, solo son obligatorios symbol, interval y start_date. y todos son de tipo string.

# Preguntas

<details>

<summary> ¿Cómo se usa la librería argparse? </summary>

La librería `argparse` de Python se utiliza para crear interfaces de línea de comandos (CLI) de forma sencilla y estructurada. Permite definir los argumentos que un script espera recibir, los procesa desde la línea de comandos y genera automáticamente mensajes de ayuda.

En el archivo `src/AdqusicionDatos/config/cli.py`, el uso de `argparse` se puede desglosar en los siguientes pasos:

1.  **Importación**: Primero, se importa la librería.
    ````python
    import argparse
    ````

2.  **Creación del Parser**: Se instancia la clase `ArgumentParser`. Este objeto contendrá toda la información necesaria para procesar los argumentos de la línea de comandos. El parámetro `description` proporciona un texto que se muestra cuando se solicita ayuda (`-h` o `--help`).
    ````python
    parser = argparse.ArgumentParser(description="Descarga de datos históricos de Binance Futures.")
    ````

3.  **Definición de Argumentos**: Se añaden los argumentos que el script aceptará usando el método `add_argument()`.
    ````python
    parser.add_argument("--symbol", type=str, help="Símbolo del par de trading, e.g., 'BTCUSDT'.")
    parser.add_argument("--start_date", type=str, help="Fecha de inicio en formato 'YYYY-MM-DD'.")
    ````
    *   `"--symbol"`: Es el nombre del argumento que se usará en la terminal (por ejemplo, `--symbol BTCUSDT`).
    *   `type=str`: Especifica que el valor proporcionado debe ser tratado como una cadena de texto.
    *   `help="..."`: Proporciona un mensaje descriptivo para este argumento en el menú de ayuda.
    *   `default="..."`: (Como en `--config`) establece un valor por defecto si el argumento no es proporcionado por el usuario.

4.  **Procesamiento de Argumentos**: Finalmente, `parser.parse_args()` se encarga de leer los argumentos proporcionados en la terminal, los valida según las definiciones y los devuelve en un objeto para que puedan ser utilizados en el resto del programa.
    ````python
    return parser.parse_args()
    ````

#### Ejemplo de Uso

Si se ejecuta un script que use esta función desde la terminal:

```bash
python <nombre_del_script>.py --symbol ETHUSDT --interval 1h --start_date 2025-01-01
```

La función `parse_args()` devolverá un objeto (que podemos llamar `args`) donde los valores estarán accesibles como atributos:

*   `args.symbol` será `'ETHUSDT'`
*   `args.interval` será `'1h'`
*   `args.start_date` será `'2025-01-01'`

</details>