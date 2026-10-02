# Metodología de diseño y fabricación del reloj

Cómo se diseña un reloj de pared de péndulo, cómo se prueba antes de gastar
dinero, y qué sale por la puerta con cada unidad.

- El **expediente** (`docs/reloj/expediente.md`) dice qué es y en qué punto está.
- El **plan de diseño** (`plan-de-diseno.md`) recorre esto pieza a pieza, de la
  primera al bastidor.
- Las **piezas** (`docs/reloj/piezas.md`) dicen qué se fabrica, en qué orden y
  de qué parámetro sale cada una.
- Los **contratos** (`docs/reloj/contratos.json`) dicen qué números no se tocan.
- Este documento dice *cómo* se diseña, se prueba y se documenta.

---

## 1. Qué manda sobre qué

Hay una intuición razonable y equivocada, y conviene deshacerla antes de cortar
nada, porque de ella depende que este proyecto sea viable en madera:

> **«Un reloj da bien la hora si las ruedas están bien cortadas.»**

No. Son dos problemas distintos, con dos soluciones distintas y dos
verificaciones distintas:

| Pregunta | Quién la decide | Qué precisión pide |
| --- | --- | --- |
| **¿Anda?** ¿O se para? | El rozamiento y el engrane | **Constancia**, no exactitud. ±0,3 mm vale si es parejo |
| **¿Da la hora?** | La longitud del péndulo | 1 mm en 994 son 43 s/día. Se corrige con una tuerca |

**La madera decide si anda; el péndulo decide si da la hora.** Un tren cortado
a mano con ±0,3 mm mantiene la hora exactamente igual de bien que uno fresado,
siempre que no agarrote: el tren no mide el tiempo, solo cuenta oscilaciones.
Lo que un tren tosco se come es **margen de par**, y eso se compensa con más
pesa.

Ahí está la viabilidad del proyecto entero. Es el equivalente del hallazgo del
escribiente —*el modelo es seis veces más fino que la pieza*— pero al revés y a
nuestro favor: aquí la pieza puede ser tosca sin que el producto empeore.

### La cadena causal, que va del péndulo hacia afuera

```
periodo del péndulo (2 s)   <- se ELIGE. Es LA decisión de producto
        |
        v  L = g·T²/4π², corregido por inercia real de varilla y lenteja
longitud del péndulo = 994 mm  ----> altura mínima de la caja
        |
        v  × dientes de la rueda de escape (30)
vuelta de la rueda de escape = 60 s  ----> aguja de segundos, gratis
        |
        v  relación hasta 1 vuelta/hora = 60:1, en dos parejas
tren de marcha: nº de dientes de cada rueda y piñón
        |
        v  × módulo del dentado
distancias entre centros  ----> tamaño de las platinas ----> ¿choca una rueda?
        ^
        |
módulo y nº de dientes  <- se eligen por socavado del piñón, holgura de
                           corte a mano y rozamiento
```

Y una segunda cadena, que no depende de la primera y se cruza con ella al final:

```
autonomía (30 h) + caída disponible en la pared (1,0 m)
        |
        v  ÷ horas por vuelta de la rueda grande (4 h) = 7,5 vueltas de tambor
        |
        v  + polea 2:1  ->  2,0 m de cuerda
diámetro del tambor = 85 mm
        |
        v  × par mínimo MEDIDO en el banco de escape
masa de la pesa  ----> esfuerzo del anclaje a la pared
```

**Lo que no está en ninguna de las dos cadenas es el aspecto.** El diámetro de
la esfera, el estilo de las agujas y la caja son libres, y por eso son el sitio
donde personalizar sin tocar ingeniería. Esa es la versión reloj del modelo
plataforma + cartucho: **el movimiento es plataforma, la esfera y la caja son
cartucho.**

### La pesa no la decide el peso de las ruedas

Es el número que más sorprende y el que ordena todo el plan de pruebas.

Un péndulo de 1 kg a 2° de amplitud almacena **5,9 mJ**. Lo que pierde por
oscilación depende de su factor de calidad Q, y ahí está la incógnita:

