# Piezas del reloj, su orden de fabricación y sus variables

Qué se fabrica, en qué orden, con qué utillaje, y **de qué parámetro sale cada
cota**. Si una pieza no dice de dónde salen sus medidas, es que falta decidirlo.

La cadena causal que gobierna todo esto está en `docs/reloj/metodologia.md`, §1.
Los números congelados, en `docs/reloj/contratos.json`.

---

## La decisión que hace esto fabricable: piñones de linterna

**Los piñones no llevan dientes. Llevan pernos.**

Un piñón de linterna son dos discos paralelos con pernos cilíndricos entre
ellos. Es la solución histórica de los relojes de torre y de los relojes de
madera, y para este taller resuelve de golpe el problema más difícil:

| | Piñón de dientes | **Piñón de linterna** |
| --- | --- | --- |
| Cómo se hace | Cortar 8 perfiles cicloidales de 6 mm en madera, a mano | **Taladrar 8 agujeros en un círculo y meter 8 varillas** |
| Qué precisión pide | El perfil del diente, décimas | La posición del agujero, que la da la plantilla |
| Qué pasa si hay polvo | Agarrota | Lo expulsa: el hueco entre pernos es abierto |
| Socavado con 8 hojas | Problema real | **No existe**: un perno cilíndrico no tiene base que socavar |
| Si uno se rompe | Pieza nueva | Se saca y se mete otro |

Las ruedas que los mueven sí llevan perfil, pero una rueda de 64 dientes y
Ø128 mm tiene dientes de 6 mm de paso que se cortan con sierra de marquetería
siguiendo la plantilla. **Lo difícil se compra en forma de varilla calibrada.**

Esto añade una envolvente propia: los pernos necesitan madera entre ellos.

> **Separación entre centros de perno ≥ 2 × diámetro de perno.**
> Con 8 pernos de Ø3 en un círculo primitivo de Ø16, la separación es 6,28 mm y
> el límite son 6,0. Pasa, y por poco: es lo que pone suelo al módulo del
> dentado.

---

## Las variables, por nivel

Repetidas aquí en forma de tabla porque son lo que hay que mirar al configurar.
Solo las de **nivel 0** se teclean.

### Nivel 0 · Se eligen (son las cinco preguntas de la app)

| Variable | Unidad | Por defecto | Qué arrastra |
| --- | --- | --- | --- |
| `periodo_pendulo` | s | 2,0 | Longitud del péndulo, altura de la caja, vuelta de la rueda de escape |
| `dientes_escape` | — | 30 | Aguja de segundos, relación que pide el tren |
| `autonomia_horas` | h | 30 | Vueltas del tambor, nº de ruedas del tren |
| `caida_disponible` | m | 1,0 | Polea, longitud de cuerda, diámetro del tambor |
| `diametro_esfera` | mm | 180 | Solo esfera, agujas y caja. **No toca el movimiento** |

### Nivel 1 · Salen de la física (nadie las teclea)

| Variable | Fórmula | Valor por defecto |
| --- | --- | --- |
| `longitud_pendulo` | `g·T²/4π²`, corregido por inercia real | 994 mm |
| `vuelta_rueda_escape` | `dientes_escape × periodo_pendulo` | 60 s |
| `relacion_tren` | `3600 / vuelta_rueda_escape` | 60:1 |
| `vueltas_tambor` | `autonomia_horas / horas_por_vuelta_rueda_grande` | 7,5 |
| `longitud_cuerda` | `caida_disponible × ramales_polea` | 2,0 m |
| `diametro_tambor` | `longitud_cuerda / (π · vueltas_tambor)` | 85 mm |

### Nivel 2 · El compilador propone, la envolvente juzga

| Variable | Qué la limita | Valor de ejemplo |
| --- | --- | --- |
| `modulo` | Separación entre pernos, tamaño de platina, holgura de corte | 2,0 mm |
| `dientes` de cada rueda | Relación exacta, mínimo 8 pernos en el piñón | 64 / 64 / 60 |
| `pernos` de cada piñón | ≥ 8; separación ≥ 2 × diámetro | 16 / 8 / 8 |
| `diametro_perno` | Resistencia y separación | 3 mm |
| `distancias_entre_centros` | `modulo × (z_rueda + z_piñón) / 2` | 80 / 72 / 68 mm |
| `masa_lenteja` | Q del péndulo y perturbación del escape | ~1 kg |
| `masa_pesa` | **Par mínimo MEDIDO en el banco** | 3,5 kg, **previsión** |
| `masa_pesa_techo` | Lo que aguanta la estructura sin rehacerla | 5 kg |

