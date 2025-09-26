# AFML: Segundo intento de crear un agente de *trading*

> **Resumen:**
> A partir de mi primer proyecto, *btcbot*, he aprendido una lección fundamental: debo asumir la mayor parte del trabajo y no delegarlo ciegamente a la IA. Esta es, sin duda, una herramienta valiosa de apoyo, pero no un sustituto del entendimiento humano.
> Uno de los principales errores que cometí fue incorporar de forma continua funcionalidades avanzadas que no llegué a comprender del todo, lo que derivó en un proyecto caótico y difícil de mantener.
> En esta nueva etapa, mi objetivo es construir un sistema **simple, funcional, documentado, testeado y escalable**. Ese será el propósito central. No pretendo que este repositorio represente el mejor sistema jamás creado, sino una base sólida sobre la que poder iterar.

---

## Workflow

El flujo de trabajo será un aspecto clave. Para evitar delegar nuevamente tareas críticas a la IA, he definido una serie de reglas y procesos claros.

* **Documentación personal:**
  Todo el proceso de diseño, razonamiento y toma de decisiones se registrará en mi **libreta personal**. Allí anotaré tanto las conclusiones extraídas de mis conversaciones con la IA como las decisiones técnicas tomadas a lo largo del proyecto.
  En particular, incluiré:

  * Un registro de las preguntas que he planteado a la IA y la respuesta que *yo* he asimilado tras analizarlas, evitando simplemente copiar el texto literal.
  * Un apartado donde describa las funcionalidades que pretendo implementar en cada módulo o función, así como el comportamiento esperado de estas.

* **Uso controlado de la IA:**
  No emplearé el modo “agente” de la IA para generar grandes bloques de código de manera automática. Podré solicitar fragmentos de código concretos, pero me comprometo a estudiar y comprender cada uno de ellos antes de integrarlos.
  Este enfoque busca minimizar la generación masiva de código difícil de revisar y mantener, favoreciendo un mayor control sobre el resultado final y evitando comportamientos inesperados.

---

> [!WARNING]
> **Advertencia de riesgo:** Este proyecto interactúa con los mercados financieros y ejecuta operaciones automatizadas en criptomonedas mediante la API de Binance. Su uso implica riesgos de pérdidas financieras. Asegúrate de comprender plenamente dichos riesgos antes de utilizar el sistema y hazlo bajo tu propia responsabilidad. Este software no ofrece garantías de rendimiento ni asesoramiento financiero.
