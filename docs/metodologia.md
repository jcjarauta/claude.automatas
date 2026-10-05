# Metodología de diseño y fabricación

Cómo se diseña un escribiente, cómo se prueba antes de gastar dinero, y qué
sale por la puerta con cada pedido.

- El **expediente** (`docs/expediente.md`) es la puerta de entrada: qué es el
  producto, en qué punto está y qué falta.
- La **ficha de producto** (`docs/ficha-producto.md`) dice *qué* se compra y
  cuánto cuesta.
- Este documento dice *cómo* se diseña, se prueba y se documenta.
- Los **contratos** (`docs/contratos.md`) dicen qué cotas no se tocan.

---

## 1. Qué manda sobre qué

Hay una intuición razonable y equivocada: que el bloque de levas es la pieza
que manda y el resto del conjunto se adapta a su tamaño. Conviene deshacerla
antes de montar ningún sistema encima, porque de ella depende que la
plataforma se pueda fabricar a stock o no.

**La cadena causal real va al revés:**

```
caja de escritura (80 × 30 mm)   <- se elige. Es LA decisión de producto
        |
        v
barrido del brazo de cinco barras
        |
        v  ÷ relación 6:1
barrido del seguidor
        |
        v  + radio base 55 mm
radio máximo de la leva  ------> hueco al poste  ------> ¿cabe esta frase?
        ^
        |
radio base y brazo del seguidor  <- se eligen por ángulo de presión,
                                    curvatura y rodillo disponible
```

Y de ahí sale la cota de conjunto:

```
posición de los postes = hypot(radio_base, brazo_seguidor) = hypot(55, 45) = 71,1 mm
```

**Los postes no dependen de la frase.** Dependen del radio base y del brazo
del seguidor, que son decisiones de diseño. Lo único que cambia con la frase
es el **radio máximo** de la leva, es decir cuánto ondula: entre 53,3 y
54,5 mm en las frases probadas. El hueco al poste se mueve entre 9,1 y
10,3 mm, y por debajo de 3 mm el compilador avisa.

Es decir: **la plataforma es fija y el cartucho varía dentro de una
envolvente.** Eso no es una limitación, es el modelo de negocio. Si la
plataforma tuviera que adaptarse a cada cliente no se podría fabricar a
stock, y el escribiente pasaría de ser un producto a ser un encargo.

### Paramétrico ¿para qué, entonces?

Para **generaciones de producto**, no para clientes.

El diseño tiene que ser paramétrico para que el día que E4 diga «sube el
radio base a 60» o «la relación tiene que ser 5:1», todo lo demás siga solo:
postes, bastidor, planos, dossier. Eso pasará, y pasará varias veces.

Y para una **línea de tallas**, que es la respuesta elegante a «¿y si la
frase no cabe?»:

| Talla | Caja de escritura | Para qué |
| --- | --- | --- |
| **M** | 80 × 30 mm | La actual. Una palabra o dos, una firma |
| **L** | ~120 × 40 mm | Una frase corta. Levas mayores, bastidor mayor |
| **S** | ~50 × 20 mm | Una inicial, un monograma. Objeto pequeño y barato |

Tres plataformas congeladas, un solo motor paramétrico, y el compilador
eligiendo la menor en la que la frase entra. El cliente no configura una
máquina: elige un tamaño, como quien elige la talla de un marco.

### El hallazgo que hay que arreglar antes de dibujar nada

**Hoy el calaje del brazo depende de la frase, y no debería.**

El calaje es el ángulo al que cada brazo se cala sobre el eje de su
seguidor. `compile/escribiente.py` lo calcula como la media de los ángulos
del brazo a lo largo del ciclo, que es lo que minimiza el barrido de la leva.
Pero esa media depende de por dónde escriba el cliente:

| Frase | Calaje izq. | Calaje der. |
| --- | --- | --- |
| «hola» | -5,41° | -174,34° |
| Un trazo vertical | -3,81° | -176,18° |
| Barrido de toda la caja | -2,10° | -177,90° |

Un rango de **3,3°**. Sobre un brazo proximal de 90 mm eso son 5 mm de
desplazamiento del trazo si el brazo se monta al calaje de otra frase.

La consecuencia es que **el brazo deja de ser pieza de stock**: no se puede
premontar la plataforma y enchufar el cartucho, porque el brazo hay que
calarlo para ese pedido. Eso rompe justo lo que el modelo de negocio
necesita.

**La solución es barata.** Fijar el calaje a una constante de la máquina —el
centro de la caja de escritura— en vez de a la media de la frase. La leva
absorbe la diferencia: crece, como mucho, **0,22 mm de radio**, y el hueco al
poste baja de 9,5 a unos 9,3 mm. A cambio, el brazo se cala una vez, en el
diseño, y se monta igual en todas las máquinas.

Es una cota de contrato y hay que congelarla. **Debería hacerse antes de
dibujar la plataforma**, porque si no se dibuja sobre una referencia que se
mueve.

### Y una consecuencia que reordena el presupuesto de error

El varillaje amplifica. Un error radial en el canto de la leva llega a la
punta del lápiz multiplicado por

```
relación × brazo proximal / brazo del seguidor = 6 × 90 / 45 = 12×
```

| Error de corte en el canto | Lo que se ve en el papel |
| --- | --- |
| 0,05 mm — la tolerancia que pedimos al taller | **0,60 mm** |
| 0,10 mm | 1,20 mm |
| 0,30 mm — a mano, con cuidado | 3,60 mm |
| 0,50 mm — a mano, primera vez | 6,00 mm |

**El error de trazo simulado era 0,108 mm y la tolerancia de fabricación
permite 0,60.** (Desde el 2026-10-04 se mide contra la línea escrita y es
de 3 µm: el argumento se refuerza.) O sea que el modelo es seis veces más fino que la pieza: la
precisión de la máquina no la decide el compilador, la decide el taller que
corta. Dejar de perseguir décimas en el modelo y empezar a perseguirlas en la
tolerancia del canto es, probablemente, el cambio de foco más rentable que
hay ahora mismo.

`core/tolerance.py` implementa C4 —la cadena de tolerancias, con la
corrección por ángulo de presión que aquí se ha omitido— y **no está
enchufado a nada**. Enchufarlo al compilador para que cada pedido salga con
su presupuesto de error es trabajo de un rato y convierte los 0,60 mm en un
número defendible en vez de una estimación de servilleta.

---

## 2. El sistema de diseño

Cuatro fuentes de verdad, y **una sola dirección de flujo**. La regla es que
ningún número se teclea dos veces.

```
        docs/contratos.json            <- LOS PARÁMETROS. Aquí y en ningún otro sitio
       /         |          \
      /          |           \
 Python      Onshape      docs/piezas/*.json
compilador   Variable       fichas de piezas
             Studio         comerciales
      |          |                |
      v          v                v
  cartucho   plataforma      envolventes
 (generado)  (FeatureScript)  (cotas de interfaz)
      \          |                /
       \         |               /
        v        v              v
         conjunto en Onshape
                 |
                 v
        dossier + plantillas + DXF
```

### 2a. Los parámetros, que hoy son prosa y deberían ser dato

