# Propuesta · dimensionar el escribiente para tareas más grandes

2026-10-04 · estado: **propuesta, pendiente de aprobar**

La pregunta: el escribiente se queda pequeño. ¿Qué hay que agrandar para que
escriba tarjetas, dedicatorias y párrafos? La respuesta corta, medida: **no la
leva**. Una vuelta da para un renglón, y eso apenas depende del tamaño de la
máquina. Lo que escala es **el número de vueltas**: un renglón por vuelta, con
el papel avanzando entre renglón y renglón.

---

## 1. Qué limita una vuelta (medido, no estimado)

Banco: texto en inglesa Hershey enlazada, altura de x 4 mm, renglones de
75 mm. Se busca cuántas letras caben en una vuelta, letra a letra.

### Dos límites, no uno

- **El radio de la leva.** Escala exactamente con su tamaño: con la misma
  frase, 1,87 mm a ×1, 2,81 a ×1,5 y 3,74 a ×2. Es la ley `ρ ≈ Rb²/(b·ψ'')`:
  con radio base y brazo escalados por k, ρ crece con k.
- **La resolución del programa.** A 720 muestras por vuelta y 300–400 mm de
  tinta, la punta avanza 0,5 mm por muestra: más que los detalles de la letra.
  El polígono de la leva hace lazos entre muestra y muestra aunque su radio
  supere al del rodillo. A partir de cierto tamaño manda esto, no la leva.

### Y un criterio demasiado estricto

El compilador rechaza **cualquier** autocruce del perfil. Pero una leva cortada
es su **envolvente exterior**: el lazo diminuto no existe en la pieza, el
rodillo pasa por encima y la letra pierde una décima en la punta de esa vuelta,
como hace una pluma. Lo que importa es el error en el papel, y eso se puede
medir: cortar la envolvente, recorrerla por contacto (`core/cam/contacto.py`,
que ya existe) y comparar con la tinta.

| Criterio | Leva ×1 | ×1,5 | ×2 |
| --- | ---: | ---: | ---: |
| Hoy: sin autocruce, 720 muestras | 11 letras | — | — |
| Sin autocruce, muestreo convergido (2880) | 4 | 5 | 7 |
| **Envolvente cortada, error ≤ 0,25 mm, 720 muestras** | **15** | **19** | **22** |
| Envolvente cortada, error ≤ 0,25 mm, 1440 muestras | 17 | 19 | 22 |

La fila convergida enseña por qué el criterio estricto engaña: con 720 muestras
el compilador no ve los detalles finos, y la leva aprobada es en realidad una
versión filtrada de la frase. Funciona, pero el veredicto no dice cuánto se
filtró. **El error en el papel sí lo dice, y es el número que hay que poner
contra un límite** (P4).

«Feliz cumpleaños» con su swash, en **una vuelta de la máquina de hoy**:
rechazada con el criterio actual; con la envolvente cortada escribe con
**0,39 mm de error máximo y 0,02 de medio**. A ×1,5, 0,20 mm.

---

## 2. Qué cuesta agrandar la leva

| | ×1 (hoy) | ×1,5 | ×2 |
| --- | ---: | ---: | ---: |
| Letras por vuelta (≤ 0,25 mm) | 15–17 | 19 | 22 |
| Radio máximo de leva | 52 mm | 80 mm | 108 mm |
| Peso de las tres levas de POM | ~180 g | ~410 g | ~730 g |
| Ancho de la base | 256 mm | ~318 mm | ~378 mm |
| Peor caso en la punta («hola») | 1,75 mm | 1,40 mm | 1,23 mm |
| RSS en la punta | 0,84 mm | 0,64 mm | 0,55 mm |

**Doblar la máquina da un 30–45 % más de letras.** No es la palanca de la
capacidad. Lo que sí compra es **precisión**: la leva grande divide el error
de corte (P3). Es una decisión de calidad, no de capacidad, y se puede tomar
después.

El cabestrante y el cinco barras no cambian con k: el entre-ejes del
cabestrante es libre en el contrato (la cinta no lo fija), así que los
postes se pueden alejar sin tocar el brazo.

---

## 3. La arquitectura para tareas grandes: un renglón por vuelta