### El tren de ejemplo, que el compilador puede cambiar

Una solución válida con los valores por defecto. Sirve para comprobar que el
planteamiento cierra; no es una decisión congelada.

| Eje | Una vuelta cada | Lo mueve | Lleva |
| --- | --- | --- | --- |
| Rueda grande | 4 h | la pesa, por el tambor | Tambor Ø85, trinquete |
| Central | 1 h | rueda grande 64 → linterna 16 | **Aguja de minutos**, cañón |
| Tercera | 7,5 min | rueda central 64 → linterna 8 | — |
| Escape | 1 min | tercera rueda 60 → linterna 8 | Rueda de escape 30 d, **aguja de segundos** |

Comprobación: 30 dientes × 2 s = 60 s por vuelta de escape; 60 × 7,5 × ... hasta
la central da 1 vuelta/hora; la rueda grande da 7,5 vueltas en 30 h. Cierra.

---

## El orden de fabricación

Cinco tandas. **Cada tanda está cerrada por una medida**, no por un calendario:
hasta que el número no está medido, la tanda siguiente se fabricaría a ciegas.

### Tanda 0 · Lo que se compra

Va primero porque tiene plazo de entrega y lo demás no. Cada referencia necesita
su ficha en `docs/piezas/`, con cotas de interfaz, fuente y fecha, igual que las
del escribiente.

| Pieza | Cota de interfaz que importa | De qué variable depende |
| --- | --- | --- |
| Muelle de suspensión | Espesor de la lámina y longitud libre | `masa_lenteja` |
| Varilla calibrada para ejes | Ø, tolerancia h7 | Contrato de eje |
| Varilla para pernos de linterna | Ø3, rectitud | `diametro_perno` |
| Rodamientos de los ejes rápidos | Ø interior, exterior, ancho | Ø del eje |
| Cuerda | Ø, carga, **estiramiento** | `tension_cuerda_techo` = 24,5 N, **no la previsión** |
| Tuerca de regulación M6 + arandela | Paso 1,0 mm | `longitud_pendulo` |
| Tornillería y pasadores | DIN | — |

### Tanda 1 · El péndulo — se puede cortar hoy

No depende de ninguna medida previa. **Es lo primero que se fabrica.**

| Nº | Pieza | De dónde salen sus cotas | Proceso |
| --- | --- | --- | --- |
| 1.1 | Varilla del péndulo | `longitud_pendulo`, menos la lenteja y el muelle | Listón, veta a lo largo |
| 1.2 | Lenteja | `masa_lenteja`; el Ø es libre | Disco + lastre, **pivote de lijado** |
| 1.3 | Soporte de suspensión | Cota del muelle comprado | Plantilla |
| 1.4 | Tope de regulación | Paso de la tuerca M6 | Comercial + taladro |

→ **Medida que cierra la tanda:** 100 oscilaciones en 200,0 s, y el Q contando
cuántas tarda la amplitud en caer a la mitad. Entra en `bench/reloj/pendulo.json`.

### Tanda 2 · El escape — tras medir el péndulo

Necesita el Q de la tanda 1 para saber cuánta energía hay que reponer por
oscilación, que es lo que fija el ángulo de impulso.

| Nº | Pieza | De dónde salen sus cotas | Proceso |
| --- | --- | --- | --- |
| 2.1 | Rueda de escape | `dientes_escape`, `modulo`; perfil de diente de escape | Plantilla, **galga de diente** |
| 2.2 | Cuerpo del áncora | Abarca `dientes_escape/4 + 0,5` ≈ 7,5 dientes | Plantilla |
| 2.3 | Paletas (×2) | Ángulo de reposo y de impulso; **ranura de ajuste** | Postizas, atornilladas |
| 2.4 | Horquilla | Huelgo con la varilla del péndulo | Plantilla |
| 2.5 | Platina provisional de banco | Solo 2 ejes; se tira después | Plantilla, una sola |

→ **Medida que cierra la tanda:** el par mínimo con el que arranca y mantiene
amplitud, y la posición buena de las paletas. Entra en
`bench/reloj/escape.json`. **Es el número que dimensiona todo lo que sigue.**

### Tanda 3 · El movimiento — tras medir el par

Ahora sí se puede dimensionar el tren, porque se sabe qué par tiene que llegar
al escape y cuánto se pierde por el camino.