| Q | Pierde por oscilación | Hay que reponerle |
| --- | --- | --- |
| 500 — varilla ancha, suspensión mediocre | 75 µJ | **37 µW** |
| 1.000 | 37 µJ | **19 µW** |
| 3.000 — buena suspensión, lenteja compacta | 12 µJ | **6 µW** |

Y una pesa de 3,5 kg cayendo 1 m en 30 horas entrega **318 µW**.

**Sobra entre un factor diez y un factor cincuenta, y todo es rozamiento.**
Mantener el péndulo en marcha cuesta millonésimas de vatio; el resto se lo come
la cadena de pivotes, el engrane y, sobre todo, el escape.

Tres consecuencias que mandan sobre el plan:

1. **La masa de la pesa no se puede calcular**, porque ni el Q de un péndulo de
   madera ni el rozamiento de un pivote de madera están en ninguna tabla, y el
   resultado es su producto. Se mide. Por eso el banco de escape (R2) va antes
   que el tren, y no después.
2. **El Q del péndulo es una estimación hasta que se mida.** La primera medida
   real de R1 lo sustituye y entra en `bench/reloj/`.
3. **El suelo físico no sirve para dimensionar.** Si el tren y el escape fueran
   perfectos bastarían de 70 a 410 gramos. Ningún reloj de madera se acerca: el
   rendimiento global real anda entre el 2 y el 12 %.

### La previsión de la pesa, y por qué no bloquea nada

Hace falta un número para pedir material, aunque no esté medido. Se pone, y se
rotula como lo que es.

| | Valor | De dónde sale |
| --- | --- | --- |
| Suelo físico | 0,07 – 0,41 kg | Solo la pérdida del péndulo, con rendimiento 100 % |
| Relojes de madera comparables | 2 – 4 kg | Caída de ~1 m y 24–30 h de marcha |
| **Previsión** | **3,5 kg** | Centro del rango empírico, con la polea 2:1 |
| **Techo de diseño** | **5 kg** | Lo que aguanta la estructura sin rehacerla |

**La previsión no bloquea nada porque la pesa es la pieza más barata de
cambiar**: un tubo que se llena de perdigón o de arena hasta que el reloj anda.
Lo que no se puede redimensionar después es todo lo demás, y por eso se calcula
con el techo y no con la previsión:

| Pieza | Con el techo de 5 kg |
| --- | --- |
| Tensión de la cuerda (dos ramales) | 24,5 N, más su coeficiente de seguridad |
| Par en el tambor | 1,04 N·m |
| Eje de la rueda grande y su cojinete | Dimensionados para ese par |
| Anclaje a la pared | 49 N más el peso del reloj |

Con la previsión de 3,5 kg el par en el tambor son **730 mN·m**, quince veces
el par máximo del escribiente. No es comparable porque no es la misma máquina,
pero conviene tenerlo presente: aquí los ejes trabajan de verdad.

**R2 sustituye la previsión por una medida** y, si sale muy distinta, lo que
cambia es el contenido del tubo, no el diseño.

### El límite de conjunto, que ninguna envolvente de pieza ve

El escribiente tiene el **hueco al poste**: una cota que no mira ninguna
envolvente de leva porque surge de montar tres levas y tres postes juntos.

El reloj tiene exactamente el mismo problema con otro nombre: **la rueda grande
pasa por delante de ejes que no engrana**. Con cuatro ejes en una platina de
200 mm y una rueda grande de Ø120, hay parejas de eje y rueda que se cruzan sin
tocarse por pocos milímetros, y eso encoge cuando sube el módulo del dentado.

Es una comprobación de conjunto, vive en `compile/reloj/conjunto.py`, y tiene
su galga pasa / no pasa como la tiene el escribiente.

---

## 2. El sistema de diseño

Cuatro fuentes de verdad y una sola dirección de flujo, igual que en el
escribiente. La regla es la misma: **ningún número se teclea dos veces.**

```
     docs/reloj/contratos.json       <- LOS PARÁMETROS. Aquí y en ningún otro sitio
      /         |          \
     /          |           \
 Python     docs/piezas/      ficha_tiempo.json
compilador   fichas de        lo que el reloj ofrece
             comerciales      a otras máquinas
     |          |                   |
     v          v                   v
  ruedas y   rodamientos,      el acople futuro,
  platinas   muelle, varilla   comprobable por core/module.py
 (generadas)   (cotas)
     \          |                  /
      \         |                 /
       v        v                v
          el movimiento completo
                  |
                  v
      plantillas + DXF + dossier + lista de compra
```

