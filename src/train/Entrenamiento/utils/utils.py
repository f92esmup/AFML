""" Funciones sueltas utiles. """

def calcular_steps(num_episodios: int, max_steps_per_episode: int) -> int:
    """ Calcula el número total de pasos de entrenamiento dados los episodios y pasos por episodio. """
    if num_episodios <= 0 or max_steps_per_episode <= 0:
        raise ValueError("num_episodios y max_steps_per_episode deben ser mayores que 0.")
    return num_episodios * max_steps_per_episode