`docs/contratos.md` está escrito para leerlo, y eso está bien. Pero los
números que contiene —Ø10 h7, pasador a 18 mm, postes a 71,1 mm, pila de
19 mm— los necesita el compilador en Python **y** los necesita Onshape, y hoy
se copian a mano en los dos sitios. Copiar a mano es exactamente cómo la
valona del casquillo acabó siendo Ø12 en tres documentos cuando el fabricante
dice Ø15.

Propuesta: **`docs/contratos.json`**, validado contra un esquema como el
resto del catálogo, con `docs/contratos.md` generado a partir de él o
citándolo. Y un `scripts/exportar_variables.py` que escupa la tabla de
variables de Onshape. Se pega una vez en el **Variable Studio** y todas las
Part Studios de la plataforma la referencian.

Cuando un contrato cambia: se toca el JSON, se regenera, se pega. Un sitio,
una dirección.

### 2b. Las piezas comerciales: la ficha manda, el STEP decora

La regla 6 del repositorio dice que ningún módulo entra sin ficha. Las piezas
comerciales son el tercer tipo de módulo y todavía no la tienen.

Una ficha por referencia en `docs/piezas/`, con **las cotas de interfaz**:
las que otra pieza toca. Del casquillo igus interesan el agujero, el exterior,
el diámetro de valona y su espesor; no interesa el chaflán. Del engranaje
interesan módulo, dientes, ancho, agujero y diámetro exterior.

Y con su **fuente**: proveedor, referencia, URL y fecha, igual que los
precios.

El STEP del fabricante se importa **después**, y solo para dos cosas: que el
render se vea bien y comprobar que nada choca. **No es la fuente de la cota.**
Si el STEP y la ficha discrepan, es un bug que hay que investigar, no una cota
que se acepta. Más adelante eso puede ser un test: importar el STEP, medir su
caja envolvente y su agujero, y comprobar que coinciden con la ficha. Así un
proveedor que cambia una pieza en silencio se caza solo.

De dónde salen los archivos, por si sirve: igus y Mädler publican CAD por
referencia; tornillería DIN y pasadores están en la biblioteca de contenido
estándar de Onshape; el 6800 lo publica SKF; y el eje, los postes, los
separadores y el MR63ZZ son cilindros que se dibujan antes de encontrarlos.
El portaminas hay que medirlo y dibujarlo, y de todos modos había que medirlo.

### 2c. El reparto con Onshape, que ya estaba decidido y ahora se completa

| | Quién lo hace | Cómo llega |
| --- | --- | --- |
| **Cartucho** | Lo genera el compilador | DXF y STEP, se arrastra el archivo |
| **Plataforma** | FeatureScript a mano, una vez | Se escribe dentro de Onshape |
| **Comercial** | Ficha + STEP del fabricante | Import o contenido estándar |
| **Parámetros** | `docs/contratos.json` | Variable Studio, generado |

El camino por pedido —que es el que se repite cientos de veces— no toca la
API de Onshape nunca. Solo la toca el desarrollo de la plataforma, que ocurre
unas pocas veces al año.

**Configurations de Onshape** para las tallas S/M/L: una sola plataforma
paramétrica con tres configuraciones congeladas, en vez de tres documentos
que se desincronizan.

### 2d. El bucle de una pieza: generador · acotado · comparador

El reparto de arriba dice **quién** hace cada cosa. Esto dice **en qué orden**,
y es lo que convierte dibujar una pieza en un procedimiento en vez de en una
conversación.

Nace de un fallo concreto. Para el `brazo_proximal` el camino fue: una tabla
de variables, una hoja de bocetos, teclear ocho cotas en Onshape y comprobarlo
a ojo. La pieza salió bien, pero la comprobación a ojo **dio un diagnóstico
falso** —tres defectos que no existían— y costó más que el dibujo. Lo que
faltaba no era cuidado, era un paso mecánico al final.

**Una pieza cada vez.** No se abre la siguiente hasta que la anterior ha
pasado el paso 5. Ir a dos a la vez ahorra una hora y cuesta la tarde en que
aparece un número que ya se había copiado en otro sitio.

El bucle, por pieza:

| | Quién | Qué sale |
| --- | --- | --- |
| 1. **Generar** | el compilador | cuatro cosas, siempre las cuatro: `pieza.dxf` en su datum, la **tabla** de cotas y variables, el **boceto** con vistas y explicación, y **qué CSV hay que reimportar** |
| 2. **Dibujar** | la persona, en Onshape | importa el DXF, ancla con dos coincidentes, acota con los `#cota.…` de la tabla |
| 3. **Comprobar** | la persona | que Onshape diga **totalmente definida** |
| 4. **Devolver** | la persona | exporta el croquis a DXF y lo pasa |
| 5. **Comparar** | `scripts/comparar_dxf.py` | lo cruza contra el contrato y dice qué falta, qué sobra y dónde está puesta |
| 6. **Extruir y volver a pasar** | la persona · el mismo script | exporta el sólido a STEP y lo pasa otra vez: es lo único que comprueba el **espesor** |

Si el paso 5 falla, se corrige y se vuelve al 2. Si hace falta tocar una cota,
se toca el **contrato** —nunca el croquis a mano— y se regenera.

El paso 6 no sustituye al 5, va detrás: el croquis se comprueba **antes** de
extruir, que es cuando arreglarlo es gratis. Lo que añade el STEP es el
espesor, que no viaja en un contorno; un perfil correcto extruido a lo que el
CAD tuviera por defecto es una pieza que se ve bien y no entra en la pila.

Los cuatro artefactos del paso 1 no son opcionales y no se reparten: el DXF da
la forma, la tabla da lo que se teclea, el boceto da el porqué y las vistas, y
`REIMPORTAR.md` dice qué hay que volver a meter en el Variable Studio. Faltando
el boceto se dibuja sin entender la pieza; faltando la tabla se teclean números
leídos del dibujo, que es de donde vienen los errores que este documento existe
para evitar.

#### Una cota entra con su pieza, no suelta

El bucle de arriba es **por pieza**, y por eso tiene un agujero: se puede
añadir una cota al contrato sin que haya ninguna pieza abierta, y entonces
nada obliga a los cuatro artefactos. Pasó con las del bastidor: entraron al
contrato y salieron por CSV sin tabla y sin boceto, que es exactamente lo que
este documento dice que no se hace.

La regla: **una cota se añade dentro del bucle de la pieza que la usa.** Si la
pieza todavía no se puede dibujar, la cota puede entrar igual —el contrato es
el sitio donde viven los números— pero se entrega **diciendo a qué pieza
pertenece y por qué su bucle no se ha abierto**, y no se manda el CSV como si
fuera un paso terminado.

Y antes de abrir el bucle de una pieza hay que poder contestar a una pregunta:
**¿es una pieza?** El «bastidor» no lo era: el despiece dice «bastidor y
soportes», en plural, y el eje del reductor cae a 28 mm del árbol, dentro de
una leva de radio base 55. O sea que no está en el plano de las levas, y el
bastidor es **varias planchas en varios planos** que nadie ha repartido. Abrir
su bucle antes de ese reparto habría dado una pieza con la mitad de los
agujeros, que es el error del sector repetido.

#### Qué CSV hay que reimportar