### 2a. Los parámetros, en tres niveles

No todos los números son iguales, y confundirlos es lo que hace que un diseño
paramétrico se vuelva ingobernable. En el reloj hay tres clases:

**Nivel 0 · Se eligen.** Son cinco, y son las únicas preguntas de la app.

| Parámetro | Por defecto | Qué decide |
| --- | --- | --- |
| `periodo_pendulo` | 2,0 s | La longitud del péndulo y la altura de la caja |
| `dientes_escape` | 30 | Si hay aguja de segundos y qué relación pide el tren |
| `autonomia` | 30 | Vueltas de tambor, y si hace falta una rueda más |
| `caida_disponible` | 1,0 m | La polea y la longitud de la cuerda |
| `diametro_esfera` | 180 mm | Solo el aspecto. No toca el movimiento |

**Nivel 1 · Salen de la física.** El compilador las calcula y **nadie las
teclea nunca**: longitud del péndulo, vuelta de la rueda de escape, relación
total del tren, vueltas del tambor, diámetro del tambor.

**Nivel 2 · El compilador propone y la envolvente juzga.** Número de dientes de
cada rueda y piñón, módulo del dentado, diámetro de la lenteja, distancias
entre centros, tamaño de las platinas. Aquí hay varias soluciones válidas y el
compilador elige la que más margen deja, no la primera que encuentra.

### 2b. Las envolventes, enchufadas al motor que ya existe

`CLAUDE.md` dice: *un solo motor de comprobación, límites distintos por clase*.
El reloj aporta seis límites, no un validador nuevo.

| Envolvente | Límite | Por qué |
| --- | --- | --- |
| Socavado del piñón | ≥ 8 hojas | Por debajo, el perfil cicloidal se come la base del diente |
| Relación de contacto | ≥ 1,0 en todo el giro | Si baja de 1, hay un instante sin diente en contacto y el tren salta |
| Par disponible | > par demandado en cada eje, con el factor medido | Un eje justo se para el día que haga frío |
| Choque rueda-eje | ≥ 3 mm de hueco | El límite de conjunto del §1 |
| Caída de la pesa | ≤ `caida_disponible` | Si no, el reloj toca el suelo antes de las 30 h |
| Rueda en la platina | cabe con 10 mm de margen | Evidente y fácil de olvidar |

Un fallo de envolvente **no es una excepción**: es un `Veredicto` con motivo y
sugerencia, como en el escribiente.

### 2c. Lo que el reloj devuelve al escribiente

Tres cosas que el reloj necesita y el escribiente también, y que por eso se
escriben en `emit/` común y no en `emit/reloj/`:

- **La plantilla de taladrado**, que `docs/metodologia.md` ya pedía para los
  postes del escribiente y nadie ha escrito.
- **El generador de dentado**, que sirve al reductor del escribiente.
- **Un segundo perfil de impresora.** Imprimir las plantillas del reloj en otra
  copistería y medir la hoja patrón cierra la puerta pausada de **E3b**, que
  pide exactamente dos perfiles de dos máquinas distintas.

---

## 3. Cómo se prueba antes de pedir las piezas

Cuatro prototipos, cada uno con **una** pregunta. El orden no es negociable:
cada uno aporta el número que el siguiente necesita.

### 3a. El péndulo solo — ¿el modelo acierta el periodo?

Varilla, lenteja y muelle de suspensión colgados de una escuadra. Nada más.

Se cronometran **100 oscilaciones**: deben ser 200,0 s. Con un móvil, el error
de reacción humana sobre 100 ciclos baja al 0,1 %, que es justo lo que hace
falta.

Qué sale de aquí, y no se consigue de otra manera:

- **El periodo real frente al calculado.** Contrasta C11, incluido el término
  de inercia de la varilla, que es donde el péndulo simple se equivoca.
- **El Q medido**, contando cuántas oscilaciones tarda la amplitud en caer a la
  mitad. Es el número que sustituye a la estimación del §1.
- **El recorrido útil de la tuerca de regulación**, medido en segundos por
  vuelta.

