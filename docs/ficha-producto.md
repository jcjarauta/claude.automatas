# Ficha de producto · Escribiente

Fecha: 2026-09-29. Todos los precios son de catálogo público consultado ese
día, con el enlace al lado. **Lo que no está verificado lo dice.**

Esta ficha existe para normalizar la fabricación: fija qué se compra, a quién,
y qué se hace en el taller. No es un presupuesto cerrado — faltan por pedir
media docena de precios— pero sí es el esqueleto contra el que se piden.

**El mecanizado de la pieza personalizada se externaliza**, y se trata como
coste fijo por bloque de levas. No se compra máquina mientras E4 no haya
dicho si el modelo predice la realidad. La sección 3bis lo razona y deja
escrito el criterio para reabrirlo.

---

## 1. Qué es el producto

Un autómata de sobremesa que escribe **la letra de una persona concreta**. Se
gira una manivela y un lápiz reproduce sobre el papel la frase que esa persona
escribió a mano. La máquina es la misma para todos los pedidos; lo que cambia
es el **cartucho de tres levas**, que se fabrica para cada frase y se cambia en
un minuto.

| | |
| --- | --- |
| Precio de venta objetivo | 150 – 400 € |
| Volumen | 20 – 100 unidades al año |
| Fabricación | Taller ocupacional de Arrels Fundació, Barcelona |
| Tamaño aproximado | **190 × 275 mm** de base, unos 200 mm de alto |

### Lo que ya existe y compite