| Nº | Pieza | De dónde salen sus cotas | Proceso |
| --- | --- | --- | --- |
| 3.1 | **Platinas (×2)** | `distancias_entre_centros` | **Taladradas apiladas**, plantilla de taladrado |
| 3.2 | Pilares (×4) | Ancho de la rueda más holgura | Listón a medida |
| 3.3 | Rueda grande | `dientes`, `modulo` | Plantilla, pivote de lijado |
| 3.4 | Tambor | `diametro_tambor`, `longitud_cuerda` | Torneado o discos apilados |
| 3.5 | Trinquete y cliquet | Par en la rueda grande | Plantilla |
| 3.6 | Muelle del cliquet | — | Comercial o fleje |
| 3.7 | Rueda central | `dientes`, `modulo` | Plantilla |
| 3.8 | Piñón de linterna central | 16 pernos en Ø40 | **Taladro con plantilla** + varilla |
| 3.9 | Tercera rueda | `dientes`, `modulo` | Plantilla |
| 3.10 | Piñón de linterna tercero | 8 pernos en Ø16 | Taladro + varilla |
| 3.11 | Piñón de linterna de escape | 8 pernos en Ø16 | Taladro + varilla |
| 3.12 | Ejes (×4) | Distancia entre platinas; Ø del contrato | Varilla calibrada, a medida |
| 3.13 | Separadores y arandelas | Juego axial declarado | Tubo o disco |

→ **Medida que cierra la tanda:** 30 horas seguidas sin pararse, con la pesa
nominal. Binario.

### Tanda 4 · La esfera y lo que se ve — en paralelo

No depende del par ni del tren. **Se puede fabricar a la vez que la tanda 3**,
y es el trabajo de nivel inicial del taller.

| Nº | Pieza | De dónde salen sus cotas | Proceso |
| --- | --- | --- | --- |
| 4.1 | Esfera | `diametro_esfera` | Plantilla impresa, pegada |
| 4.2 | Aguja de minutos | 0,95 × radio de esfera | Plantilla |
| 4.3 | Aguja de horas | 0,65 × radio de esfera | Plantilla |
| 4.4 | Aguja de segundos | Esfera pequeña sobre el eje de escape | Plantilla |
| 4.5 | Cañón de minutos | Ø del eje central, **ajuste a fricción** | Tubo + fieltro |
| 4.6 | Rueda y piñón de minutos | Relación 12:1 del tren de esfera | Plantilla |
| 4.7 | Rueda de horas | Relación 12:1 | Plantilla |
| 4.8 | Polea de la pesa | `ramales_polea` | Disco + rodamiento |
| 4.9 | Cubo de la pesa | `masa_pesa` = 3,5 kg de previsión; **se llena hasta que ande** | Tubo + perdigón o arena |
| 4.10 | Tabla de pared y caja | `longitud_pendulo` + `caida_disponible` | Plantilla |

→ **Medida que cierra la tanda:** siete días de marcha dentro de ±1 min/día.

### Tanda U · Utillajes — antes de la tanda que los usa

| Nº | Utillaje | Antes de | Por qué |
| --- | --- | --- | --- |
| U.1 | Pivote de lijado | Tanda 1 | Lenteja y ruedas redondas por construcción |
| U.2 | Galga de diente | Tanda 2 | Verifica el perfil sin pie de rey |
| U.3 | Galga de reposo | Tanda 2 | Repite el ajuste de paletas |
| U.4 | **Plantilla de taladrado de platinas** | Tanda 3 | **La pieza más crítica del paquete** |
| U.5 | Galga de centros | Tanda 3 | Verificación binaria de cada distancia |
| U.6 | Plantilla de pernos | Tanda 3 | Los 8 agujeros del piñón, repetibles |
| U.7 | Cuna de montaje | Tanda 3 | Cuatro ejes a la vez no se sujetan a mano |

---

## Resumen: qué bloquea qué

| Tanda | Qué entrega | Sin ella no se puede |
| --- | --- | --- |
| 0 · Compra | Cotas de interfaz reales | Dibujar nada que toque una pieza comprada |
| 1 · Péndulo | Q y periodo reales | Dimensionar el impulso del escape |
| 2 · Escape | **Par mínimo medido** | Dimensionar ruedas, ejes y pesa |
| 3 · Movimiento | Rozamiento real de la cadena | Fijar la pesa definitiva |
| 4 · Esfera y caja | El reloj montado | Medir la marcha en 7 días |

**La única dependencia dura es la 2.** Mientras el par no esté medido, cualquier
rueda que se corte se corta con un número inventado.