Lo escribe `scripts/csv_pendientes.py` en `REIMPORTAR.md`, dentro del paquete.
Compara el paquete recién generado contra `docs/importado.json`, que guarda lo
que está **ahora mismo** en Onshape, y dice fila a fila qué entra, qué sale y
qué cambia de valor. Después de importar se marca con
`scripts/marcar_importado.py`.

**Decir «reimporta los cinco» por si acaso no es prudente, es caro.** Un mapa
del Variable Studio no se actualiza: se borra y se vuelve a crear, y mientras
tanto todo lo que lo referencia se pone en rojo. Normalmente ha cambiado uno.

Y cuando una cota **se va** —porque se renombró, como `brazo_ancho` o
`amplificador_sector_agujero`— el informe lo dice aparte, porque reimportar
encima no la borra: la clave vieja se queda en el mapa hasta que se borre la
tabla entera. No rompe nada mientras nadie la referencie, pero conviene saberlo
antes de buscar por qué hay una variable que ya no existe en el contrato.

Se guarda el **contenido** y no solo un hash: un hash dice que algo cambió y no
qué, y reconstruir eso a mano es justo el trabajo que esto quita.

El DXF entra como **andamio, no como vínculo**. Trae la forma resuelta —la
tangente exterior entre dos círculos desiguales, el agujero en D— que es lo
caro de construir a mano y donde están los errores. El vínculo con el contrato
lo sigue poniendo la persona al acotar, y por eso la pieza sigue siendo
paramétrica. **Acotar sobre geometría que ya está bien es, además, la propia
comprobación**: se escribe `#cota.brazo_proximal` y si el croquis no se mueve,
coincidía.

#### El datum, que es lo único que el archivo puede aportar al anclaje

Un croquis importado llega con la forma y **sin una sola restricción**: exacto
y suelto, que es el peor estado porque se ve bien y se mueve en cuanto alguien
lo roza. Y las cotas de la pieza no lo arreglan: una barra acotada de 90 sigue
pudiendo estar en cualquier punto del plano y a cualquier ángulo. Son tres
grados de libertad que ninguna cota del contrato menciona.

Ningún DXF lleva restricciones. Pero sí lleva **el sitio**, y con el sitio bien
elegido el anclaje son dos clics:

1. El **rasgo datum** —un agujero, siempre— se emite en el origen.
2. El centro siguiente se emite sobre **+X**.
3. En Onshape: coincidente(centro datum, origen) y coincidente(centro
   siguiente, eje X). Fuera los tres grados.

El datum es un agujero y no el centro de la pieza porque un agujero **ya está
dibujado y se engancha solo**; un punto medio hay que construirlo, y lo que hay
que construir se olvida. Cada pieza declara el suyo en `FICHAS`, y el
comparador informa de si el archivo lo respeta.

**La pieza se dibuja en su propio marco, no en el de la máquina.** Tentador
sería emitir el brazo donde de verdad va —el contrato tiene la transformada:
`brazo_origen_x`, `brazo_origen_y`, `brazo_orientacion`— pero entonces se
dibuja girado −3,749°, que es miserable de acotar, y además el mismo brazo
ocupa **dos** posiciones distintas en la máquina. No hay una posición. El marco
de la máquina viaja como ángulos en el CSV y se aplica en el ensamblaje.

No hay tercer grado de libertad escondido en el volteo: la cara plana del
agujero está a `brazo_chaveta_angulo` = 0, así que la pieza espejada es la
misma. La propiedad que ahorra el brazo derecho del despiece ahorra también
una restricción.

#### Las piezas y lo que se teclea en cada una

**Esta tabla se genera**, con `scripts/listado_piezas.py --escribir`, desde
`emit.plataforma.LISTADO`. Escrita a mano envejecería en silencio, y lo que la
lee es alguien tecleando cotas en un CAD: una fila que dice 40 donde el
contrato dice 80 no se nota hasta que la pieza está cortada. Un test falla si
el markdown y el código se separan.

<!-- listado:inicio · generado por scripts/listado_piezas.py, no editar a mano -->

