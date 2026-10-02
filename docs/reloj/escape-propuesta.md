# Propuesta de diseño del escape

Qué cambia después de contrastar el escape con la demostración de Wolfram
([*The Graham Clock Escapement*](https://demonstrations.wolfram.com/TheGrahamClockEscapement/),
Erik Mahieu, 2013) y con
[*Clock and Watch Escapement Mechanics*](https://www.abbeyclock.com/EscMechanics.pdf),
de Mark Headrick.

**Esto es una propuesta, no un cambio.** Las cotas vigentes siguen en
`docs/reloj/contratos.json`. Lo que hay aquí son tres hallazgos y una decisión
que hay que tomar antes de dibujar las paletas.

---

## 1. La buena noticia: la planta ya es la de Graham

Las dos fórmulas que derivamos para el áncora son **exactamente** las de
Headrick, palabra por palabra:

| Nuestro `core/reloj/escape.py` | Headrick |
| --- | --- |
| `brazo = radio × tan(abarque/2)` | `Rp = Re × tan(half tooth span)` |
| `entre_centros = radio / cos(abarque/2)` | `cos(A) = escape_radius / distance` |

Y el abarque de 7,5 dientes sobre 30 —90° exactos— es el que Headrick llama
«generally accepted as providing the most desirable results in practice».

La distancia entre centros, el brazo y el ángulo entre brazos **no hay que
tocarlos**. Lo que falta es todo lo demás.

---

## 2. El hallazgo que invalida una envolvente: el reposo no sale del barrido

`test_el_reposo_cabe_en_el_recorrido_con_sitio_para_el_impulso` dice que los
dos reposos no pueden pasar de la mitad del barrido. **Eso es cierto en un
escape de retroceso y falso en un Graham**, y la diferencia es la razón de ser
del Graham:

> En un deadbeat la cara de reposo es un **arco centrado en el eje del
> áncora**. Mientras el diente apoya en ese arco, el áncora puede seguir
> girando sin mover la rueda y sin recibir nada. Ese tramo —el **arco
> suplementario**— es gratis.

El presupuesto angular correcto es:

```
barrido del áncora  =  reposo + impulso + caída  +  arco suplementario
                       \_________ el trabajo ________/   \_ lo que sobra _/
```

Nuestro modelo repartía el barrido entre reposo e impulso como si no existiera
el arco suplementario. Con 4° de barrido y 0,6° de reposo salía un escape
teóricamente válido y prácticamente al límite.

**La envolvente hay que reescribirla**, y de paso deja de ser la que fija el
reposo. Lo que lo fija es el punto 4.

---

## 3. El diente necesita tres ángulos, no uno

La demostración parametriza el diente con tres, y nosotros con uno. Los tres
dicen cosas distintas y los tres hacen falta para cortarlo:

| Wolfram | Valor | Qué es | Nuestro equivalente |
| --- | --- | --- | --- |
| `undercut angle` | **−8°** | Lo que la cara de ataque se inclina respecto del radio | `rueda_escape_inclinacion_diente` = 8° ✔ |
| `included angle` | **23°** | El ángulo de la punta, entre cara y dorso | **no existe** |
| `tooth thickness` | **0,5°** | Espesor de la punta, como ángulo central | **no existe** |
| `root circle radius` | **0,75** | Fondo como **fracción** del radio de punta | lo tenemos absoluto (0,844) |
| `number of spokes` | **3** | Radios de la rueda | **no existe**: la dibujamos maciza |

Que el socavado coincidiera en 8° después de la corrección de ayer es una
validación cruzada que no esperaba.

**Tres consecuencias para el dibujo:**

- **La punta no es un punto.** Con 0,5° de espesor a radio 45 son 0,39 mm de
  material en la punta. Dibujarla afilada promete un filo que el contrachapado
  no da, y es justo donde apoya la paleta.
- **El fondo relativo escala.** Declararlo como fracción y no en milímetros
  hace que cambiar el diámetro no rompa la proporción del diente.
- **La rueda lleva radios.** Es el eje más rápido del reloj: la masa ahí es la
  que hay que quitar. Tres radios, como la demostración.

---

## 4. La decisión: retroceso o Graham, y la amplitud va con ella

El contrato dice **«escape de áncora de retroceso»** y la geometría que hemos
derivado es la del **Graham**. Hay que elegir, porque las paletas son distintas:

| | Retroceso | Graham (deadbeat) |
| --- | --- | --- |
| Cara de reposo | Plano inclinado | **Arco centrado en el eje del áncora** |
| Al pasar del impulso | La rueda **retrocede** | La rueda se queda quieta |
| La marcha depende de la pesa | **Sí**, y mucho | No |
| Dificultad de la paleta | Dos planos | Un arco y un plano |

En madera la tradición manda retroceso, porque tolera errores. **Aquí hay un
argumento para lo contrario**: nuestras paletas son **postizas**, de un material
que puede no ser madera, pequeñas y rehacibles. El arco es lo único difícil y
cae en la pieza más barata de repetir.

Y lo que se gana es grande: en un reloj de madera el rozamiento varía con la
humedad y con el desgaste, así que **la pesa efectiva varía**. Con retroceso eso
se traduce en marcha; con deadbeat, no.

### Los tres paquetes coherentes

El reposo tiene un suelo que no es negociable: **tiene que superar el error de
sierra de la rueda**, ±0,3 mm declarados. Y subir el reposo obliga a subir la
amplitud, que es lo que cuesta energía.

| Paquete | Amplitud | Barrido | Reposo | Impulso | Caída | Trabajo | Suplementario | Reposo en el brazo | Energía |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Conservador | ±2,0° | 4,0° | 0,75° | 1,25° | 0,50° | 2,50° | 1,50° | 0,59 mm · **2× sierra** | ×1,0 · 13,5 µW |
| **Intermedio** | **±3,0°** | **6,0°** | **1,50°** | **2,00°** | **0,75°** | **4,25°** | **1,75°** | **1,18 mm · 3,9× sierra** | **×2,25 · 30 µW** |
| Wolfram | ±3,5° | 7,0° | 2,50° | 2,50° | 1,00° | 6,00° | 1,00° | 1,96 mm · 6,5× | ×3,06 · 41 µW |

**Recomendación: el intermedio.** El conservador deja el reposo a dos veces el
error de sierra, que en una rueda cortada a mano es demasiado poco: bastan dos
dientes mal para que el escape se dispare solo en esos. El de Wolfram es
robusto pero deja solo 1° de arco suplementario, y ese arco es el colchón que
absorbe que la pesa varíe.

**Lo que cuesta subir la amplitud no es la energía.** 30 µW siguen siendo
ridículos frente a los 318 µW que entrega la pesa prevista. Lo que cuesta es
**error circular**: un péndulo sin cicloide atrasa con la amplitud, y a ±3° la
sensibilidad es mayor. Pero es constante si la amplitud lo es —y con deadbeat
lo es—, así que se absorbe en la puesta en hora.

### Los dos arcos de reposo

Lo que hace deadbeat a un Graham son dos radios, uno por paleta, y salen del
impulso:

| Paquete | Arco de entrada | Arco de salida | Plano de impulso |
| --- | --- | --- | --- |
| Conservador | 44,51 | 45,49 | 0,98 mm |
| **Intermedio** | **44,21** | **45,79** | **1,57 mm** |
| Wolfram | 44,02 | 45,98 | 1,96 mm |

Headrick da el mismo par para su ejemplo —5,69" y 6,31" sobre un brazo de 3"—
y es la comprobación de que la construcción es la buena.

---

## 5. Qué debería ser la hoja del escape

Una sola hoja, `boceto-escape.svg`, con cinco paneles:

1. **El escape montado**, con la rueda de tres radios y el áncora de yugo
   (arco, no V: la demostración usa `yoke angle` = 20°), en la fase de reposo.
2. **Un diente**, a 10:1, con los tres ángulos y el espesor de punta.
3. **Una paleta**, a 6:1, con el arco de reposo acotado **por su radio desde el
   eje del áncora** —que es como se traza— y el plano de impulso con su ángulo.
4. **El ciclo en cuatro fases**: reposo → desbloqueo → impulso → caída. Es lo
   que anima la demostración y lo que hace entendible el escape a quien lo
   monta. Va al dossier del taller tal cual.
5. **El presupuesto angular corregido**, con el arco suplementario dibujado
   como lo que es: el colchón.

---

## 6. Qué hay que tocar, en orden

1. **Decidir retroceso o Graham.** Todo lo demás cuelga de ahí.
2. Si Graham: subir `amplitud_nominal` a 3°, y con ella `ancora_reposo` a 1,5°,
   `ancora_impulso` a 2° y `ancora_caida` a 0,75°. **Mueve la energía del
   péndulo y el par del escape**, así que `bench/reloj/pendulo.json` se
   recalcula.
3. Reescribir `test_el_reposo_cabe_en_el_recorrido_...`: la condición es
   `reposo + impulso + caída < barrido`, con el arco suplementario como holgura
   declarada, no `2 × reposo < barrido / 2`.
4. Partir `rueda_escape_inclinacion_diente` en tres cotas y pasar el fondo a
   fracción.
5. Añadir los radios de los dos arcos de reposo, derivados del impulso.
6. Añadir `rueda_escape_radios` = 3 y dibujarlos.
7. Rehacer la hoja con los cinco paneles.

**Nada de esto toca la planta**: distancia entre centros, brazo y ángulo entre
brazos se quedan como están, y eso es lo que permite proponerlo sin volver
atrás.