Coste: una tarde y unos pocos euros. **Es la prueba con mejor relación entre lo
que cuesta y lo que decide de todo el proyecto.**

### 3b. El banco de escape — ¿cuánta pesa hace falta?

Péndulo, áncora, rueda de escape y **una sola platina provisional**. En el eje
de la rueda de escape, un hilo con una pesa pequeña.

Se añade peso hasta que el reloj arranca y mantiene la amplitud. Ese es el
**par mínimo de escape**, y es el número que dimensiona el tren entero.

Y aquí se ajustan las paletas, que es la operación que decide si el reloj
funciona:

- Poco **reposo** (el diente apoya demasiado cerca del filo): el escape se
  dispara solo con una vibración.
- Mucho reposo: pide más pesa de la necesaria.
- **Impulso** desigual entre las dos paletas: el tictac suena cojo, y se oye.

Son postizas y atornilladas justo para esto. Se ajustan, se marca la posición
buena con lápiz, y esa posición entra en `docs/reloj/contratos.json` como cota
de puesta a punto.

### 3c. El tren de marcha — ¿anda 30 horas?

Ya con las platinas definitivas, pero sin esfera ni agujas. Se da cuerda y se
mira.

Lo que caza, y es casi todo lo que falla:

- Un pivote agarrotado, que se nota porque el reloj se para siempre en el mismo
  sitio del ciclo.
- Un engrane justo, que se nota porque se para al llegar a los mismos dientes.
- La pesa real frente a la prevista en 3b.

**El criterio es binario:** 30 horas seguidas sin pararse, o no pasa.

### 3d. El reloj completo — ¿da la hora?

En la pared definitiva, con esfera y agujas. Siete días anotando la diferencia
con el móvil a la misma hora cada día.

- Primer día: se mide la deriva.
- Se corrige con la tuerca, usando los segundos por vuelta medidos en 3a.
- Seis días más para comprobar que la corrección aguanta.

**Criterio: ±1 min/día sostenido durante 7 días.** Para un reloj de madera es
un buen resultado, y se verifica sin ningún instrumento.

### 3e. Por qué este orden y no otro

Cada prototipo entrega el dato que el siguiente necesita:

| Prototipo | Entrega | Lo necesita |
| --- | --- | --- |
| Péndulo | Q real, periodo real, s/vuelta de tuerca | El escape, para saber cuánta energía reponer |
| Banco de escape | Par mínimo de escape | El tren, para dimensionar ruedas y pesa |
| Tren | Rozamiento real de la cadena completa | El reloj, para fijar la pesa definitiva |
| Reloj | Marcha en 7 días | El dossier y el producto |

Saltarse uno obliga a adivinar su número, y adivinar el par es exactamente lo
que hace que un reloj de madera no arranque.

---

## 4. El dossier de fabricación

Cinco cuadernos, igual que el escribiente y por la misma razón: los lee gente
distinta en momentos distintos.

| Cuaderno | Para quién | Qué lleva de propio del reloj |
| --- | --- | --- |
| `plantillas.pdf` | El que corta | Una hoja por material y espesor. La plantilla de taladrado va **aparte y numerada**, porque es la pieza crítica |
| `dossier.pdf` | El que monta | Secuencia, y **las cotas de puesta a punto**: reposo de paletas, caída, juego axial, altura del péndulo |
| `taller.pdf` | El taller ocupacional | Operaciones por nivel de habilidad, galgas pasa/no-pasa, qué hacer cuando no pasa |
| `verificacion.pdf` | El que firma | Las cuatro comprobaciones del §3, con casillas, y la hoja de marcha de 7 días |
| `manual.pdf` | Quien se lo lleva | Dar cuerda, poner en hora, regular con la tuerca, qué no lubricar |

**La hoja de marcha es el equivalente de la hoja de trazo patrón.** Una tabla
de siete filas donde se anota la diferencia con el móvil. Cualifica el reloj
sin instrumentos, la rellena cualquiera, y además alimenta `bench/reloj/` con
datos reales de deriva por unidad y por estación del año.

---

## 5. Utillajes y galgas

Se cortan con las mismas plantillas y del mismo material. Sin ellos la máquina
no sale igual dos veces.

