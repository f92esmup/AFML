# Portafolio.md

> **Resumen:** Este es el encargado de llevar a cabo todas las simulaciones de acciones que habitualmente harias en un broker.
El enfoque  va a ser un poco distinto. Vamos a delegar toda la gestión del riesgo al modelo (no habrá stoploss), solo estableceremos un MaxDrawdown como requisito. 
# Responsabilidades:

Respecto a la información general de una cartera debe contener:
- Balance
- Equity
- PnL (no realizado)

Respecto a las ordenes:

- Crea ordenes

- Cierra ordenes

- Calucula el PnL, comisiones y slippage.

- Registra el historial de todos los datos para cada episodio.

- Calcular el stoploss

Gestión de riesgo:

- Calculo de margen

- MaxDrawdown

# Gestión de las posiciones

# lógica de la clase

**init**

En esta función vamos a inicializar los valores:

**abrir_posicion**
La función abre una posición a MERCADO, ya sea alcista o bajista. Además, voy a añadir una función para comprob

Haber, para abrir una posición, o mejor dicho. Para saber si abrir una posición tengo que tener en cuenta el margen no? Y por ende debo calcualar también de algun modo la cantidad que se invierte del activo. y también la posición del stoploss

Osea que de este razonamiento ya podemos crear 3 funciones más:
- calcular stoploss
- calcular cantidad
- comprobar margen


Ahora bien, el margen que retiro tengo que tenerlo en cuenta porque también se descuenta del balance.

Se llama a esta tres funciones y se comprueba si los valores de margen y balance son apropiados. SI lo son se crea la nueva posición. Dicho objeto se incluye ne posiciones abiertas y por útlimo actualizamos el balance.

**_calucular posición**


**_calcular_margen**
El margen requerido para abrir una operación se calcula como una fracción del valor total de la posición. Esto es común en instrumentos apalancados, donde solo necesitas una parte del valor total de la operación como garantía.

[ \text{Margen Requerido} = \text{Precio del Activo} \times \text{Cantidad} \times \text{Porcentaje de Margen} ]

Donde:

Precio del Activo: Es el precio al que se abre la posición.
Cantidad: Es el número de unidades del activo que deseas comprar o vender.
Porcentaje de Margen: Es el porcentaje requerido por el broker o el simulador (por ejemplo, 10% o 0.1).

**_calcular_stoploss**

**_Actualizar equity y balance**



# Preguntas:

## Estrategia de calculo de cantidad y stoploss

### **Cómo funciona esta estrategia**

1. **Calcular el stop-loss usando el ATR**:
   - El stop-loss se establece a una distancia del precio de entrada basada en un múltiplo del ATR.
   - Para posiciones **long**:
     \[
     \text{Stop-Loss} = \text{Precio de Entrada} - (\text{ATR} \times \text{Multiplicador})
     \]
   - Para posiciones **short**:
     \[
     \text{Stop-Loss} = \text{Precio de Entrada} + (\text{ATR} \times \text{Multiplicador})
     \]

2. **Calcular la cantidad a invertir**:
   - La cantidad se calcula en función del **riesgo máximo permitido** (porcentaje del balance que estás dispuesto a perder si se alcanza el stop-loss).
   - Fórmula:
     \[
     \text{Cantidad} = \frac{\text{Riesgo Máximo}}{\text{Distancia al Stop-Loss}}
     \]
   - Donde:
     - **Riesgo Máximo**: Es el porcentaje del balance que estás dispuesto a arriesgar.
     - **Distancia al Stop-Loss**: Es la diferencia entre el precio de entrada y el nivel de stop-loss.

---

### **Implementación en tu clase**

#### **1. Modificar `_calcular_stop_loss` para usar el ATR**
El método `_calcular_stop_loss` debe aceptar el ATR y calcular el stop-loss dinámicamente:

```python
def _calcular_stop_loss(self, precio: float, tipo: str, atr: float, multiplicador: float = 2) -> float:
    """Calcula un stop-loss basado en el ATR y el tipo de posición."""
    if tipo == 'long':
        return precio - (atr * multiplicador)
    elif tipo == 'short':
        return precio + (atr * multiplicador)
    else:
        raise ValueError("El tipo de posición debe ser 'long' o 'short'.")
```

---

#### **2. Modificar `_calcular_cantidad` para usar el riesgo máximo**
El método `_calcular_cantidad` debe calcular la cantidad en función del riesgo máximo y la distancia al stop-loss:

```python
def _calcular_cantidad(self, precio: float, stop_loss: float, riesgo_maximo: float) -> float:
    """Calcula la cantidad a invertir basada en el riesgo máximo y la distancia al stop-loss."""
    distancia_stop_loss = abs(precio - stop_loss)
    return riesgo_maximo / distancia_stop_loss
```

---

#### **3. Modificar `abrir_posición` para integrar el ATR y el cálculo del riesgo**
El método `abrir_posición` debe calcular el stop-loss usando el ATR y determinar la cantidad a invertir en función del riesgo máximo:

```python
def abrir_posición(self, tipo: str, porcentaje_inversion: float, precio: float, atr: float, multiplicador: float = 2) -> bool:
    """Abre una nueva posición si hay suficiente margen y calcula el stop-loss usando el ATR."""

    # Validar el tipo de posición
    if tipo not in ['long', 'short']:
        raise ValueError("El tipo de posición debe ser 'long' o 'short'.")

    # Calcular el riesgo máximo permitido
    riesgo_maximo = self.balance * porcentaje_inversion

    # Calcular el stop-loss usando el ATR
    stop_loss = self._calcular_stop_loss(precio, tipo, atr, multiplicador)

    # Calcular la cantidad a invertir
    cantidad = self._calcular_cantidad(precio, stop_loss, riesgo_maximo)

    # Comprobar el margen disponible
    margen = self._calcular_margen(precio, cantidad, self.porcentaje_margen_requerido)
    if self.balance < margen:
        print("Orden rechazada: margen insuficiente.")
        return False

    # Calcular comisiones y slippage
    comision = cantidad * precio * self.comision_prc
    slippage = cantidad * precio * self.slippage_prc

    # Abrir la posición
    nueva_posicion = posicion(
        tipo=tipo,
        precio=precio,
        cantidad=cantidad,
        fecha=pd.Timestamp.now(),
        stop_loss=stop_loss,
        comision=comision,
        slippage=slippage
    )
    self.posiciones_abiertas.append(nueva_posicion)

    # Actualizar el balance
    self.balance -= (margen + comision + slippage)

    print(f"Posición {tipo} abierta: {cantidad} unidades a {precio} con stop-loss en {stop_loss}")
    return True
```

---

### **Ejemplo práctico**

Supongamos:
- **Balance**: $10,000.
- **Porcentaje de inversión**: 2% (riesgo máximo = $200).
- **Precio de entrada**: $100.
- **ATR**: $5.
- **Multiplicador del ATR**: 2.

#### **Cálculos**:
1. **Stop-Loss**:
   - Para una posición **long**:
     \[
     \text{Stop-Loss} = 100 - (5 \times 2) = 90
     \]

2. **Distancia al Stop-Loss**:
   \[
   \text{Distancia al Stop-Loss} = 100 - 90 = 10
   \]

3. **Cantidad a invertir**:
   \[
   \text{Cantidad} = \frac{200}{10} = 20 \, \text{unidades}
   \]

4. **Margen requerido** (suponiendo 10%):
   \[
   \text{Margen} = 100 \times 20 \times 0.1 = 200
   \]

---

### **Ventajas de este enfoque**
1. **Gestión de riesgo precisa**:
   - El riesgo está controlado y limitado al porcentaje especificado del balance.

2. **Adaptación a la volatilidad**:
   - Usar el ATR permite ajustar el stop-loss dinámicamente según las condiciones del mercado.

3. **Flexibilidad**:
   - Puedes ajustar el multiplicador del ATR para ser más o menos conservador.

---

### **Conclusión**
Sí, puedes usar el ATR para calcular el stop-loss y determinar la cantidad a invertir en función del riesgo máximo permitido. Este enfoque es robusto, dinámico y ampliamente utilizado en estrategias de trading profesional. Con las modificaciones sugeridas, tu simulador será capaz de manejar esta lógica de manera eficiente y realista.

## Para que sirve el @property en una clase? 
En una clase como `Portafolio`, las propiedades que definas dependerán de las responsabilidades y funcionalidades que quieras implementar. Basándome en el contexto de tu archivo Markdown y el propósito de la clase, aquí hay algunas sugerencias de propiedades y una explicación de cómo funcionan los decoradores `@property` en Python.

---

### **Propiedades sugeridas para la clase `Portafolio`**
1. **Propiedades relacionadas con el estado del portafolio**:
   - `balance`: El saldo disponible en efectivo.
   - `equity`: El valor total del portafolio (incluyendo posiciones abiertas).
   - `pnl_no_realizado`: Ganancias o pérdidas no realizadas de las posiciones abiertas.
   - `pnl_realizado`: Ganancias o pérdidas realizadas de las posiciones cerradas.

2. **Propiedades relacionadas con las órdenes**:
   - `ordenes_abiertas`: Lista de órdenes abiertas.
   - `historial_ordenes`: Registro de todas las órdenes ejecutadas.
   - `comisiones_totales`: Total de comisiones acumuladas.

3. **Propiedades relacionadas con la gestión de riesgo**:
   - `margen_usado`: Margen utilizado actualmente.
   - `margen_disponible`: Margen restante para abrir nuevas posiciones.
   - `max_drawdown`: Máxima caída del portafolio desde su punto más alto.

4. **Propiedades relacionadas con la configuración**:
   - `slippage`: Deslizamiento aplicado a las órdenes.
   - `comision`: Porcentaje o monto fijo de comisión por operación.

---

### **¿Cómo funcionan las `@property` en Python?**

El decorador `@property` se utiliza para definir métodos que actúan como atributos de solo lectura o con lógica personalizada para obtener, establecer o eliminar valores. Esto permite encapsular la lógica de acceso a los atributos mientras se mantiene una interfaz limpia.

#### **Ejemplo básico de `@property`**
```python
class Portafolio:
    def __init__(self, balance_inicial):
        self._balance = balance_inicial  # Atributo privado

    @property
    def balance(self):
        """Devuelve el balance actual del portafolio."""
        return self._balance

    @balance.setter
    def balance(self, nuevo_balance):
        """Permite actualizar el balance, con validación."""
        if nuevo_balance < 0:
            raise ValueError("El balance no puede ser negativo.")
        self._balance = nuevo_balance

    @balance.deleter
    def balance(self):
        """Permite eliminar el balance (opcional)."""
        del self._balance
```

#### **Uso del ejemplo anterior**:
```python
p = Portafolio(1000)
print(p.balance)  # Accede al balance (1000)
p.balance = 1200  # Actualiza el balance
print(p.balance)  # Nuevo balance (1200)
# p.balance = -500  # Esto lanzará un ValueError
```

---

### **Ventajas de usar `@property`**
1. **Encapsulación**: Permite controlar el acceso y la modificación de los atributos internos.
2. **Interfaz limpia**: Los métodos decorados con `@property` se usan como si fueran atributos, lo que hace que el código sea más legible.
3. **Validación**: Puedes agregar lógica para validar los valores antes de asignarlos.
4. **Compatibilidad**: Puedes cambiar la implementación interna sin afectar el código que utiliza la clase.

---