| Pieza | Forma | Cotas |
| --- | --- | --- |
| `brazo_proximal` ×2 | barra de dos cubos **desiguales** | entre centros `#cota.brazo_proximal` 90 · espesor `#cota.brazo_espesor` 3 · Ø eje `#cota.brazo_eje_diametro` 10 H7 · Ø perno `#cota.brazo_perno_diametro` 6 H7 · R del cubo del eje `#cota.brazo_cubo_diametro_radio` 9 · R del extremo `#cota.brazo_extremo_diametro_radio` 6 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 · girada `#angulo.brazo_chaveta_angulo` 0 · calaje del EJE `#angulo.calaje_izquierdo` -3,749 |
| `brazo_distal` ×2 | barra CURVA: codo y punta | entre centros `#cota.brazo_distal` 110 · espesor `#cota.brazo_espesor` 3 · Ø perno del codo `#cota.brazo_perno_diametro` 6 H7 · R del codo `#cota.brazo_extremo_diametro_radio` 6 · Ø tubo de la punta `#cota.punta_tubo_diametro` 13 H7 · R de la punta `#cota.distal_punta_diametro_radio` 9,5 · del codo al centro del arco `#cota.distal_curva_radio` 108,333 · centro del arco a, bajo +X `#angulo.distal_curva_centro_angulo_positivo` 59,49 · R canto de dentro `#cota.distal_curva_interior_radio` 102,333 · R canto de fuera `#cota.distal_curva_exterior_radio` 114,333 · flecha `#cota.distal_flecha` 15 |
| `palanca_lapiz` ×1 | barra de dos cubos **desiguales** | entre centros `#cota.brazo_palanca` 40 · espesor `#cota.brazo_espesor` 3 · Ø eje `#cota.balancin_eje_diametro` 4 H7 · Ø perno `#cota.brazo_perno_diametro` 6 H7 · R del cubo del eje `#cota.balancin_cubo_diametro_radio` 5 · R del extremo `#cota.brazo_extremo_diametro_radio` 6 · cara plana a `#cota.balancin_chaveta` 1,6 · cuerda `#cota.balancin_chaveta_cuerda` 2,4 · girada `#angulo.brazo_chaveta_angulo` 0 · calaje del EJE `#angulo.calaje_elevador` 2,149 |
| `mordaza` ×2 | bloque con un tornillo que aprieta y una ranura que cala | largo `#cota.mordaza_largo` 24 · del tornillo al borde `#cota.mordaza_voladizo` 5 · ancho `#cota.mordaza_ancho` 10 · espesor `#cota.mordaza_espesor` 6 · Ø aprieta la cinta `#cota.mordaza_tornillo_diametro` 3 M3 · Ø fija al sector `#cota.mordaza_fijacion_diametro` 4 M4 · entre los dos `#cota.mordaza_entre_tornillos` 10 · recorrido de la ranura `#cota.mordaza_recorrido` 6 · datum al centro cercano `#cota.mordaza_ranura_cerca` 7 · datum al centro lejano `#cota.mordaza_ranura_lejos` 13 · radio mínimo de la cinta `#cota.cinta_radio_minimo` 5 |
| `eje_pivote` ×2 | eje Ø10 h6 con una cara plana, cortado a medida | Ø `#cota.brazo_eje_diametro` 10 h6 · largo `#cota.eje_pivote_largo` 69,5 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 |
| `sector` ×2 | disco sin muesca, con los dos tornillos que lo calan al seguidor | Ø del canto `#cota.amplificador_sector_radio_mecanizado_diametro` 111,95 · espesor `#cota.amplificador_sector_espesor` 5 · Ø de paso `#cota.amplificador_sector_agujero_diametro` 16 · la cinta entra a `#angulo.amplificador_tangencia` 43,897 · centro al tornillo cercano `#cota.union_sector_seguidor_cerca` 22 · centro al tornillo lejano `#cota.union_sector_seguidor_lejos` 38 · Ø paso de los dos al seguidor `#cota.union_sector_seguidor_diametro` 3,2 · centro a la mordaza `#cota.sector_mordaza_al_centro` 51,063 · mordaza, canal izquierdo, por debajo de X `#angulo.sector_mordaza_angulo_izquierdo_positivo` 157,221 · mordaza, canal derecho `#angulo.sector_mordaza_angulo_derecho` 169,952 · Ø paso del M4 de la mordaza `#cota.sector_mordaza_diametro` 4,3 |
| `tambor` ×2 | cilindro liso con agujero, sin pestañas | Ø del canto `#cota.amplificador_tambor_radio_mecanizado_diametro` 13,95 · ancho `#cota.amplificador_tambor_ancho` 6 · Ø agujero `#cota.brazo_eje_diametro` 10 H7 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 · girada `#angulo.brazo_chaveta_angulo` 0 · abrazado `#angulo.amplificador_tambor_abrazado` 164,858 |
| `manivela` ×1 | barra de dos cubos, como los brazos | entre centros `#cota.manivela_entre_centros` 100 · espesor `#cota.brazo_espesor` 3 · Ø eje `#cota.brazo_eje_diametro` 10 H7 · Ø del pomo `#cota.brazo_perno_diametro` 6 H7 · R del cubo del eje `#cota.brazo_cubo_diametro_radio` 9 · R del extremo `#cota.brazo_extremo_diametro_radio` 6 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 · girada `#angulo.brazo_chaveta_angulo` 0 |
| `volante` ×1 | disco aligerado, en el eje de la manivela | Ø del disco `#cota.volante_diametro` 104 · espesor `#cota.volante_espesor` 6 · Ø del eje `#cota.brazo_eje_diametro` 10 H7 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 · Ø de cada aligeramiento `#cota.volante_aligeramiento_diametro` 24 · del eje a cada aligeramiento `#cota.volante_aligeramiento_al_centro` 30 · entre aligeramientos `#angulo.volante_aligeramiento_reparto` 60 · a cuánto se gira (no se dibuja) `#num.manivela_vueltas_por_minuto` 90 |
| `base` ×1 | tabla con los tres agujeros de los postes | ancho `#cota.base_ancho` 256 · fondo `#cota.base_fondo` 275 · espesor `#cota.base_espesor` 25 · Ø de cada poste `#cota.poste_eje_diametro` 8 H7 · entre postes `#cota.base_entre_postes` 123,085 · el tercero a `#angulo.base_postes_angulo` 60 · datum al borde izquierdo `#cota.base_poste_al_borde_izquierdo` 66,457 · datum al borde de atrás `#cota.base_poste_al_borde_trasero` 59,468 · fondo del agujero ciego `#cota.base_poste_empotrado` 15 |
| `balancin` ×1 | barra de dos cubos diminuta, de la misma chapa que los brazos | entre centros `#cota.balancin_entrada` 6,333 · espesor `#cota.balancin_espesor` 3 · Ø eje `#cota.balancin_eje_diametro` 4 H7 · Ø pasador `#cota.balancin_perno_diametro` 2 H7 · R del cubo del eje `#cota.balancin_cubo_diametro_radio` 5 · R del extremo `#cota.balancin_extremo_diametro_radio` 4 · cara plana a `#cota.balancin_chaveta` 1,6 · cuerda `#cota.balancin_chaveta_cuerda` 2,4 · girada `#angulo.balancin_chaveta_angulo` 90 |
| `platina_levas` ×3 | disco con los siete agujeros del mecanismo | Ø del disco `#cota.platina_diametro` 170 · espesor `#cota.platina_espesor` 9 · Ø del árbol `#cota.rodamiento_arbol_alojamiento_diametro` 19 H7 · Ø de cada poste `#cota.poste_eje_diametro` 8 h6 · del árbol a los postes `#cota.poste_radio_al_arbol` 71,063 · entre postes `#angulo.poste_reparto` 120 · Ø de cada pivote `#cota.brazo_eje_diametro` 10 · del árbol a los pivotes `#cota.platina_pivote_al_arbol` 68,213 · pivote izquierdo a, bajo +X `#angulo.platina_pivote_angulo_izquierdo_positivo` 58,407 · pivote derecho a `#angulo.platina_pivote_angulo_derecho` 178,407 · del árbol a la manivela `#cota.reductor_entre_ejes` 28 · eje de la manivela a, bajo +X `#angulo.platina_manivela_angulo_positivo` 90 · Ø de los dos M3 de los apoyos `#cota.apoyo_balancin_tornillo_diametro` 3,2 · del árbol al apoyo de popa `#cota.platina_apoyo_trasero_al_arbol` 44,216 · apoyo de popa a, bajo +X `#angulo.platina_apoyo_trasero_angulo_positivo` 154,475 · del árbol al apoyo de proa `#cota.platina_apoyo_delantero_al_arbol` 75,708 · apoyo de proa a, bajo +X `#angulo.platina_apoyo_delantero_angulo_positivo` 139,305 |
| `seguidor` ×3 | barra de dos cubos con seis agujeros en línea | al rodillo del elevador `#cota.brazo_seguidor` 45 · al rodillo del derecho `#cota.brazo_seguidor_derecho` 50 · al rodillo del izquierdo, el extremo `#cota.brazo_seguidor_izquierdo` 55 · espesor `#cota.seguidor_espesor` 5 · Ø alojamiento del casquillo `#cota.seguidor_pivote_diametro` 10 H7 · Ø del cubo `#cota.seguidor_cubo_diametro` 16 · Ø del extremo `#cota.seguidor_extremo_diametro` 11 · Ø paso del eje del rodillo `#cota.seguidor_rodillo_diametro` 3,2 · pivote al muelle `#cota.seguidor_muelle_radio` 12 · Ø anclaje del muelle `#cota.seguidor_muelle_diametro` 3 · pivote al tornillo cercano `#cota.union_sector_seguidor_cerca` 22 · pivote al tornillo lejano `#cota.union_sector_seguidor_lejos` 38 · Ø paso de los dos al sector `#cota.union_sector_seguidor_diametro` 3,2 · baja el rodillo, izquierdo `#cota.rodillo_descuelgue_1` 7 · derecho `#cota.rodillo_descuelgue_2` 14 · elevador `#cota.rodillo_descuelgue_3` 21 |
| `eje_manivela` ×1 | eje Ø10 h6 con una cara plana, como los de pivote | Ø `#cota.brazo_eje_diametro` 10 h6 · largo `#cota.eje_manivela_largo` 51 · cara plana a `#cota.brazo_chaveta` 4 · cuerda `#cota.brazo_chaveta_cuerda` 6 · girada `#angulo.brazo_chaveta_angulo` 0 |
| `casquillo_rueda` ×1 | casquillo: la rueda Z60 en el árbol | Ø exterior `#cota.casquillo_rueda_diametro` 15 p6 · Ø interior `#cota.eje_diametro` 10 H7 · largo `#cota.casquillo_rueda_largo` 4 |
| `eje_balancin` ×1 | eje Ø4 h6 con UNA cara plana | Ø `#cota.balancin_eje_diametro` 4 h6 · largo `#cota.balancin_eje_largo` 96,748 · cara plana a `#cota.balancin_chaveta` 1,6 · cuerda `#cota.balancin_chaveta_cuerda` 2,4 · girada `#angulo.brazo_chaveta_angulo` 0 |
| `apoyo_balancin` ×2 | bloque colgado del plato 2, con el agujero del eje del balancín | alto (sobre X) `#cota.apoyo_balancin_alto` 19 · ancho `#cota.apoyo_balancin_ancho` 10 · grueso `#cota.apoyo_balancin_fondo` 6 · Ø del eje `#cota.balancin_eje_diametro` 4 H7 · del eje al pie `#cota.apoyo_balancin_bajo_eje` 5 |
| `bieleta` ×1 | varilla de Ø2 doblada en sus dos extremos | Ø `#cota.bieleta_diametro` 2 h8 · largo antes de doblar `#cota.bieleta_largo_desarrollado` 83,575 · entre ejes `#cota.bieleta_entre_centros` 60,242 · pata hacia abajo `#cota.bieleta_pata_seguidor` 19,333 · pata hacia popa `#cota.bieleta_pata_balancin` 4 |
| `casquillo_bieleta` ×1 | casquillo en el agujero de Ø3,2 del seguidor 3 | Ø exterior `#cota.casquillo_bieleta_diametro` 3,2 p6 · Ø interior `#cota.bieleta_diametro` 2 H8 · largo `#cota.seguidor_espesor` 5 |
| `tirante` ×1 | varilla de Ø4 con un taladro transversal abajo | Ø `#cota.tirante_diametro` 4 · largo `#cota.tirante_largo` 113,5 PENDIENTE · taladro del ojo `#cota.tirante_ojo_diametro` 1,8 |
| `bulon_tirante` ×1 | bulón Ø6 con un taladro transversal | Ø `#cota.brazo_perno_diametro` 6 h7 · largo `#cota.bulon_tirante_largo` 9 |
| `perno_codo` ×2 | pasador Ø6 enrasado | Ø `#cota.brazo_perno_diametro` 6 m6 · largo `#cota.perno_codo_largo` 6,5 |
| `casquillo_punta` ×1 | casquillo entre los dos distales, en el tubo de la punta | Ø exterior `#cota.distal_punta_diametro` 19 · Ø interior `#cota.punta_tubo_diametro` 13 H8 · largo `#cota.casquillo_punta_largo` 4 |
| `mesa` ×1 | placa donde va la tarjeta | fondo (sobre X) `#cota.mesa_fondo` 90 · ancho `#cota.mesa_ancho` 120 · espesor `#cota.mesa_espesor` 4 · Ø de los dos M2 `#cota.mesa_tornillo_diametro` 2,2 · entre los dos M2 `#cota.mesa_tornillos_entre` 60 · del M2 al canto de atrás `#cota.mesa_tornillo_al_borde` 25 · planitud `#cota.mesa_planitud` 0,5 |
| `biela_mesa` ×4 | barra de dos cubos iguales | entre centros `#cota.mesa_biela` 40 · espesor `#cota.mesa_biela_espesor` 3 · Ø los dos `#cota.mesa_eje_diametro` 1,5 H8 · R los dos `#cota.mesa_biela_extremo_diametro_radio` 2,5 |
| `eje_mesa_movil` ×2 | varilla de Ø1,5 que cruza bajo la mesa | Ø `#cota.mesa_eje_diametro` 1,5 h8 · largo `#cota.mesa_eje_movil_largo` 142 |
| `eje_mesa_fijo` ×4 | varilla de Ø1,5, corta | Ø `#cota.mesa_eje_diametro` 1,5 h8 · largo `#cota.mesa_eje_fijo_largo` 7 |
| `soporte_mesa` ×4 | bloque sobre la base con el agujero de un eje fijo | alto (sobre X) `#cota.soporte_mesa_alto` 8,5 · fondo `#cota.soporte_mesa_fondo` 8 · grueso `#cota.soporte_mesa_ancho` 4 · Ø del eje `#cota.mesa_eje_diametro` 1,5 H8 · del eje a la base `#cota.mesa_bisagra_z` 6 |
| `orejeta_mesa` ×2 | bloque bajo la mesa, con el agujero de un eje móvil | alto (sobre X) `#cota.orejeta_mesa_alto` 4,5 · fondo `#cota.orejeta_mesa_fondo` 6 · largo `#cota.orejeta_mesa_ancho` 40 · Ø del eje `#cota.mesa_eje_diametro` 1,5 H8 · del eje al pie `#cota.mesa_biela_extremo_diametro_radio` 2,5 |
| `tubo_punta` ×1 | tubo: el perno hueco de la punta del cinco barras | Ø exterior `#cota.punta_tubo_diametro` 13 h7 · Ø interior `#cota.punta_tubo_interior_diametro` 10,6 · largo `#cota.punta_tubo_largo` 16 |
| `brazo_horquilla` ×1 | brazo del portalápiz: del tubo de la punta al poste | entre centros `#cota.horquilla_largo` 35 · espesor `#cota.horquilla_espesor` 3 · R los dos `#cota.horquilla_cubo_diametro_radio` 8 · Ø del tubo `#cota.punta_tubo_diametro` 13 |
| `poste_horquilla` ×1 | poste donde se aprietan las láminas | alto (sobre X) `#cota.poste_horquilla_alto` 34 · ancho `#cota.horquilla_ancho` 12 · grueso `#cota.poste_horquilla_fondo` 4 · Ø de los dos M2 `#cota.flexura_tornillo_diametro` 2,2 · entre los dos M2 `#cota.flexura_separacion` 20 · del M2 al pie `#cota.poste_horquilla_tornillo_al_pie` 9,5 |
| `pinza` ×1 | bloque cuadrado apretado al portaminas | lado `#cota.pinza_ancho` 16 · alto `#cota.pinza_largo` 28 · Ø del portaminas `#cota.pinza_agujero_diametro` 8,1 ajustar · del eje a cada cara `#cota.pinza_al_borde` 8 |
| `lamina_flexura` ×2 | lámina de 0,15 con una pestaña doblada en cada punta | largo antes de doblar `#cota.lamina_desarrollo` 35 · ancho `#cota.flexura_ancho` 12 · espesor `#cota.flexura_espesor` 0,15 · Ø de los dos M2 `#cota.flexura_tornillo_diametro` 2,2 · entre los dos M2 `#cota.lamina_entre_tornillos` 30 · del M2 a la punta `#cota.lamina_tornillo_al_borde` 2,5 |
| `eje_cartucho` ×1 | eje con su valona: tetón abajo, pasador en la valona, ranura arriba | Ø de la valona `#cota.cubo_diametro` 24 · Ø del eje `#cota.eje_diametro` 10 h6 · Ø del pasador `#cota.pasador_diametro` 3 m6 (apretado) · del eje al pasador `#cota.pasador_radio` 18 · largo `#cota.cartucho_eje_largo` 27 · alto de la valona `#cota.cubo_espesor` 5 · Ø del tetón `#cota.cartucho_teton_diametro` 5 g6 · largo del tetón `#cota.cartucho_teton_largo` 4 · ancho de la ranura `#cota.garra_ranura_ancho` 3 · fondo de la ranura `#cota.garra_ranura_profundidad` 3 · ranura fuera del centro `#cota.garra_ranura_desplazamiento` 1,5 · ranura respecto del pasador `#angulo.cartucho_salida_angulo` 60 |
| `separador` ×2 | disco de 2 con el agujero del eje y el del pasador | Ø exterior `#cota.separador_diametro` 44 · espesor `#cota.separador_espesor` 2 · Ø del eje `#cota.eje_diametro` 10 H8 · Ø del pasador `#cota.pasador_diametro` 3 H8 · del eje al pasador `#cota.pasador_radio` 18 |
| `munon` ×1 | eje Ø10 h6 con una horquilla en U arriba | Ø `#cota.eje_diametro` 10 h6 · largo `#cota.munon_largo` 16 · boca de la U `#cota.munon_horquilla_ancho` 5,1 H9 · fondo de la U `#cota.munon_horquilla_alto` 4 |
| `eje_motriz` ×1 | eje Ø10 h6 con el taladro transversal del pasador abajo | Ø `#cota.eje_diametro` 10 h6 · largo `#cota.eje_motriz_largo` 61 · taladro del pasador `#cota.garra_pasador_diametro` 2 |
| `collar` ×9 | collar con un prisionero M3 radial | Ø exterior `#cota.collar_seguidor_diametro` 11,5 · Ø interior `#cota.poste_eje_diametro` 8 F7 · largo `#cota.collar_seguidor_largo` 7 |
| `placa_tope` ×3 | brazo corto con el poste, la pata del muelle y el pasador de tope en línea | del poste al pasador `#cota.tope_brazo` 20 · espesor `#cota.tope_placa_espesor` 2 · Ø del cubo `#cota.tope_cubo_diametro` 12 · Ø del extremo `#cota.tope_extremo_diametro` 7 · Ø del poste `#cota.poste_eje_diametro` 8 F7 · del poste a la pata fija `#cota.muelle_pata_radio` 14 · Ø de la pata fija `#cota.muelle_pata_diametro` 1 · Ø del pasador de tope `#cota.tope_pasador_diametro` 3 m6 · girada respecto del seguidor `#angulo.tope_angulo` 29,754 |
| `calzo_sector` ×2 | barra con el paso de la valona y los dos tornillos al sector | al tornillo lejano `#cota.union_sector_seguidor_lejos` 38 · al tornillo cercano `#cota.union_sector_seguidor_cerca` 22 · espesor `#cota.calzo_sector_espesor` 3 · Ø del cubo `#cota.calzo_sector_cubo_diametro` 22 · Ø del extremo `#cota.calzo_sector_extremo_diametro` 9 · Ø de paso de la valona `#cota.amplificador_sector_agujero_diametro` 16 · Ø de los tornillos `#cota.union_sector_seguidor_diametro` 3,2 |
| `tubo_separador` ×6 | tubo cortado a dos largos | Ø exterior `#cota.tubo_separador_diametro` 12 · Ø interior `#cota.tubo_separador_interior_diametro` 9 · base a plato 1 `#cota.tubo_separador_largo_1` 60 · plato 2 a plato 3 `#cota.tubo_separador_largo_2` 20 |
| `casquillo_rodillo` ×3 | tubo de Ø4 cortado a tres largos | Ø exterior `#cota.casquillo_rodillo_diametro` 4 · Ø interior `#cota.casquillo_rodillo_interior_diametro` 3,1 · izquierdo `#cota.casquillo_rodillo_largo_1` 3,25 · derecho `#cota.casquillo_rodillo_largo_2` 10,25 · elevador `#cota.casquillo_rodillo_largo_3` 17,25 |
| `garra` ×1 | manguito con una lengüeta descentrada y dos ranuras verticales | Ø exterior `#cota.garra_diametro` 14 · Ø interior `#cota.eje_diametro` 10 F7, corre · alto `#cota.garra_alto` 8 · lengüeta, 0,1 menos `#cota.garra_ranura_ancho` 3 · fuera del centro `#cota.garra_ranura_desplazamiento` 1,5 · carrera `#cota.garra_carrera` 5 |