| Utillaje | Para qué | Por qué importa |
| --- | --- | --- |
| **Plantilla de taladrado de platinas** | Los cuatro ejes y los pilares | Se taladran **las dos platinas apiladas**: coinciden por construcción, no por pulso |
| **Galga de centros** | Comprueba cada distancia entre ejes | Verificación binaria; en madera no hay ajuste posterior |
| **Galga de diente** | Comprueba el perfil cortado | Pasa el hueco entre dientes o no pasa |
| **Pivote de lijado** | Redondear ruedas a mano | Un disco sale redondo por construcción, no por pulso |
| **Galga de reposo** | El ajuste de las paletas del áncora | Traduce «un pelín más» a una cota repetible |
| **Cuna de montaje** | Sujeta el movimiento mientras se monta | Dos manos no bastan con cuatro ejes a la vez |

---

## 6. La app, que es el objetivo del proyecto

El reloj es el primer producto. **La app es el entregable.**

Y es mucho más simple que la del escribiente, porque la entrada no es una
escritura a mano alzada: son cinco números.

| | Escribiente | Reloj |
| --- | --- | --- |
| Captura | Lienzo táctil, trazos, privacidad | **Cinco campos** |
| Front-end | Reparametrizar, repartir θ, capacidad | Nada: los cinco números entran tal cual |
| Núcleo | C1–C4 | C11, C12 |
| Envolvente | Ángulo de presión, curvatura | Las seis del §2b |
| Salida | Tres levas | El movimiento completo + `ficha_tiempo.json` |

Eso quita de en medio la pantalla de captura, el test de privacidad y la prueba
con cinco usuarios. **La interfaz del reloj son cinco campos, un botón y una
vista previa**, y se puede escribir en una semana cuando el compilador funcione.

### Las tres pantallas

1. **Configurar.** Cinco campos, con los valores por defecto puestos. Cada uno
   dice en una línea qué cambia si lo tocas.
2. **Comprobar.** El tren dibujado a escala, los números derivados, y el
   veredicto: apto, o no apto con motivo y sugerencia. Si una envolvente falla,
   dice cuál y qué cambiar.
3. **Fabricar.** Descargar el paquete: plantillas, DXF, dossier, lista de
   compra con precios, y la ficha de tiempo.

### El pedido, de principio a fin

1. **Configurar.** Cinco campos. Segundos, no minutos.
2. **Veredicto.** Apto o no apto con motivo.
3. **Presupuesto.** Sale de la lista de compra más las horas de taller. No hace
   falta compilar para dar precio: el movimiento cuesta lo mismo.
4. **Fabricación.** Plantillas a copistería; el resto, al taller.
5. **Verificación.** Las cuatro comprobaciones y la hoja de marcha de 7 días.
6. **Entrega.** Reloj, manual y la hoja de marcha firmada.

---

## 7. Qué hay que construir, por orden de lo que desbloquea

| | Qué | Por qué ahora |
| --- | --- | --- |
| 1 | **`docs/reloj/contratos.json`** y el esqueleto de `core/reloj/` | Un número, un sitio, desde el primer día |
| 2 | **C11: péndulo físico** y su test | Es la raíz de la cadena causal entera |
| 3 | **Colgar el primer péndulo y medirlo** | Una tarde, y da el Q que no se puede calcular |
| 4 | **C11: geometría del escape** | Necesita el Q del paso 3 |
| 5 | **Banco de escape y medir la pesa mínima** | El número que dimensiona todo lo demás |
| 6 | **C12: tren y dentado**, con las seis envolventes | Ya se puede: el par de entrada está medido |
| 7 | **Plantillas, con la de taladrado** | Lo comparte el escribiente, y cierra E3b de paso |
| 8 | **Tren en madera, 30 horas** | La primera puerta física |
| 9 | **Reloj completo y 7 días de marcha** | La puerta que valida el proyecto |
| 10 | **La app: tres pantallas** | Cuando el compilador ya hace el trabajo |
| 11 | **`ficha_tiempo.json` y el contrato de eje** | El órgano temporal, listo para cuando haya qué acoplar |

Del 1 al 6 no hace falta ni copistería ni proveedor: es código, una varilla y
una tarde de taller. Del 7 en adelante, sí.