**[Lanky Doodler](https://www.contraptioncart.com/shop/lankydoodler/)**, de
Shasa Bolton: el mismo mecanismo, con app de generación de levas, a **49 AUD
(unos 28 €)**, en kit o montado, y con planos para marquetería a la venta en
Etsy. No competimos con eso en precio y no deberíamos intentarlo. Lo que
vendemos es otra cosa: un objeto de nogal y latón, con **la letra de alguien**,
fabricado por personas en proceso de inserción. Si el producto acaba pareciendo
un kit de hobby caro, hemos perdido.

---

## 2. Despiece

### 2a. Cartucho — se fabrica para cada pedido

| Nº | Pieza | Cant. | Material | Proceso |
| --- | --- | --- | --- | --- |
| L-001 | Leva izquierda | 1 | POM-C negro 5 mm | Fresado CNC |
| L-002 | Leva derecha | 1 | POM-C negro 5 mm | Fresado CNC |
| L-003 | Leva del elevador | 1 | POM-C negro 5 mm | Fresado CNC |
| S-001 | Separador de pila | 2 | Latón, Ø3,2 × Ø6 × 2 | Comercial |

Las tres levas son **escalonadas** —de abajo arriba, unos Ø105, Ø95 y Ø78
según la frase: elevador, derecho e izquierdo—, con taladro de eje Ø10 y pasador de índice Ø3
a 18 mm sobre +X. La geometría la genera el compilador; el contrato de fase
está congelado en `docs/contratos.md`.

### 2b. Plataforma — se fabrica a stock

| Pieza | Cant. | Material |
| --- | --- | --- |
| Base | 1 | Nogal americano macizo 25 mm, 190 × 275 |
| Bastidor y soportes | — | Contrachapado de abedul 9 mm |
| Brazos del cinco barras | 4 | Latón o contrachapado |
| Seguidores | 3 | Contrachapado o latón |
| Manivela | 1 | Brazo de latón + pomo de madera (fabricada) |
| Volante | 1 | Disco de latón Ø104 × 6 aligerado con 6 agujeros de Ø24, 294 g (cortado) |

### 2c. Comercial

| Familia | Cant./máquina | Referencia recomendada | Proveedor | €/ud |
| --- | --- | --- | --- | --- |
| Rodillo seguidor | 3 | **MR63ZZ** (3 × 6 × **2,5**) | [123rodamiento](https://www.123rodamiento.es/rodamiento-cojinete/rodamiento-bola/una-hilera/mr63-zz), tarifa 50+ | 1,19 |
| Rodamiento del árbol | 2 | **6800-2Z** (10 × 19 × 5) | [123rodamiento](https://www.123rodamiento.es/rodamiento-cojinete/rodamiento-bola/una-hilera/6800-2rs) | 0,87 *(precio del 2RS)* |
| Árbol de levas | 1 | **W10H6**, CF53 h6 rectificado, Ra 0,3 | [Motedis](https://www.motedis.es/es/Eje-de-precision-10-mm-H6-acero-templado-y-rectificado) | 0,47 /120 mm |
| Pasador de índice | 3 | **DIN 6325 Ø3 × 16** m6 | [esutil.es](https://www.esutil.es/pasador-din-6325-cilindrico-templado-de-acero-b53d0/) | 0,14 |
| Separador de pila | 6 | **RS 224-0382**, latón Ø3,2 × Ø6 × 2 | [RS España](https://es.rs-online.com/web/p/espaciadores/2240382) | 0,19 |
| Casquillo de pivote | 3 | **igus GFM-0810-06**, valona Ø15 × 1 | [RS España](https://es.rs-online.com/web/p/plain-bearings/2692707) | 0,61 *(neto)* |
| Poste de pivote | 3 | Eje inox X46Cr13 Ø8 h6, **195 mm** (baja hasta la base y hace de pata) | [Dold Mechatronik](https://www.dold-mechatronik.de/) | ~1,00 *(sin IVA ni portes)* |
| Rueda Z60 **m0,7** latón, Ø ext 43,4 | 1 | **Mädler 26206000** | [Mädler](https://www.maedler.de/article/26206000) | 12,30 (50 ud, neto) |
| Piñón Z20 **m0,7** latón, Ø ext 15,4 | 1 | **Mädler 26202000** | [Mädler](https://www.maedler.de/article/26202000) | 8,89 (50 ud, neto) |
| Muelle del seguidor | 3 | **RS PRO 751-540**, k = 0,44 N/mm, Fmáx 19,5 N | [RS España](https://es.rs-online.com/web/p/muelles-de-compresion/0751540) | 1,25 *(neto, pack de 5)* |
| Anillo de apriete del lápiz | 1 | **Mädler 62311000GA** o hecho en latón | [Mädler](https://www.maedler.de/Article/62311000GA) | 5,63 (50 ud) |
| Tornillería M3/M4 A2 | ~20 | DIN 912 inox A-2, cajas de 100 | [Ferretería Campollano](https://www.ferreteriacampollano.com/tornilleria-y-fijaciones/tornillos-allen/din-912.html) | ~0,04 |

---

## 3. Valoración

Todo lo que sigue sale de `bench/precios.json` —una línea por partida, con
fecha, proveedor y enlace— y lo calcula `compile/coste.py`, que además lo
imprime en el informe de cada pedido. **No es una tabla escrita a mano**: se
recalcula al cambiar un precio o al cambiar la geometría.

**Todos los importes llevan IVA.** Arrels no repercute IVA en la mayor parte
de su actividad, así que el IVA soportado no se recupera: es coste. Sumar un
catálogo que da precios netos con otro que los da con IVA miente un 21 % en
la parte que no se ve, y la mitad de los proveedores de esta lista son
alemanes y cotizan en neto.

### 3a. El cartucho, que se rehace en cada pedido

| | € |
| --- | --- |
| POM-C, tres levas | 2,70 |
| Dos separadores de latón | 0,38 |
| **Corte del bloque, externalizado a precio cerrado** | **35,00** |
| **Cartucho** | **38,08** |

Los 35 € son **una previsión nuestra, no un precio pactado**: el fichero de
precios lo marca con `cerrado: false` y el informe de cada pedido lo dice.
Cuando haya presupuesto firmado se sustituye el número y se pone el nombre
del taller. De dónde sale esa cifra, y qué hay que negociar para que no
suba, está en la sección siguiente.

### 3b. La plataforma, que va a stock

| Partida | Cant. | €/ud | € |
| --- | --- | --- | --- |
| Rueda del reductor, Mädler m0,7 Z60 latón | 1 | 14,88 | 14,88 |
| Piñón del reductor, Mädler m0,7 Z20 latón | 1 | 10,76 | 10,76 |
| Base de nogal americano 25 mm, 190 × 275 | 1 | 19,30 | 19,30 |
| Portaminas Staedtler 780 C | 1 | 8,98 | 8,98 |
| Rodillos y pivotes, MR63ZZ | 7 | 1,19 | 8,33 |
| Anillo de apriete del lápiz | 1 | 6,81 | 6,81 |
| Cinta del amplificador, fleje 1.4310 0,05 × 5 | 1 | 4,57 | 4,57 |
| Muelles de compresión RS PRO 751-540 | 3 | 1,51 | 4,54 |
| Contrachapado de abedul 9 mm | 1 | 4,43 | 4,43 |
| Postes de pivote, inox Ø8 h6 | 3 | 1,21 | 3,63 |
| Volante, material (disco de plancha de latón Ø104 × 6) | 1 | 5,57 | 5,57 |
| Casquillos igus GFM-0810-06 | 3 | 0,74 | 2,21 |
| Rodamientos del árbol, 6800-2Z | 2 | 0,69 | 1,38 |
| Tornillería inox A2 | 20 | 0,04 | 0,80 |
| Árbol de levas, Ø10 h6 rectificado | 1 | 0,47 | 0,47 |
| Pasadores de índice DIN 6325 Ø3 | 3 | 0,14 | 0,42 |
| Acabado Osmo 3062 | 1 | 0,30 | 0,30 |
| **Plataforma** | | | **97,39** |

La **base casi dobla** su línea, de 10,39 a 19,30: al cerrar la planta pasó
de 154 a 275 mm de fondo, así que una tabla de 2 m da 7 bases y no 13. El
precio del material no ha cambiado; lo que ha cambiado es cuántas salen.
Falta confirmar que la tabla da los 190 de ancho, y por eso la línea está
sin verificar.

### 3c. El total, y lo que dice

| | € |
| --- | --- |
| Cartucho | 38,08 |
| Plataforma | 97,39 |
| **Material y compras de un escribiente** | **135,47** |

Son **70 € más** de lo que decía la estimación anterior de 60-65 €, y la
diferencia no es que algo haya subido: es que antes faltaban el corte, los
muelles, los casquillos, los postes, el portaminas y el material del
volante, y que la mitad de los precios estaban en neto.

Sobre un PVP de 150-400 €, esto es entre el **30 % y el 79 %**. En el
extremo bajo de la horquilla el producto no deja margen para pagar horas de
taller, que es de lo que se trata. **La conclusión de precio es que el
escribiente no se puede vender a 150 €.** Su sitio está en 300-400.

Dónde está el dinero, por orden:

1. **El corte del bloque, 35,00 €** — casi un 30 % del total, y es la única
   partida que se paga en cada pedido. Es también la única que todavía no
   tiene presupuesto.
2. **La transmisión, 25,64 €** — dos engranajes. Pasar de módulo 1 a módulo
   0,7 ya ahorró 2,63 € y bajó la rueda de Ø62 a Ø43. Una transmisión por
   correa GT2 costaría unos 10 € y es la alternativa a valorar con la pieza
   en la mano.
3. **La madera y el portaminas, 19,67 €** — y esto es lo que se ve y se
   toca. No se toca.

---

## 3bis. El corte de las levas: por qué 35 € y qué negociar

**Decisión tomada: el mecanizado de la pieza personalizada se externaliza**,
y se asume como coste fijo por bloque de levas. No se compra máquina. El
motivo es de orden, no de dinero: **E4 —el banco de ensayo— todavía no ha
dicho si el modelo predice la realidad**, y no se inmoviliza capital en la
fabricación de un producto cuyo número clave sigue siendo una promesa. Al
final de esta sección está el criterio para reabrirlo.

Externalizar a precio cerrado tiene además dos ventajas que no son menores:

- **Se presupuesta sin compilar.** El bloque cuesta lo mismo sea cual sea la
  frase, así que se puede dar precio al cliente antes de que escriba nada.
  Con tarifa por hora habría que compilar para saber qué cobrar.
- **La conversación del amarre se tiene una vez.** Ver abajo por qué eso
  vale la mitad del precio.

### De dónde salen los 35 €

**Ningún proveedor publica lo que cuesta esta pieza.** Se han mirado once
plataformas de mecanizado online y seis talleres de Barcelona: todas piden
subir el archivo, y ninguna publica tarifa, mínimo ni setup. Lo único
publicado son precios por hora.

Así que la cifra no se copia de ninguna tabla: se acota calculando. El
compilador conoce la geometría exacta de cada leva, y con unos parámetros de
corte declarados sale el tiempo de máquina.

| | |
| --- | --- |
| Contorno de una leva | 327 mm |
| Recorrido de la fresa | 336 mm por pasada — va por fuera, y eso son 2·π·r_fresa de más |
| Pasadas | 3 de desbaste (1,8 mm) + 1 de acabado |
| Taladros | Ø10 interpolado en helicoidal, Ø3 pinchado |
| **Tiempo de máquina, las tres levas** | **7,5 min** |

Contrastado por dos caminos que no comparten código: por recorrido de
herramienta salen 7,5 min, y por volumen arrancado dividido entre la tasa de
arranque salen 4,1 min de desbaste, a los que el acabado añade lo que falta.
Hay un test que lo comprueba.

Con eso, el corte del bloque debería costar:

| Escenario | Tarifa | Corte del bloque |
| --- | --- | --- |
| Taller universitario (UPM) | 38 €/h | 14,27 € |
| Taller universitario (Unizar) | 55,85 €/h | 20,97 € |
| Fab Lab con mínimo de 30 min | 65 €/h | 32,50 € |
| Mercado europeo, 3 ejes | 95 €/h | 35,67 € |
| **Las tres por separado, tres amarres** | 55,85 €/h | **48,90 €** |

**35 € acota por arriba todo salvo el caso malo**, y el caso malo es
evitable. Por eso es la previsión que se usa hasta tener presupuesto.

### Lo que hay que negociar, y no es el precio por hora

Siete minutos y medio de máquina a 55,85 €/h son **7 €**. Todo lo demás es
**preparación**: los quince minutos de amarrar, poner cero y cargar el
programa. De ahí salen las tres únicas cosas que hay que llevar al taller:

1. **Que las tres levas del pedido salgan de un solo amarre.** Mismo
   material, mismo espesor, mismo programa. Es la diferencia entre 21 € y
   49 €, sin que cambie un milímetro de geometría.
2. **Cuál es el mínimo de facturación.** Con un trabajo de veinte minutos,
   el mínimo *es* el precio. Es el número que más puede desviar la
   previsión.
3. **Un precio cerrado por bloque, no una tarifa.** Con 20 a 100 pedidos al
   año hay volumen para pedirlo, y quita la negociación de cada pedido.

Una nota de contexto para esa conversación: de una plancha de 1 × 1 m salen
**81 levas, o sea 27 cartuchos**. Al taller le conviene saberlo, porque
significa que el material lo pone una vez por trimestre y no por pedido.

### Cuándo se reabre lo de la máquina propia

Aparcado, no descartado. Los números para cuando toque: el trabajo anual de
máquina son **2,5 a 12,5 horas** a 20-100 pedidos, y una fresadora de
sobremesa capaz de esta pieza está entre 1.450 € (Genmitsu PROVerXL 4030) y
5.250 € (Makera Carvera), con la Makera Carvera Air (2.249 €) y la Carbide
Nomad 3 (~3.390 €) en medio. A 35 € de corte por bloque, una máquina de
2.250 € se paga con **64 cartuchos**.

Pero la amortización no es el argumento bueno, y conviene decirlo antes de
que alguien lo use: en un taller ocupacional la hora de taller no es un
coste que se evita, **es el producto**. Los argumentos buenos son otros dos,
y los dos son de plazo:

- **El cartucho es la única pieza que no se puede tener a stock.**
  Encargarlo fuera mete entre tres días y dos semanas entre el pedido y la
  entrega.
- **E4 se hace cortando levas, midiéndolas y volviendo a cortar.** Con corte
  externo, cada vuelta de ese bucle son dos semanas.

**El criterio para reabrirlo**, entonces, no es un número de pedidos: es que
E4 esté cerrado y que el plazo de entrega se haya convertido en el cuello de
botella real. Si eso pasa, lo que hay que comprobar antes de comprar nada es
que la máquina llega a ±0,05 mm **en el canto**, no en el movimiento:
ninguna especificación de fabricante lo dice, y hay que cortar una leva de
prueba y medirla.

## 4. Decisiones que esta ficha normaliza

### Las levas van en POM, no en metacrilato

El render del producto las enseñaba transparentes y es tentador. No:

| | POM-C | PMMA colada |
| --- | --- | --- |
| Fricción contra acero | **0,32** | 0,5 |
| Desgaste contra acero | **8,9 µm/km** | sin dato publicado |
| Impacto **sin** entalla | **no rompe** | 18 kJ/m² |
| Impacto **con** entalla | — | **1,60 kJ/m²**, pierde un factor once |

La leva tiene dos agujeros y zonas de curvatura mínima: son concentradores de
tensión, que es justo lo que el PMMA no perdona. A millones de ciclos una leva
de metacrilato no se desgasta, **se agrieta desde un agujero**. Y la tolerancia
de espesor del metacrilato colado es ±10 %: sobre tres levas apiladas, hasta
1,5 mm de error en una pila que tiene 11 mm de hueco.

El metacrilato sí tiene su sitio: **una campana transparente** que deje ver el
cartucho girando. Ahí corta precioso a láser y no soporta carga.

### Las levas se fresan, no se cortan a láser

Cortar POM a láser **libera formaldehído**, irritante de piel y pulmón. En un
taller ocupacional eso es motivo suficiente por sí solo. Además el láser deja
conicidad en el canto y libera tensiones que alabean la pieza — y el canto de
la leva es *la* superficie funcional de toda la máquina.

[Polygom](https://www.polygom.es/), en Carrer Caracas 11 de Barcelona, vende la
plancha **y** tiene taller de CNC propio. El láser se queda para el
contrachapado y el metacrilato, donde es el proceso correcto.

### Los postes bajan de Ø16 a Ø8

Esto lo destapó la investigación y es el hallazgo más valioso de la tanda.
El conjunto calculaba el hueco contra el **poste desnudo**, pero un poste
necesita casquillo, y los casquillos con valona tienen la valona mucho mayor:

| Obstáculo real | Ø | Hueco a la leva | |
| --- | --- | --- | --- |
| Poste Ø16 desnudo *(lo que suponíamos)* | 16 | 9,0 mm | |
| + casquillo de bronce B-16-22-16, valona Ø28 | 28 | **3,0 mm** | **aviso** |
| Poste Ø8 + casquillo de bronce B-8-12-8, valona Ø16 | 16 | 9,0 mm | limpio |
| **Poste Ø8 + igus GFM-0810-06, valona Ø15** | **15** | **9,5 mm** | **limpio** |
| Pivote sobre dos MR63ZZ en un eje Ø3 | 6 | 14,0 mm | limpio |

Con el casquillo de bronce sobre Ø16 el hueco se quedaba en 3 mm y saltaba el
aviso: **el límite de conjunto habría pasado de "qué frases caben" a "no cabe
ninguna"**. Y el Ø16 nunca estuvo justificado: con 0,7 N de fuerza tangencial,
un Ø8 sobra por dos órdenes de magnitud. `Cartucho.radio_poste` pasa a ser el
radio del **obstáculo**, no el del poste, y su valor por defecto es 7,5 mm.

**Una corrección sobre lo que se escribió primero.** La primera versión de
esta ficha daba la valona del GFM-0810 como Ø12 y el hueco como 11,0 mm. La
ficha de igus dice **d3 = 15 mm**, y con eso el hueco son 9,5. Sigue siendo
holgado —el mínimo son 3— pero con menos margen del que se anunció. El Ø12
sí existe en igus, en el **GFM-081012-125**, que es otra referencia y mide
12,5 mm de largo; está por confirmar con el plano del fabricante.

### El rodillo se escribe MR63**ZZ**, con las dos letras

Tres correcciones de catálogo que cambian cotas:

1. **El 683 no es equivalente al MR63.** Mide 3 × 7 × 3, no 3 × 6 × 2,5.
2. **El MR63 abierto es 3 × 6 × 2,0.** Solo el blindado mide 2,5 de ancho.
   Pedir "MR63" a secas trae el abierto y deja **0,5 mm de juego axial**.
3. **MR63 no es medida ISO.** SKF, FAG, NSK y NTN no la fabrican; solo ZEN,
   EZO, NMB y genéricos. Si algún día hace falta cadena de suministro de marca
   europea, el diseño tendría que girar sobre **623 (3 × 10 × 4)**.

Y blindado **ZZ**, no 2RS: con Ø3 de agujero, dos retenes de contacto generan
un par de arrastre del orden del par de tracción disponible en el contacto. **El
rodillo dejaría de rodar y deslizaría**, labrando una cara plana y haciendo que
el error de trazo deje de ser repetible.

### El pasador de índice va deslizante en el POM

`docs/contratos.md` congela un pasador Ø3 m6. Pero **m6 está pensado para
apretar en acero**, y el POM fluye en frío: el apriete se relaja en semanas y
el calaje se pierde **después de la venta**, en silencio. El pasador debe ser
**deslizante en las tres levas y apretado solo en el plato de arrastre
metálico**. El argumento del contrato se mantiene —el error de fase sigue
siendo imposible, no improbable— y deja de depender de una interferencia sobre
plástico.

### El muelle es de compresión

De los tres tipos, el de tracción es el peor aquí: rompe por el gancho, se
puede desenganchar y **tintinea**, que en un objeto cuyo argumento es que suena
bien lo descalifica. El de compresión va guiado y cautivo, y la precarga se
ajusta con un tornillo sin tocar geometría.

Dimensionado: **blando y muy precargado**, de modo que los 9° de recorrido
cambien la fuerza menos de un 15 %. Eso pide **K entre 0,8 y 1,5 N·mm/°** con
par máximo ≥ 80 N·mm. Ninguna referencia de stock que se ha mirado sirve tal
cual; hay que pedirlo a [springmakers.net](https://www.springmakers.net/es/589-muelles-de-torsion),
que están en Barcelona.

### La manivela y el volante se hacen en el taller

**Ninguna manivela de catálogo está a la altura del objeto.** La mejor
mecánicamente ([Mädler 66730600](https://www.maedler.de/Article/66730600), 64 mm
de radio, 12,54 €) es zamak con recubrimiento de plástico negro. Manivela
comercial de latón con radio 60–120 mm **no existe**: lo que hay en latón son
manivelas de mueble de 20–30 mm.

Se hace: brazo de latón o inox cortado en el taller, **pomo de madera girando
sobre dos MR63ZZ** —el mismo rodamiento que ya se compra para los rodillos—.
Con 16 mN·m en ese eje, el brazo no trabaja.

El volante igual: una rodaja de Ø48 × 6 de un redondo de latón, mandrinada y
pulida. **Es la pieza donde más barato se compra aspecto**: un disco de latón
pulido girando a 60 rpm es, con la rueda dentada, lo que justifica el precio.

### El lápiz no va sobre guía deslizante

Con 3 mm de carrera, un casquillo —por bueno que sea— tiene holgura radial, y
esa holgura mueve la punta lateralmente al levantarse. Sobre un presupuesto de
error de centésimas, se lo come entero. Y un deslizamiento con arranque y
parada mil veces por minuto es donde aparece el *stick-slip*, que es
precisamente el ruido que no queremos.

**Paralelogramo articulado sobre dos MR63ZZ**, o **flexura** de dos láminas de
acero de muelle de 0,2–0,3 mm. Cero fricción, cero holgura, cero ruido. La
fuerza hacia abajo la da el peso del propio lápiz.

Y el instrumento: **portaminas de pinza de 2 mm** (Fixpencil, Staedtler Mars
technico) y no de 0,5. El de 2 mm no necesita avanzar la mina, tiene cuerpo
metálico cilíndrico que entra directo en el anillo de apriete, y la mina no se
rompe.

---

## 5. Proveedores

| Proveedor | Qué | Dónde | Nota |
| --- | --- | --- | --- |
| [Polygom](https://www.polygom.es/) | POM-C en plancha **y fresado CNC** | Barcelona, C/ Caracas 11 | El proveedor clave. Plancha 1×1 m de 5 mm: 70,15 € |
| [Esteba](https://www.esteba.com/es/nogal-americano) | Nogal americano, contrachapado de abedul | Delegaciones en Catalunya | Precios netos publicados |
| [123rodamiento](https://www.123rodamiento.es/) | Rodamientos, con escalado a 50+ | España | El más barato con tarifa pública |
| [Motedis ES](https://www.motedis.es/) | Eje rectificado h6, poleas | España | 3,90 €/m el Ø10 h6 |
| [esutil.es](https://www.esutil.es/) | Pasadores DIN 6325 | España, 48-72 h | Venta por unidad, envío gratis |
| [Ferretería Campollano](https://www.ferreteriacampollano.com/) | Tornillería inox A2 | Albacete, 24-48 h | Cajas de 100 a ~3,80 € |
| [Mädler](https://www.maedler.de/) | Engranajes, anillos de apriete | Alemania | Único con Z60 de latón m1 y precio público |
| [springmakers.net](https://www.springmakers.net/) | Muelles a medida | Barcelona | Filtro por constante K |
| [RS España](https://es.rs-online.com/) | Separadores, varilla, igus | España | |
| [Woodna](https://woodna.es/) | Nogal cepillado y alistonado | Galicia, envío nacional | Tabla de 2 m: 13 bases a 3,46 € |

---

## 6. Lo que falta por cerrar

Ninguno de estos es un dato que se pueda inventar. **Son llamadas de
teléfono.** Están por orden de lo que mueven en el precio.

1. **Cerrar el precio del bloque de levas.** Es la única partida que se paga
   en cada pedido y la única sin presupuesto: los 35 € son previsión
   nuestra. A Polygom (696 052 254, info@polygom.es) y a dos más para
   comparar: Baño-Lid (93 721 44 29), Talleres Torrecillas (93 424 50 48),
   Comecanic (93 118 44 86), CIM UPC (93 401 71 71). Enviar el DXF de una
   leva y pedir cinco cosas: **precio cerrado por bloque de tres**, que
   salgan de **un solo amarre**, mínimo de facturación, si garantizan
   ±0,05 mm en el perfil y H7 en el Ø10, y plazo de entrega. El plazo
   importa tanto como el precio: es lo que el cliente espera.
2. **Tolerancia de espesor de la plancha de POM-C de 5 mm** — no está en
   ninguna ficha, y es lo que decide si la pila de tres levas se come el
   hueco. A Polygom, en la misma llamada.
3. **Confirmar la valona del igus GFM-081012-125**: ¿Ø12 o Ø12,5? Si es Ø12,
   el hueco al poste vuelve a 11,0 mm en vez de 9,5. A igus España.
4. **Portes e IVA de Mädler a España.** Por debajo de 75 € cobran 15 € de
   gestión, y los portes fuera de Alemania no están publicados. Sobre 25 €
   de engranajes por máquina, eso decide si compensa pedir de 50 en 50.
5. **Valorar la correa GT2 frente a los engranajes.** Un juego de poleas
   20T/60T más correa ronda los 10 € contra los 25,64 € de los engranajes de
   latón. Cambia el aspecto del producto, así que es una decisión de diseño
   y no solo de precio: la rueda de latón es de las cosas que se ven.
6. **IVA y portes a España del eje inox Ø8 h6 de Dold**, y precio de corte
   en serie. Es el único precio de la lista sin verificar.
7. **Medir con pie de rey el cuerpo del portaminas** antes de dimensionar el
   anillo de apriete. El catálogo da 10 mm nominales de la caja, que no es
   la cota de la pieza.
8. **Precio del redondo de latón Ø50** a Servei Estació (933 932 410), que
   está en Barcelona y se puede ir con el plano. El único precio leído es de
   Randrade, 283,23 €/m.
9. **Confirmar que "B H7" en la ficha de Mädler es el agujero** antes de
   diseñar el eje contra ese dato.

Y dos cosas que no son llamadas:

- **Comprar un Lanky Doodler.** Son 28 € y es la referencia de banco más
  barata que existe para E4 — un autómata de levas que escribe, funcionando,
  encima de la mesa.
- **Cortar una leva de prueba en la máquina que se esté valorando** y
  medirla. Ninguna especificación de fabricante dice si llega a ±0,05 mm en
  el canto; dicen la precisión del movimiento, que es otra cosa.