<!-- listado:fin -->

Del `brazo_proximal` se corta **una** y valen las dos: los calajes suman -180°,
así que el derecho es el izquierdo volteado.

Tres cosas que la tabla no dice sola:

**Los `_radio` son gemelos**, no cotas del contrato. El contrato guarda
`brazo_cubo_diametro`; el exportador saca su mitad porque el contorno de una
barra son dos arcos y ahí el CAD pide radio. Meter el diámetro en ese campo da
un cubo del doble, sin un solo aviso.

**El calaje no se acota en la pieza.** Va en la fila porque hay que saberlo,
pero con la cara plana a 0° el brazo es simétrico respecto de su propio eje y
no tiene orientación: el ángulo se mecaniza en la cara plana del **eje**, que
es otra pieza y aún no tiene plano.

**Las que no están en el perfil hay que teclearlas igual.** El espesor, el
ancho del tambor, el abrazado, el calaje: no son geometría del croquis, así
que el DXF no las trae. El archivo no sustituye a la tabla de variables, la
adelgaza.

#### Qué lleva el boceto, y por qué dos vistas y no una

El boceto lo genera `scripts/dibujar_pieza.py` desde el mismo perfil que
escribe el DXF. No se escribe a mano: había tres hojas escritas así y con la
cuarta ya empezaban a divergir, y un contorno dibujado que no es el que se
corta es la forma más cara de descubrir una cota.

