# Idea sobre la integración de la evaluación


Para la evaluación, he planteado un mecanismo relativamente integrado con el proceso de entrenamiento, aunque flexible. En un primer momento buscaba crear procesos completamente separados, pero la complejidad y repeticióm innecesaria de código me ha llevado a replantear la estructura. 

En el script agente.py, el cual se encarga de la orquestación de la creación del modelo, llamada del entrenamiento y guardado de pesos. Quiero implementar una función "evaluar", esta función tiene de entrada el dataset de evaluación (que habra que envolverlo en vecnormalize de nuevo y se crea su entorno también). Luego se crea el bucle de llamadas del número de episodios y como se guarda la información. Para ello tengo que refactorizar y crear una estructura modelo para el diccionario de información.

El punto fuerte de esta estructura es que puedo crear un script principal de walkforward que orqueste varias evaluaciones o simplemente ejecutar manualmente el train.py que ya estoy creando ya que se será equivalente a un walkforward. Vamos, flexibilidad total. 

Ahora ya se lo que tengo que crear y solucionar, osea que manos a la obra.