Es lo que hicieron los autómatas que escribían textos largos:

- **Maillardet** (hacia 1800): 72 levas apiladas, 24 juegos de tres, guardan
  cuatro dibujos y tres poemas. La memoria crece en juegos que se leen uno
  tras otro.
- **Jaquet-Droz** (1774): una pila de levas **por letra** y una rueda de
  programa que elige la siguiente. Escribe cualquier texto de hasta 40 letras.

Para un producto que reproduce **la letra del cliente**, con sus enlaces, el
modelo es el de Maillardet: el programa es la frase entera, troceada en
renglones.

### Lo que hace falta

1. **Renglón en el compilador.** Un pedido se escribe en una franja de la caja
   sin cambiar los calajes (contrato congelado: no se toca). Un texto largo se
   parte en renglones de ~17 letras, y cada renglón es una vuelta.
2. **Avance de papel.** La caja de 80 × 30 ya admite **tres renglones** sin
   mover el papel. Para más, la mesa lleva un carro con un **trinquete de un
   renglón por clic**, de mano, como el rodillo de una máquina de escribir.
   Tarjeta A6: renglón de 80 mm en sus 105 de ancho, hasta diez renglones.
3. **Memoria de varios renglones**, en dos pasos:
   - **A · un cartucho por renglón** (ahora). Se cambia a mano entre vuelta y
     vuelta, como los cilindros de una caja de música. No toca ningún contrato
     congelado. Un párrafo de cinco renglones son cinco cartuchos.
   - **B · cartucho de varios juegos** (máquina 2). Dos o tres juegos en el
     mismo eje y un indexado que cambia de juego en el vuelo de regreso, con el
     lápiz arriba. **Toca el contrato de eje, congelado**: la pila deja de ser
     de 19 mm (con 80 de máximo caben tres juegos). Se decide después de que A
     funcione en el banco.

La rueda de letras de Jaquet-Droz queda como otra línea de producto («cartucho
alfabeto»: mensajes cambiables con la letra del cliente), no como la
arquitectura de esta máquina.

---

## 4. Plan

| Fase | Qué | Toca contratos | Prueba de que está |
| --- | --- | --- | --- |
| **1** | Criterio de la envolvente: cortar la envolvente exterior, recorrerla por contacto, aceptar si el error en el papel ≤ 0,25 mm (nueva incidencia `socavado_tolerable`, aviso y no error). Test primero en `core/` | Ninguno | «Feliz cumpleaños» compila con su error medido; «Hola Mundo» con rúbrica también, si su error cabe |
| **2** | Muestras según la tinta: el compilador sube a 1440 cuando la punta avanzaría más de 0,25 mm por muestra | Ninguno | Veredicto estable entre 1440 y 2880 |
| **3** | Renglón en el compilador, con los calajes fijos | Ninguno (cartucho, pendiente) | Dos cartuchos, el mismo calaje, renglones que no se pisan |
| **4** | «Feliz cumpleaños» en dos renglones, dos cartuchos, y la animación de dos vueltas con cambio de cartucho | Ninguno | Error ≤ 0,25 mm en cada renglón; animación con la tarjeta entera |
| **5** | Carro de la mesa con trinquete de renglón (diseño, plano y montaje) | Levantamiento y base, pendientes | Tarjeta A6 de cinco renglones en la animación |
| **6** | Decidir tamaño de leva (×1 o ×1,5) por precisión, con datos del banco E4 | Bastidor y cartucho, pendientes | Medida real del error en la punta |
| — | Cartucho de varios juegos (máquina 2) | **Eje, congelado** | Se propone aparte |

Las fases 1 a 4 son software y se pueden hacer ya. La 5 es la primera pieza
nueva de hardware. La 6 espera al banco.

## Lo que se queda fuera

- Agrandar el cinco barras: la caja de 80 mm ya es un renglón de tarjeta, y el
  error en la punta crece con los eslabones.
- Subir la relación por encima de 8: gana poco y empeora la tolerancia en
  proporción directa.
- Rodillo menor: un MR52 (R2,5) ganaría algo de radio, pero el límite a ×1 ya
  no es solo el radio.