Lleva, por pieza:

| | |
| --- | --- |
| **Planta** | El contorno, el DATUM marcado, y **todas** las cotas que la ficha declara: radios, distancias entre centros, recorrido de ranura, cara plana y segmentos |
| **Segunda vista** | La tercera dimensión: **sección** si es plancha, **alzado** si es barra |
| **El porqué** | Dos frases de por qué la pieza es así |
| **La tabla** | Lo que se teclea, con el valor y lo que marca lo que no está en el DXF |

**Un perfil 2D no es una pieza: le falta por dónde se extruye.** Por eso cada
pieza declara su sólido en `LISTADO` —`("plancha", "mordaza_espesor")`,
`("barra", "eje_pivote_largo")`— y de ahí sale la segunda vista. Sin ella el
espesor vive solo en la tabla, que es donde menos se mira, y un espesor que no
se ve en el dibujo se extruye al que tenga puesto el CAD por defecto.

**Y se acotan todas, no las principales.** Acotar solo algunas fue el agujero
de la primera versión: lo que no aparece dibujado se teclea leyéndolo de la
tabla sin saber a qué rasgo corresponde, y entonces la hoja no sirve para
dibujar, solo para recordar.

Las cotas que dibuja salen de `FICHAS`, que es lo que el comparador va a mirar
después. Esa procedencia es la que hace útil la hoja: **enseña exactamente lo
que se va a verificar**, así que una cota que nadie vigile tampoco aparece, y
se ve que falta antes de cortar nada.

#### Qué comprueba el comparador y qué no

Comprueba **la forma**: cada radio con su cota y su recuento, la distancia
entre centros, la cuerda de la cara plana, y que las tangentes sean tangentes
de verdad —perpendicularidad impuesta, no mirada: es el error que este repo ya
cometió dos veces con la cinta del cabestrante—. Un rasgo que falta y uno que
sobra son fallos distintos y los dos se ven.

Lo hace contra la **ficha de la pieza**, no contra el contrato entero. Buscar
«alguna cota que valga 6» no comprueba nada: con ochenta cotas, cualquier
número redondo encuentra una. La primera versión daba por bueno un radio de 6
citando el ancho del tambor del cabestrante, que no pinta nada en un brazo.

**No comprueba las restricciones.** No viajan en un DXF. Un croquis exacto y
suelto pasa el comparador entero, y por eso el paso 3 es de la persona y el
informe lo recuerda cada vez.

**No comprueba el espesor, el material, la tolerancia ni el calaje**, que no
son geometría del perfil. Esos siguen en el CSV y en la hoja: el DXF no
sustituye a la tabla de variables, la adelgaza.

---

## 3. Cómo se prueba antes de pedir las piezas

Aquí está la pregunta del corte en madera, y la respuesta es que **sí, pero
hacen falta dos cartuchos distintos y prueban cosas distintas.** La
infraestructura ya existe: `emit/template.py` emite plantillas 1:1 con cuadro
de calibración, que es exactamente para esto. El cuadro importa más que
nunca: un 1 % de escalado de impresora sobre una leva de Ø108 es **1 mm**, y
a 12× son 12 mm en el papel.

### 3a. El cartucho mudo — ¿esto se monta y se mueve?

Tres levas con el perfil real, recortadas a mano sobre la plantilla pegada.

**Material: HDF o DM de 5 mm, no contrachapado.** El contrachapado tiene
huecos y capas de dureza distinta, y el rodillo rodaría sobre un canto
irregular. El DM es uniforme, no tiene veta y se lija a la línea. El canto es
blando y se desgastará, pero para unos cientos de ciclos sobra.

Precisión realista: **±0,3 mm** con sierra de marquetería y lijadora de
disco, pegando la plantilla con adhesivo en espray y lijando hasta la línea.
±0,5 mm la primera vez.

**Eso son 3,6 a 6 mm en la punta.** Así que este cartucho **no prueba la
fidelidad del trazo** y no hay que pedirle que lo haga. Lo que sí prueba, y
es mucho:

- Que el conjunto **se monta**: pila, huecos, postes, interferencias.
- Que el **varillaje no se atasca** ni cambia de rama. Es la trampa conocida
  de la cinemática inversa, y en el papel no se ve.
- Que el **pasador de índice hace su trabajo**: que el cartucho solo entra de
  una manera.
- Que el **levantamiento del lápiz** sube y baja limpio, sin arrastrar.
- Que el **par es el que dijimos**. Se mide con un dinamómetro de pesar
  maletas en la manivela, y contrasta C6 con la realidad.
- Que **escribe algo reconocible**. Con 4 mm de error será un garabato
  tembloroso, pero se verá si el reparto de θ y el canal de levantamiento
  están bien. Un fallo de programa se ve a 4 mm; uno de fidelidad, no.

**Si en el taller hay una impresora 3D, imprime las levas en vez de
recortarlas.** Una FDM decente da ±0,1 a 0,2 mm, es repetible, no gasta
habilidad y sale del STEP que el compilador ya emite. Es mejor mula que la
madera y es gratis.

### 3b. El cartucho de calibración — el que de verdad mide

Este es el que propongo con más ganas, porque ataca justo lo que E4 tiene que
medir y hoy no está modelado: **el juego**.

Tres levas que no son levas, sino **discos excéntricos**: círculos con el
agujero del eje descentrado una excentricidad conocida.

Un círculo es **la única forma que una persona puede fabricar con precisión
usando herramienta de mano**: se recorta basto, se monta en un pivote sobre
la lijadora de disco y se gira. Sale redondo por construcción, no por
pulso. La excentricidad se consigue taladrando el agujero descentrado, que se
mide con pie de rey.

Y un excéntrico tiene **solución cerrada**: la ley de movimiento del seguidor
se calcula exactamente. Con eso tienes lo que no se consigue de ninguna otra
manera:

- **Entrada conocida y salida medida.** La diferencia es todo lo que el
  modelo no sabe.
- **El juego, medido.** Se gira en un sentido, se marca; se gira en el otro,
  se marca. La diferencia es el juego total de la cadena, amplificado 12×, o
  sea visible a simple vista. Es *el* número que impide subir la relación del
  varillaje, y hoy es una incógnita.
- **La amplificación real**, contra el 12× teórico.
- **El rozamiento y el par**, sin la complicación de un perfil que cambia.

Un excéntrico de 2 mm de excentricidad da 24 mm de recorrido en la punta:
grande, fácil de medir con una regla, y separa limpiamente la señal del ruido.

**Esto es E4 empezando, con 10 € de DM y sin esperar a ningún proveedor.**

### 3c. El cartucho real, y qué queda para él

Solo una cosa, pero es la que decide si el producto existe: **si el trazo
sale a las décimas prometidas**. Eso necesita la pieza de POM cortada a
±0,05 mm, y no hay atajo. Pero llega a un banco donde todo lo demás ya
funciona, y eso convierte un experimento con diez incógnitas en uno con una.

### 3d. El orden que propongo

1. Fijar el calaje y congelarlo (§1). Sin esto, lo que se dibuje se mueve.
2. Fichas de piezas comerciales con cotas de interfaz.
3. `contratos.json` y la tabla de variables.
4. Plataforma paramétrica en Onshape, talla M.
5. **Pedir las piezas comerciales ya**, en paralelo con 4. Tienen plazo de
   entrega y el CAD no.
6. Cartucho de calibración en DM. Montar, medir juego y par.
7. Cartucho mudo en DM. Montar entero, comprobar que se mueve y escribe algo.
8. Corregir el modelo con lo medido.
9. Y entonces sí, encargar el bloque de POM.

---

## 4. El dossier completo de fabricación

Cinco cuadernos, y van separados porque los lee gente distinta en momentos
distintos. Mezclarlos es cómo alguien acaba cortando por una vista a escala
libre.

### Cuaderno 1 · Plantillas de corte 1:1 — `plantillas.pdf`

**Ya existe** (`emit/template.py`). Para el carpintero, sobre el tablero.
Escala 1:1 exacta, cuadro de calibración en cada hoja, semántica de línea en
blanco y negro, siete metadatos por pieza.

Lo que le falta: **una plantilla por material y espesor**, no por conjunto.
El carpintero corta todo el DM de 5 mm de una vez, no va pieza a pieza.

### Cuaderno 2 · Dossier de montaje — `dossier.pdf`

**No existe.** `emit/dossier.py` está en la estructura y vacío. Es el hueco
grande. Debería llevar:

- Vista de conjunto, tres ortográficas y una isométrica, con cajetín.
- **Explosionado por subconjunto**, no uno global ilegible: cartucho,
  seguidor (×3), cinco barras, palanca del lápiz, accionamiento, bastidor.
- **Secuencia numerada** con una imagen por paso, qué piezas entran, qué
  herramienta hace falta y qué hay que comprobar **antes de seguir**.
- **Las cotas de puesta a punto**, que son las que no están en ninguna pieza:
  el calaje de cada brazo, la precarga del muelle, el juego axial de la pila,
  la altura del lápiz sobre el papel.
- **La fase cero**: dónde está la marca, cómo se verifica, y qué pasa si se
  monta mal. Con foto.
- Plantilla de taladrado del bastidor, 1:1, aparte.

### Cuaderno 3 · Hoja de ruta del taller — `taller.pdf`

**No existe y es el que más falta hace en un taller ocupacional**, porque el
dossier de montaje asume a alguien que sabe leer un plano.

- Orden de operaciones con tiempo estimado por operación.
- Qué operaciones son de qué nivel de habilidad, para repartir el trabajo.
- **Galgas pasa / no pasa** en vez de cotas. Esto es lo importante: en lugar
  de «comprueba que quedan 9,5 mm», una galga cortada en el mismo DM que
  entra o no entra. Verificación sin instrumento, sin interpretación y sin
  saber leer un pie de rey. Se cortan con las mismas plantillas.
- Puntos de control con criterio **binario**: pasa o no pasa, nunca «más o
  menos bien».
- Qué hacer cuando no pasa, y a quién avisar.

### Cuaderno 4 · Verificación y ensayo — `verificacion.pdf`

- Hoja de comprobación final, para firmar.
- **La hoja de trazo patrón**, que es la idea que más rendimiento da por lo
  que cuesta: el compilador ya simula el trazo, así que puede **emitirlo
  como PDF a 1:1**. Se pone esa hoja bajo la máquina, se gira la manivela, y
  se ve si el lápiz cae sobre la línea impresa. Cualificación visual, sin
  medir, por cualquiera. Un emisor nuevo de media tarde.
- Registro de la unidad: número de serie, fecha, quién la montó, qué cartucho
  lleva, qué medidas dio. Es también el dato de `bench/` que alimenta E4.

### Cuaderno 5 · Lo que va al cliente — `manual.pdf`

- Cómo se usa y a qué velocidad se gira.
- **Cómo se cambia el cartucho y cómo se verifica la fase.** Si el cliente
  puede comprar cartuchos nuevos —y debería poder—, esta página es el
  producto.
- Mantenimiento: qué se lubrica y qué no, cada cuánto.
- La frase, la fecha, y quién lo fabricó. En un producto cuyo argumento es
  que lo hacen personas, eso no es decoración.

### De dónde sale cada cosa

| Cuaderno | Quién lo genera | Estado |
| --- | --- | --- |
| Plantillas 1:1 | `emit/template.py` | **Hecho** |
| DXF de corte | `emit/dxf.py` | **Hecho** |
| Cartucho 3-D | `emit/step.py` | **Hecho** |
| Trazo patrón | emisor nuevo, del simulador | Media tarde |
| Dossier de montaje | `emit/dossier.py` + vistas de build123d | El hueco grande |
| Hoja de taller y galgas | Plantilla fija + datos del pedido | Por diseñar |
| Manual del cliente | Plantilla fija + la frase | Por diseñar |

Los tres primeros ya salen de `compile.cli`. Los cuatro restantes entran por
el mismo sitio, `emit/paquete.py`, que ya decide qué archivos salen.

---

## 5. Utillajes y galgas

Piezas que no van en la máquina pero sin las cuales la máquina no sale igual
dos veces. Se cortan con las mismas plantillas y del mismo material.

| Utillaje | Para qué | Por qué importa |
| --- | --- | --- |
| **Plantilla de taladrado de postes** | Los tres postes a 71,1 mm y 120° | Si esto se descuadra, no hay ajuste posterior que lo salve |
| **Galga de calaje** | Cala el brazo sobre el eje del seguidor | Montarlo mal escribe basura, y no se nota hasta el final |
| **Galga de fase** | Verifica que el cartucho entra calado | Confirma el poka-yoke en vez de confiar en él |
| **Galga pasa/no-pasa del hueco** | El hueco leva-poste | Verificación binaria, sin pie de rey |
| **Pivote de lijado** | Redondear discos a mano | Es lo que hace posible el cartucho de calibración |
| **Cuna de montaje** | Sujeta el bastidor mientras se monta | Dos manos no bastan para un cinco barras |

---

## 6. La metodología de pedido

Lo que pasa desde que un cliente escribe hasta que sale una caja.

1. **Captura.** El cliente escribe en el lienzo. La interfaz **enseña la caja
   de escritura mientras escribe** y avisa si se sale. Un rechazo en el
   momento de escribir es una molestia; el mismo rechazo tres días después es
   un pedido perdido.
2. **Compilación.** El compilador devuelve veredicto: apto, o no apto con
   motivo y sugerencia. Ya funciona así.
3. **Talla.** Si no cabe en M, se prueba L. Si no cabe en L, se dice que no y
   se propone acortar. El cliente elige talla, no configura una máquina.
4. **Presupuesto.** Sale del informe: cartucho a precio cerrado más
   plataforma de stock. **No hace falta compilar para dar precio**, porque el
   bloque cuesta lo mismo sea cual sea la frase.
5. **Fabricación.** El DXF al taller de corte; las plantillas, el dossier y la
   hoja de taller a producción; la plataforma sale del stock.
6. **Verificación.** Hoja de trazo patrón, comprobación final, registro.
7. **Entrega.** Máquina, manual y el certificado con su frase.

Los pasos 1 a 4 son minutos y no tocan a nadie del taller. Es lo que permite
que un producto artesanal se pida por internet.

---

## 7. Qué hay que construir, por orden de lo que desbloquea

| | Qué | Por qué ahora |
| --- | --- | --- |
| 1 | **Fijar el calaje** a una constante de máquina | Sin esto el brazo no es pieza de stock y lo que se dibuje se mueve |
| 2 | Enchufar **C4** al compilador | El presupuesto de error deja de ser una estimación |
| 3 | **Fichas de piezas comerciales** | Evita la clase de error del Ø15 |
| 4 | **`contratos.json`** y la tabla de variables de Onshape | Un número, un sitio |
| 5 | **Pedir las piezas** | Tienen plazo; el CAD no. Va en paralelo |
| 6 | **Emisor de trazo patrón** | Media tarde, y da el método de verificación entero |
| 7 | **Plataforma paramétrica** en Onshape, talla M | Ya se puede: los parámetros están fijos |
| 8 | **Cartucho de calibración** en DM | E4 empieza aquí, sin esperar a nadie |
| 9 | **`emit/dossier.py`** | El hueco grande. Necesita el 3-D del 7 |
| 10 | Hoja de taller y galgas | Necesita el dossier del 9 |

Del 1 al 6 no hace falta CAD ni proveedor: son código, datos y una llamada de
teléfono. Del 7 en adelante, sí.
