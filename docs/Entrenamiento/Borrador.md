# Módulo de entrenamiento
> Este modulo va a tener toda la lógica referida al entorno, entrenamiento del agente, evaluación del agente, la definición del propio agente y más.

En este módulo hay mucho contenido asique voy a dividirlo en pequeñas partes:

**COnfiguración:** Seguimos la misma estructura que en el módulo de datos. Pero como quiero tratarlos como programas diferentes vamos a crearlo desde cero. Añadiremos poco a poco los valores de configuración necesaroi, ya sea por cli, metadata desde el data_id o el config.yaml.

**Entorno** El entorno para el agente de RL debe simular a la perfección como funciona un broker en la vida real. en el entorno separaremos principalmente en dos scripts. El entorno.py que usará gymnasium y el portafolio.py que tendrá la lógica para simular las transacciones de operaciones, comisiones etc.

**Agente** Este modulo es el que contiene el modelo de IA que procesara los datos. QUiero usar un SAC con un espacio de acción continuo entre -1 y 1, donde 1 sera comprar con todo lo que estamos dispuesto a arriesgar (NO todo el balance), -1 es vender y un valor que sea cero dentro de un umbral será mantener. EJ, un valor de 0.5 es una compro arriesgando el 0,5 que estamos dispuesto a perder.

**scripts** Una conjunto de script como trainer.py, evaluator.py, que funcionan como un pipeline justamente para eso. Para ejecutar un entrenameinto o evaluación completo.



# Componentes

Los componentes que vamos a crear son los siguientes:


