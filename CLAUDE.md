# CLAUDE.md

Herramienta para diseñar y fabricar **máquinas mecánicas programables**: autómatas
de levas, cajas de música, telares y máquinas de trabajo impulsadas por personas.

El primer producto es el **escribiente**: el cliente escribe una frase a mano y el
sistema genera las tres levas (x, y, levantamiento) que la reproducen, más la
documentación para fabricarla.

- Referencia conceptual (principios, ontología, módulos, hitos): `docs/baseline.md`
- Este archivo es la referencia **técnica** del repositorio.

---

## Reglas que no se rompen

1. **Todo programa es función de θ**, el ángulo del eje maestro. Nunca del tiempo.
   Si aparece un `dt` dentro de `core/`, algo está mal planteado.
2. **`core/` es puro.** Sin red, sin disco, sin Onshape, sin FastAPI. Entra dato,
   sale dato. Todo depende de `core/`; `core/` no depende de nada del proyecto.
3. **SI dentro, mm fuera.** Metros, radianes, newtons y julios en todo `core/`.
   La conversión a milímetros y grados ocurre solo en `emit/` y en `api/`.
   Nunca a medias, nunca "por comodidad".
4. **Ninguna geometría de producción la genera un modelo de lenguaje.** El motor
   es determinista: mismo input, mismo DXF, byte a byte. Claude escribe y prueba
   el motor; no fabrica pedidos.
5. **Nada se emite sin pasar la envolvente.** `compile/` valida antes de llamar a
   cualquier emisor. Que la envolvente falle es un resultado legítimo que se
   devuelve al usuario, no una excepción que se traga.
6. **Ningún módulo sin ficha.** Todo módulo es un modelo Pydantic validado. Sin
   ficha no entra en una máquina.
7. **De la escritura se captura solo geometría.** Nunca tiempo, presión ni
   velocidad. Se reparametriza en el cliente, antes de enviar nada.
8. **Tests antes de feature en `core/`.** En el resto del repo puede ir después.
9. **Un contrato congelado no se toca sin decirlo.** Ver `docs/contratos.md`.
   Si un cambio los afecta, párate y avisa antes de implementar.

---

## Comandos

```bash
uv sync                      # instalar dependencias
uv sync --group cad          # + el kernel OCCT, solo si vas a exportar STEP
uv sync --group web          # + la interfaz local de pedidos
uv run pytest                # tests
uv run pytest -m core        # solo el núcleo (rápido)
uv run --group cad pytest    # + los tests del kernel OCCT, que si no SE SALTAN
uv run ruff check --fix .    # lint
uv run ruff format .         # formato
uv run mypy core compile emit  # tipos (estricto en core/)

uv run python scripts/export_schema.py        # esquema JSON tras tocar un modelo
uv run python scripts/exportar_variables.py   # variables para el Variable Studio del CAD
uv run --group cad python scripts/exportar_catalogo.py  # STEP de las piezas comerciales
uv run --group cad python scripts/exportar_para_cad.py demo/hola.json --out build/cad/  # el paquete entero para el CAD
uv run python scripts/dibujar_perfiles.py     # lámina de perfiles para revisar
uv run python scripts/dibujar_maquina.py      # el dibujo conceptual, generado desde el modelo
uv run python scripts/dibujar_conjunto.py     # el PLANO DE CONJUNTO: planta, alzado y despiece
uv run --group cad python scripts/ver.py seguidor            # una pieza en el visor de VS Code
uv run --group cad python scripts/ver.py --conjunto --theta 90  # la máquina montada, a ese ángulo
uv run python scripts/dibujar_piezas.py       # sección y cotas de cada pieza comercial, para dibujarla en el CAD
uv run python scripts/dibujar_amplificador.py # el cabestrante 6:1, acotado desde el contrato
uv run python scripts/dibujar_cinco_barras.py # el varillaje y la palanca, acotados desde el contrato
uv run python scripts/dibujar_plano_cabestrante.py  # plano con vistas y cotas del sector y del tambor
uv run python scripts/dibujar_plano_brazos.py       # plano con vistas y cotas de los tres brazos
uv run python scripts/plantillas_demo.py      # plantillas 1:1 de muestra
uv run python scripts/regenerar_golden.py     # SOLO si el cambio es intencionado

uv run python scripts/comparar_dxf.py pieza.dxf   # cruzar el croquis contra el contrato
uv run python scripts/comparar_dxf.py pieza.step  # y el sólido: lo mismo MÁS el espesor
uv run python scripts/listado_piezas.py --escribir  # el listado de docs/metodologia.md §2d
uv run python scripts/dibujar_pieza.py mordaza --out build/mordaza.svg  # el boceto de una pieza

uv run python -m compile.cli demo/hola.json --out build/   # compilar un pedido
uv run python -m compile.cli demo/hola.json --corte 28      # con un presupuesto real del taller
uv run --group web uvicorn api.main:app --reload           # la interfaz de pedidos, en http://127.0.0.1:8000
uv run python scripts/extraer_fuente.py cursiva            # SOLO al añadir una fuente
npm --prefix web run dev                                   # frontend en local
```

Antes de dar por terminado un cambio: `uv run ruff check . && uv run mypy core compile emit api && uv run pytest`.

---

## Estructura

```
core/                 # PURO. Geometría, cinemática, energía.
  program.py          #   Programa, Pista, Evento — el modelo θ-indexado
  module.py           #   Ficha de módulo, ModuloMontado, Maquina
  verdict.py          #   Veredicto e Incidencia
  errors.py           #   Excepciones de dominio
  units.py            #   Constructores con unidad. Nada de floats desnudos.
  escritura.py        #   Front-end: frase -> tres pistas θ (arco, reparto, capacidad)
  tipografia.py       #   C0 · un texto tecleado -> trazos y renglones, en monotrazo
  cam/
    synth.py          #   C2 · curva de paso y perfil
    offset.py         #   C2 · offset por radio de rodillo
    envelope.py       #   C3 · ángulo de presión, curvatura, veredicto
    contacto.py       #   C3 · ψ recuperado apoyando el rodillo en el perfil cortado
  actors/             #   C1 · catálogo de cinemáticas inversas
  energy/
    budget.py         #   C6 · par y energía
    flywheel.py       #   C7 · inercia y volante
    humano.py         #   C9 · lo que da una mano en la manivela
    accumulator.py    #   C10 · carga y descarga
  tolerance.py        #   C4 · cadena de tolerancias
  solido.py           #   Masa y momento polar de un prisma, desde su polígono
  comercial.py        #   Ficha de pieza de catálogo: cotas de interfaz y fuente
  tarjeta.py          #   El papel donde escribe, y la caja que queda dentro
compile/              # Orquesta: intención -> piezas + informe. I/O permitido.
  escribiente.py      #   La máquina concreta: compilar y simular
  conjunto.py         #   El cartucho montado: interferencias, pila, masa
  energia.py          #   ¿Puede girarlo una persona, y sale limpio?
  tolerancias.py      #   C4 aplicado: cuánto error llega de verdad a la punta
  coste.py            #   Qué cuesta: lo que se compra y lo que se corta
  contratos.py        #   Los contratos congelados, como dato
  informe.py          #   El informe del pedido, en markdown
  cli.py              #   Un pedido, un comando
  texto.py            #   Carga la fuente y compone el texto. El disco de C0
  tarjetas.py         #   El catálogo de formatos, y la máquina para cada uno
emit/
  pieza.py            #   Pieza y sus siete metadatos, compartida por los tres
  layout.py           #   Maquetación 1:1 en mm: cabecera, colocación, troceado
  calibracion.py      #   Perfil de impresora: factores x/y, hoja patrón
  paquete.py          #   Qué archivos salen y qué lleva cada uno
  template.py         #   PDF 1:1 para copistería          <- ver abajo
  patron.py           #   Hoja de trazo patrón 1:1 para verificar sin medir
  catalogo.py         #   Envolventes STEP de las piezas comerciales, desde su ficha
  dxf.py              #   Corte láser / CNC
  dossier.py          #   Dossier de montaje
  step.py             #   3D
  montaje.py          #   El conjunto en 3D: sólidos de plataforma y dónde va cada uno
  onshape.py          #   Gemelo paramétrico (1 llamada por pedido)
api/                  # FastAPI
web/                  # React + Vite + TypeScript
bench/                # Datos del banco de ensayo y calibraciones medidas
  impresoras/         #   Un perfil por impresora, con fecha, papel e instrumento
  precios.json        #   Precios de catálogo, con fecha y enlace por línea
docs/
  fuentes/            #   Una fuente monotrazo por archivo. Dato, no dependencia
  tarjetas/           #   Un formato de papel por archivo, con su caja derivada
web/                  #   index.html: la interfaz local de pedidos
tests/
```

---

## Arquitectura

Tres capas, en este orden de dependencia:

**Núcleo → Compilador → Emisores.** El núcleo no sabe que existe un archivo. El
compilador orquesta y decide. Los emisores solo traducen a formato.

Patrón de compilación, siempre el mismo:

1. **Captura** — intención del usuario (escritura, melodía, movimiento, tarea).
2. **Front-end** — normaliza, reparametriza por longitud de arco, reparte grados
   de θ, comprueba capacidad.
3. **Núcleo** — C1 a C10 según la clase de máquina.
4. **Envolvente** — juez enchufable según clase. Devuelve veredicto y motivo.
5. **Emisores** — DXF, plantilla, dossier, 3D.

**Un solo motor de comprobación, límites distintos por clase.** El ángulo de
presión, la energía de impacto y el par disponible frente al demandado son el
mismo patrón: una magnitud evaluada en cada grado del ciclo contra un límite. No
escribas un validador por máquina; escribe uno y enchúfale el límite.

---

## Stack

| Capa | Elección | Por qué |
| --- | --- | --- |
| Lenguaje | Python 3.12+, `uv` | Ecosistema geométrico y científico |
| Modelo de datos | Pydantic v2 | La ficha de módulo *es* un esquema |
| Numérico | numpy, scipy | Splines periódicos, optimización |
| 2D | shapely | Offset, autointersecciones, booleanas |
| 3D | build123d | Kernel OCCT, dibujo técnico, exportación |
| DXF | ezdxf | Escritura y su add-on de exportación |
| PDF | ezdxf (`PyMuPdfBackend`) + reportlab | Vectorial exacto y maquetación |
| API | FastAPI + uvicorn | Tipado, esquema automático |
| Persistencia | SQLite → Postgres cuando haga falta | No adelantar complejidad |
| Frontend | React + Vite + TypeScript + Tailwind | Soporte, tipos, velocidad |
| Captura | Canvas 2D + Pointer Events | Nativo, sin dependencias |

No añadas cola de trabajos, Redis, Docker Compose ni Celery hasta que un pedido
real tarde demasiado. Síncrono primero.

---

## Los cuatro emisores

Una máquina no se entrega como un DXF. Se entrega como un **paquete de fabricación**
que permite construirla por la vía que el cliente pueda pagar.

**Planos de pieza ≠ documentación.** Se imprimen distinto, en momentos distintos
y para manos distintas. No van en el mismo PDF:

| | Plantillas de corte | Dossier de montaje |
| --- | --- | --- |
| Para quién | El carpintero, sobre el tablero | Quien monta, sobre la mesa |
| Escala | 1:1 exacta, siempre | Libre, con la escala rotulada |
| Formato | El que pida la pieza, de A4 a A0 | A4, encuadernable |
| Vida | Se pega, se corta y se tira | Se guarda con la máquina |
| Cuadro de calibración | Sí, en cada hoja | No |

El compilador entrega dos archivos separados, `plantillas.pdf` y `dossier.pdf`.
Mezclar una vista a escala libre con un plano 1:1 en el mismo documento es la
forma más rápida de que alguien corte por la vista. **No es una convención de
nombres**: cada `Lamina` declara su `escala` y `escribir_pdf` se niega a
escribir un documento con dos.

### `emit/dxf.py` — corte digital
Láser o CNC. Compensación de kerf **aquí**, nunca en `core/`. El kerf es un dato
calibrado por material y espesor: vive en `bench/kerf.json`. Exporta splines como
polilínea densa o arcos: mucho software de láser no traga splines.

### `emit/template.py` — plantilla 1:1 para copistería
Genera un PDF a escala real que se imprime en una copistería, se pega sobre el
tablero y se corta a mano o con sierra de cinta. Es lo que permite fabricar sin
máquina digital. Requisitos no negociables:

- **Cuadro de calibración** de 100 × 100 mm en cada hoja, con la leyenda
  *"si este cuadrado no mide 100 mm, la impresión está escalada"*. Sin esto, la
  plantilla es peligrosa.
- **Imprimir sin ajuste de página.** Indicado en la hoja.
- **Semántica de línea** distinguible en blanco y negro: corte (continua gruesa),
  taladro (cruz más círculo con el diámetro escrito), referencia (discontinua),
  cara oculta (punteada).
- **Metadatos por pieza**: número, material, espesor, cantidad, orientación de
  veta, y a qué conjunto pertenece.
- **Teselado** con solape y marcas de registro si la pieza no cabe en la hoja, y
  modo de hoja única para plóter A0/A1.
- **Formato por trabajo, no por pieza.** El formato lo elige el pedido: A4 para
  lo que quepa, A3 o A2 para levas grandes, A1/A0 en hoja única de plóter para
  el bastidor. `formato_minimo()` propone; la interfaz deja cambiarlo, y el
  cambio no toca la geometría, solo la maquetación.
- **Varias piezas por hoja.** `maquetar_juego()` agrupa las que caben, con
  holgura para la hoja de la sierra; lo que no cabe se trocea aparte con su
  cabecera entera. El conjunto va en la cabecera —con la lista de números,
  que es la hoja de recuento— y los otros seis metadatos junto a su pieza. El
  reparto es por estantes: **no** resuelve el empaquetado óptimo, y no lo hará
  hasta E5.

### `emit/calibracion.py` — perfil de impresora
Una impresora no imprime a escala. El error típico está entre el 0,2 y el 1 %, y
es **sistemático**: la misma máquina con el mismo papel se equivoca siempre
igual. Lo sistemático se compensa; la deriva —humedad, fusor, arrastre— no. De
ahí que el perfil se mida una vez y el cuadro se siga comprobando siempre.

- **Dos factores, no uno.** `factor_x` y `factor_y` por separado: el arrastre
  del papel deforma más en la dirección de avance que a lo ancho, y un factor
  único reparte el error del eje malo sobre el bueno.
- **El patrón es más largo que el cuadro.** Medir 100 mm con una regla da un
  error de lectura de unos ±0,25 mm, es decir un 0,25 %, del mismo orden que el
  error que se quiere medir: calibrar sobre 100 mm no mejora casi nada. La hoja
  patrón lleva dos reglas, **150 mm** para pie de rey (0,05 mm → 0,03 %) y
  **250 mm** para cinta métrica (1 mm → 0,4 %, pero es lo que hay en cualquier
  taller). Se usa la que se tenga, y el perfil anota cuál.
- **Compensar no es verificar.** El cuadro de 100 × 100 mm sigue en todas las
  hojas aunque el perfil esté aplicado, y se escala con él. El factor corrige el
  error conocido; el cuadro caza el que no lo es.
- **Una impresora se puede rechazar.** La hoja patrón repite la medida en tres
  bandas. Si el error no es uniforme dentro de la hoja no hay factor que lo
  arregle: veredicto negativo con motivo, en vez de compensar una media que
  miente.
- **El perfil es dato, no código.** Un JSON por impresora en `bench/impresoras/`,
  con fecha, formato, papel e instrumento de medida, igual que el kerf.
  Configurable desde la interfaz: cada cliente calibra su copistería, no la
  nuestra. Sin perfil el sistema sigue funcionando, con factores 1,0 y el aviso
  de que no está calibrado.

### `emit/patron.py` — la hoja de trazo patrón
El compilador ya simula el trazo para comprobarse a sí mismo; esto lo saca
por la impresora a 1:1. Se pone bajo la máquina alineando las cuatro
escuadras, se gira la manivela y se mira si el lápiz cae sobre la línea.
**Cualifica cualquiera, sin instrumentos y sin saber leer un plano**, que en
un taller ocupacional es la diferencia entre una verificación que se hace y
una que no.

Caza lo que se ve a simple vista y es casi todo lo que falla al montar: un
cartucho calado donde no toca, un brazo con el calaje equivocado, una leva
cambiada de sitio, el lápiz que no levanta. No caza décimas.

Se imprime también el **vuelo**, punteado: por dónde pasa la punta con el
lápiz levantado. No queda en el papel del cliente, pero dice si el
levantamiento ocurre donde debe.

`UMBRAL_DE_APOYO` no puede ser cero: la altura sale de recorrer la leva, así
que oscila alrededor del cero unas milésimas, y con umbral cero el trazo se
parte en costuras donde la máquina dibuja seguido.

### `emit/catalogo.py` — las piezas comerciales, en STEP
Para montar el conjunto en un CAD hacen falta los sólidos de las catorce
referencias que se compran. Bajarlos del fabricante tiene tres pegas: pueden
no coincidir con lo que calcula el compilador, la mitad no existen (el
portaminas, los genéricos), y los de bibliotecas de terceros tienen licencia
—los de GrabCAD son «for private use only»—.

Aquí el sólido **se genera desde la ficha**, así que por construcción dice lo
mismo que el compilador, existe siempre y es nuestro. Como sale en STEP, no
ata la decisión de qué CAD usar.

Son **envolventes**: exactas en las cotas que la ficha marca como críticas y
toscas en el resto. Un engranaje sale como un disco sin dientes, porque para
saber si cabe no aportan nada y la pieza se compra hecha. Para el render de
venta se importa el STEP del fabricante encima.

Hay un test que mide la caja envolvente de cada sólido y la compara con la
cota crítica de su ficha, y otro que exige que **ninguna familia del enum se
quede sin forma**: si alguien añade una familia y olvida el generador, salta
al añadirla y no al primer pedido.

**Cinco de las catorce están contrastadas contra Onshape** (2026-09-30):
poste, árbol, pasador, separador y casquillo, dibujadas allí desde las mismas
cotas y pesadas con las mismas densidades. Coinciden: el poste da 3518,584 mm³
y 27,445 g por los **tres** caminos —el polígono de `core/solido.py`, el OCCT
de build123d y el de Onshape—, que no comparten una línea de código.
`MASAS_VERIFICADAS` las congela; si un número cambia, el modelo dibujado ha
dejado de coincidir con el compilador y hay que redibujarlo, no ajustar el
test.

**Solo esas cinco**, porque son aquellas cuya envolvente **es** el sólido
real. Las otras nueve no: el muelle sale como el cilindro que ocupa y pesaría
32 g en vez de cuatro, el rodamiento como un anillo macizo sin bolas ni
pistas, el engranaje como un disco sin dientes. Para saber si caben eso basta;
para pesarlos su masa buena es la del proveedor, y debería ir en la ficha.

Pendiente de medir con el pie de rey: **si la valona del casquillo entra
dentro de sus 6 mm o se suma**. El modelo la mete dentro —altura total 6— y
la ficha no lo aclara. La masa apenas cambia; la altura de la pila sí.

### `emit/dossier.py` — dossier de montaje
El PDF que acompaña a las piezas. Contiene: vistas ortográficas y una isométrica,
lista de materiales, lista de tornillería y comercial, secuencia de montaje paso a
paso con vistas explosionadas, la marca de fase cero y cómo verificarla, y la hoja
de comprobación final. Se apoya en `project_to_viewport()` y `ExportSVG` de
build123d para las vistas, y en `TechnicalDrawing` para el cajetín.

### `emit/step.py` — el sólido 3-D
No calcula nada: la masa y la inercia salen exactas del polígono en
`core/solido.py` y las interferencias que importan son planas. Lo que da, y no
se consigue de otra manera, es un **STEP B-rep**: caras, aristas y vértices de
verdad, que es lo que un CAD necesita para acotar y emparejar. Una malla —lo
que exporta un OpenSCAD— entra como un amasijo de triángulos inservible.

`build123d` es **dependencia opcional** (`uv sync --group cad`): son unos 800 MB
de kernel OCCT y nada de lo que calcula el proyecto depende de él. Sin la
dependencia, todo lo demás funciona y el CLI avisa.

Hay un test que contrasta la masa del kernel contra la del polígono. Coinciden
al 0,02 %, por dos caminos que no comparten una línea de código.

### `emit/onshape.py` — el gemelo paramétrico
**El reparto con Onshape, que es lo que hace que su cuota anual deje de
importar:**

| | Quién lo hace | Cómo llega a Onshape |
| --- | --- | --- |
| **El cartucho** — cambia en cada pedido, no se edita nunca | Lo genera el compilador | DXF para bocetos, STEP para el sólido. Se arrastra el archivo |
| **La plataforma** — no cambia entre pedidos, tiene que seguir siendo paramétrica | FeatureScript escrito a mano, una vez | Se escribe dentro de Onshape |

Así el camino **por pedido**, que es el que se repite cientos de veces, no
toca la API nunca. Los números que comparten los dos lados —eje, bastidor,
fase, calaje— viven en **`docs/contratos.json`**, y
`scripts/exportar_variables.py` los convierte en la tabla que se pega **una
vez** en el Variable Studio de Onshape. De ahí las referencian todas las
Part Studios de la plataforma.

**El flujo es de un solo sentido**: se toca el JSON, se regenera, se pega.
Lo que se edite dentro de Onshape se pierde en la siguiente regeneración y,
peor, deja de coincidir con lo que calcula el compilador sin que nadie se
entere. El markdown sigue siendo donde se explica el porqué y donde vive el
registro de cambios; lo que ya no está ahí es el número suelto.

---

## El contrato de datos (E1)

Cuatro decisiones que condicionan todo lo demás:

- **θ vive en [0, 2π), sin repetir el extremo.** Guardar la muestra de 2π
  permitiría que contradijera a la de 0. El cierre es implícito.
- **Las pistas guardan muestras, no splines**, en dos listas paralelas
  (`thetas`, `valores`). El spline es un cálculo, no un dato.
- **Un canal es la señal, no el cable.** Cada canal tiene exactamente un
  módulo que lo `produce` — la leva o el tambor que lo almacena — y los que
  hay aguas abajo lo `consume`n. `Maquina` comprueba ese cableado.
- **Ficha ≠ montaje.** `FichaModulo` es la entrada de catálogo; el desfase y
  la bahía viven en `ModuloMontado`. Una estación de pedal no tiene fase; su
  instalación sí.
- **La cinemática se referencia por clave**, no se incrusta: una función no se
  serializa. Vive en el actuador que consume el canal, nunca en la leva.
- **El catálogo es dato**: un JSON por módulo en `docs/modulos/`, validado
  contra el esquema de `docs/schema/`. Añadir un módulo no es programar.
- **Las piezas comerciales también tienen ficha**, en `docs/piezas/`: sus
  **cotas de interfaz** —las que otra pieza toca— con fuente, fecha y enlace.
  La ficha manda sobre el STEP del fabricante, que se importa para mirar y
  no para acotar. `tests/compile/test_piezas_reales.py` cruza cada cota
  crítica con el número que usa el compilador, y es lo que impide que una
  cota mal leída se cuele en la geometría.

Tras tocar un modelo: `uv run python scripts/export_schema.py`. Hay un test que
falla si el esquema versionado se queda atrás.

---

## Convenciones

- **Vocabulario del dominio en español** (`leva`, `seguidor`, `pista`, `actuador`,
  `envolvente`, `cartucho`); todo lo demás, en inglés. Consistencia por encima de
  la preferencia personal.
- Hay **dos `Trazo`** y no son lo mismo: `core.escritura.Trazo` es un trazo de
  escritura, con el lápiz apoyado; `emit.layout.Trazo` es una primitiva de
  dibujo. Nunca se cruzan en el mismo módulo, y las dos son la palabra correcta.
- Nombres de los núcleos como en el baseline: `C1`…`C10` aparecen en docstrings
  para que se pueda rastrear qué implementa qué.
- Tipos en todas las firmas públicas. `mypy` estricto en `core/`.
- Los comentarios explican **por qué**, no qué. El qué se lee en el código.
- Errores de dominio con excepciones propias en `core/errors.py`. Un fallo de
  envolvente **no** es una excepción: es un `Veredicto` con motivo y sugerencia.
- Las excepciones se llaman `ErrorDeAlgo`, con la palabra delante, como en
  castellano. `core/errors.py` lleva por eso una excepción declarada a la regla
  N818 de ruff; está documentada en `pyproject.toml`.
- Datos medidos (kerf, desgaste, fidelidad, potencia) van en `bench/`, versionados
  y con fecha. Nunca incrustados en el código.

---

## Tests

- `tests/core/` — unitarios y de propiedad (hypothesis). Obligatorios:
  cierre periódico del perfil, continuidad C², invarianza a la velocidad de giro,
  idempotencia de la compilación.
- `tests/golden/` — comparación byte a byte contra referencias guardadas.
  `test_dxf.py` vigila el **escritor** con una leva sintética;
  `test_compilado.py` vigila la **geometría que sale del compilador**, con los
  **seis** casos de referencia de `tests/casos.py` —uno de ellos una frase
  que no cabe—. Hacen falta los dos: el primero no habría cazado ningún
  cambio del front-end de escritura.

  Los cuatro primeros son escrituras hechas a mano y **son anteriores a la
  fuente**: aguantan una caja de 90 mm donde «Arrels» tecleada rompe a 88,
  así que no representan el camino del que salen hoy los pedidos. Por eso
  hay dos tecleados: `tecleada` («Arrels») y `alta` («hola», que es la que
  tiene la curvatura más justa y la que juzga un formato).
- `tests/bench/` — contrasta la predicción del núcleo con las medidas reales del
  banco de ensayo. Si esto falla, el modelo miente.

---

## Trampas conocidas

- **Escalado de impresora.** Todo PDF 1:1 lleva cuadro de calibración. Sin
  excepción, y también cuando hay perfil aplicado: compensar no es verificar.
- **Medir con lo que no resuelve.** El instrumento tiene que ser más fino que el
  error que se busca. Con cinta métrica el patrón va a 250 mm; con pie de rey
  bastan 150. Nunca se calibra midiendo el cuadro de 100.
- **Recortar un rótulo obligatorio.** Si el texto no cabe, se envuelve o se
  reserva más sitio; nunca se corta. Un espesor que no aparece obliga a
  preguntar a alguien que está en otro taller y en otro momento.
- **Poner una marca justo donde hay un número.** La banda del medio de la hoja
  patrón cae al 55 % y no al 50 % porque la mitad de 200 son 100, que es una
  cota rotulada, y la marca le pasaba por encima.
- **Splines en software de láser.** Exporta polilínea densa o arcos.
- **`TEXT` de DXF en un CAD.** No es una entidad de boceto: Onshape importa la
  geometría bien y suelta un «no se ha podido importar la entidad desconocida»
  por el rótulo de metadatos. Para el taller el rótulo se queda; para importar
  a un CAD, `--dxf-para-cad`.
- **DXF determinista.** Un DXF lleva fecha y dos identificadores aleatorios, y
  además declara sus clases recorriendo un **conjunto**, que en Python no tiene
  orden estable entre procesos. Salía idéntico dentro de una ejecución y
  distinto en la siguiente: los tests pasaban y el golden fallaba. `emit/dxf.py`
  fija las dos cosas.
- **Ángulo absoluto del brazo frente a desviación del seguidor.** La leva se
  sintetiza para lo que se **desvía** el seguidor de su punto de diseño, no para
  el ángulo al que trabaja el brazo. El brazo derecho del escribiente ronda los
  -177°: metido tal cual en la síntesis, la leva se diseña a un cuarto de vuelta
  de donde va a trabajar y el ángulo de presión calculado no es el real. La
  diferencia es el **calaje**, y va en el dossier.
- **Cuota de la API de Onshape.** Es anual, no por minuto. Una llamada por pedido.
- **El CAD pide lo que la ficha no guarda.** La ficha de un engranaje guarda
  el **diámetro exterior**, que es lo que se comprueba con el pie de rey
  sobre la pieza que llega. El FeatureScript de engranaje de Onshape pide el
  **número de dientes**. Si la hoja de bocetos no lo trae, hay que despejar
  `Z = da/m - 2` de cabeza rellenando un formulario, y así salió un piñón de
  **25 dientes en vez de 20**: engrana a 2,4 en lugar de 3 y pide un
  entre-ejes de 29,75 en vez de 28. No avisa nadie —el engranaje sale bonito—
  y se descubre con las dos piezas en la mano.

  `PiezaComercial.dientes` hace la cuenta una vez; el CSV, la hoja de bocetos
  y el test del catálogo la leen de ahí. La regla general: **en la hoja va lo
  que se teclea, no lo que se mide**, y cuando no coinciden, el derivado sale
  también.
- **Renombrar una cota DESPUÉS de entregarla rompe el croquis en silencio.**
  Entregué `seguidor_sector_lejos`, se importó y se acotó con ella, y a la
  vuelta siguiente la renombré a `union_sector_seguidor_lejos` —correcto: la
  miden las dos piezas—. El croquis siguió viéndose bien hasta que se abrió y
  salió la cota en rojo.

  **Un alta no cuesta nada y un renombrado cuesta reteclear**, así que no son
  el mismo renglón del informe: `csv_pendientes` empareja por valor lo que se
  va con lo que llega y lo nombra «RENOMBRADA». Y el informe solo ve lo que
  `docs/importado.json` tenga marcado: si se importa y no se marca, las bajas
  no aparecen y son justo las peligrosas.

  La regla: **el nombre se discute antes de entregar la cota, no después.**
  Una vez entregada, renombrarla es una operación con coste para el que
  dibuja, y hay que decirlo al entregar el CSV.

- **El gemelo no sirve de nada si la hoja rotula el otro.** Los dos gemelos
  del cabestrante existían desde hacía días, y aun así el sector y el tambor
  se dibujaron **los dos a la mitad el mismo día**: la hoja ponía
  `#cota.amplificador_sector_radio_mecanizado`, que vale 47,975 y es un radio,
  y la herramienta de círculo acota el diámetro. Lo que se teclea es lo que la
  hoja pone, no lo que el CSV ofrece.

  Así que la regla no es «que exista el gemelo», es **que ninguna hoja rotule
  el radio de un círculo entero**, y eso se comprueba cruzando cada hoja
  contra el perfil de su pieza, no leyéndola. Y una pieza **sin perfil no se
  cruza con nada**: estas dos estaban fuera del bucle «porque son discos», y
  ese fue el agujero por el que entró todo lo demás.

  Al escribir ese test volvió a salir la trampa de más abajo: la primera
  versión emparejaba cota y rasgo **por valor contra todo el contrato** y
  acusó a `brazo_espesor` —que vale 3, igual que el radio del agujero del
  perno— de ser un radio mal rotulado. Va contra la ficha de la pieza.

- **Un rótulo correcto puesto en el sitio equivocado miente, y el dibujo se
  ve bien.** La hoja de la mordaza sacaba el «R2» de la ranura con la
  directriz de largo fijo, 9 px, y lo dejaba a 18 px del «Ø3» del datum:
  **más cerca del agujero que no describe que del que sí**. Los dos números
  eran correctos, cada uno tenía su flecha, y el croquis salió con el Ø4 en
  el datum y el Ø3 en la ranura.

  No lo caza mirar el dibujo; hay que montar la caja de cada rótulo y medir
  si solapa con las demás, que es lo que hace
  `test_dos_rotulos_de_la_banda_de_arriba_no_se_tapan`. Encontró de paso un
  segundo caso que nadie había visto, el «R5» del brazo proximal escrito
  sobre un nombre de variable.

  Los rótulos de radio van ahora a una banda **encima** de la planta, con
  `alto_de_leyenda` reservando el sitio: abajo está la pila de cotas
  horizontales y un radio que la cruza se lee como parte de ella.

- **Un patrón circular se acota por su circunferencia, y esa va en
  diámetro.** `volante_aligeramiento_al_centro` vale 30 y no lleva «radio»
  ni «diametro» en el nombre, así que no sacaba gemelo: en el campo del CAD
  —que pide **Ø60**— no había nada que teclear. Lo vio quien dibujaba, con
  la pieza medio hecha.

  Es la misma familia que el canto del sector, pero el arreglo no puede ser
  el de entonces —renombrar— porque la cota ya estaba entregada. Lo que sabe
  que esa distancia es una circunferencia no es el nombre, es la **ficha**:
  declara el patrón en `polares`, y `circunferencias_de_taladros()` saca de
  ahí quién necesita gemelo. Con un solo agujero no hay patrón: se acota la
  distancia y un diámetro sería un número que no mide nada.

- **Dimensionar sobre el demo.** El volante salió de `demo/hola.json` y se
  habría quedado un **tercio corto**: «firma», que es un trazo cursivo
  largo, pide 3,62 × 10⁻⁴ kg·m² contra los 2,28 de «hola». Los casos de
  referencia de `tests/casos.py` existen justo para esto —cada uno tensa una
  cosa distinta— y una cota que depende del pedido se dimensiona contra
  **todos**, no contra el que se tiene abierto.

  Lo mismo valió para el precio: `bench/precios.json` presupuestaba una
  rodaja de latón de Ø50 que da el **20 %** de la inercia que hace falta. Un
  precio puesto sobre una pieza que nadie había calculado.

- **Dos agujeros cambiados de sitio se ven perfectos.** La platina volvió
  dos veces con el tercer poste y el pivote izquierdo cada uno en el sitio
  del otro: el Ø8 a -58,407° y el Ø10 a -120°, cuando era al revés. Cada
  agujero llevaba su radio y su diámetro correctos, así que no había nada
  raro que mirar —seis agujeros en un disco, todos redondos y todos del
  tamaño que toca—, y la segunda vez volvió igual después de corregir otra
  cosa.

  Lo que lo invitaba: a 0,62:1 un Ø8 y un Ø10 se distinguen en un píxel, y
  la hoja ponía los diámetros en una leyenda y las polares en otra, así que
  **nada decía qué agujero era cada uno**. Ahora el rótulo de cada grupo
  polar lleva su diámetro delante: «Ø8 · 71,063 · 3× 120°».

  Y el informe dice **qué hay en su lugar**, no solo que falta: «pide el 3
  de 3, un centro a 71,0634 y 240°, y lo más cerca hay un Ø10 a 2,85 mm».
  Con «el peor se queda a 2,85 mm» hay que reconstruir a mano cuál de los
  cuatro agujeros es.

- **Un ángulo negativo no se puede teclear.** La herramienta de ángulo mide
  una magnitud: `#angulo.platina_pivote_angulo_izquierdo` vale -58,407 y el
  campo se pone en rojo. Quitarle el signo a mano sí entra, y entonces el
  agujero se va al otro lado del eje X —la pieza espejada, que se ve igual
  de bien—.

  Es el gemelo del diámetro con otra cara, y se resuelve igual: cada ángulo
  negativo saca un `…_positivo` con la magnitud, y la hoja rotula ese y dice
  el lado («bajo +X»). Lo cierra
  `test_ninguna_hoja_rotula_un_angulo_negativo`.

  **Solo para lo que va al croquis.** Un calaje es negativo y se queda así:
  no se acota, se monta, y el campo de ángulo de un emparejamiento sí acepta
  el signo. Darle la magnitud y una nota en prosa sería peor que darle el
  número.

- **El test medía las cajas de los rótulos donde el dibujo no las pone.** La
  hoja de estilo le gana a un atributo de presentación, así que
  `.cotatx{text-anchor:middle}` se comía el `text-anchor="end"` que `radial`
  escribía en cada rótulo: el número salía **centrado** en el final de la
  directriz y se extendía hacia dentro de la pieza, encima del rasgo que
  describe. Y `caja_del_rotulo` y el test de solapes sí leían el atributo, de
  modo que la comprobación escrita para cazar un rótulo mal puesto estaba
  midiendo otro sitio: pasaba con los rótulos montados.

  Salió dibujando la platina, porque es la primera pieza con cotas a los dos
  lados de la planta y el desplazamiento se veía. El anclaje va ahora en
  `style`, y el test se niega a leer uno puesto por atributo.

  La lección general: **una comprobación que modela el render tiene que
  mirar lo que el render mira.** Si el modelo y el dibujo discrepan, el test
  no es que no cace nada, es que dice que todo está bien.

- **Rotular una variable que no existe.** Es la misma familia, y ha salido
  **tres veces**: los dientes que no estaban en la hoja, los dientes puestos
  en el mapa de milímetros, y `#pieza.tornilleria_longitud`, que el perfil
  dibuja con un valor por defecto porque la ficha no la declara —y por tanto
  tampoco está en el CSV—. Cada una se arregló sola y la siguiente apareció
  por otro lado.

  **Y una quinta por otro lado: un nombre que no dice que la cota es
  circular.** `brazo_ancho` y `amplificador_sector_agujero` miden un diámetro,
  pero sin «radio» ni «diametro» dentro el exportador no les sacaba gemelo, así
  que no había radio que teclear donde el CAD pide radio. Las dos se llaman
  ahora `…_diametro`. El nombre decide si la cota existe en la forma en que se
  usa.

  Lo cierra `test_toda_variable_que_la_hoja_de_bocetos_rotula_existe_en_el_csv`,
  que cruza los dos artefactos: cada `#mapa.variable` de la hoja tiene que
  estar en el CSV de ese mapa. Si no está, no hace falta saber por qué —no
  se puede teclear—. Lo que el perfil dibuja con un valor por defecto se
  rotula como hueco, con asterisco, y no como variable.

  **Y salió una cuarta, por tener el cruce solo en una hoja.** Las otras
  cuatro —las dos conceptuales y los dos planos— comprobaban sus variables
  contra `docs/contratos.json`, que no es lo que se importa: entre el
  contrato y el CSV hay un reparto por unidades que puede equivocar el
  prefijo sin equivocar el nombre. Al extender el cruce a todas, el primer
  fallo apareció solo: `dibujar_amplificador.py` seguía pidiendo
  `amplificador_sector_semiarco`, borrada del contrato dos commits antes.
  El script estaba roto y nadie lo ejecutaba.
  `test_toda_hoja_que_se_copia_rotula_variables_que_existen_en_los_csv` las
  cubre las cuatro, y de paso las ejecuta.
- **Un factor de conversión por archivo, así que un mapa por unidad.** Una
  importación de Onshape crea **una** variable de tipo mapa y aplica su
  factor a **todas** las filas. Por eso el paquete saca cinco CSV y no uno:
  `#cota` y `#pieza` en `1 mm`, `#angulo` en `1 deg`, `#num` y `#pieza_num`
  sin unidad. Los dientes de un engranaje no caben en `#pieza`: entrarían
  como veinte milímetros y el campo «número de dientes» no admite una
  longitud.

  El reparto lo declara `MAPAS` en `scripts/exportar_para_cad.py`, y lo leen
  los dos sitios que lo rotulan —la hoja de ruta del paquete y la hoja de
  bocetos—, para que no puedan contradecirse. Si la hoja dijera un prefijo
  que no existe, el que la copia se entera cuando el campo se pone en rojo,
  y eso con suerte.
- **Un CSV que se importa al Variable Studio no lleva cabecera.** El
  Variable Studio lee «todos los valores» sin saber que la primera fila es un
  rótulo, así que la cabecera entra en el mapa como una clave `nombre` cuyo
  valor es el texto `valor`. Con un factor de conversión puesto, multiplicar
  ese texto por `1 mm` **hace fallar la regeneración de la variable entera**,
  y el error que sale —«no se regeneró correctamente»— no menciona la
  cabecera por ningún lado. Por eso el paquete de CAD saca dos juegos: los
  `*_cota.csv`, `*_angulo.csv` y `*_num.csv` sin cabecera, para importar, y
  `variables.csv` y `piezas.csv` con ella, para leer.
- **El factor de conversión del Variable Studio sí acepta unidades.** Se
  escribe `1 mm` o `1 deg`, no un número pelado, y entonces el mapa sale con
  magnitudes y en el croquis se acota con `#cota.radio_base` a secas. Con un
  número el mapa queda adimensional y la cota la interpreta Onshape en la
  unidad por defecto del documento: funciona hasta que alguien cambia esa
  preferencia y el bastidor pasa a medir 55 pulgadas sin un solo aviso.
- **La mitad de las cotas circulares son radios y la otra mitad diámetros, y
  el CAD acota en diámetro por defecto.** De las siete cotas circulares del
  contrato, cuatro son radio —`radio_base`, `pasador_radio`,
  `poste_radio_al_arbol`, `rodillo_radio`— y tres diámetro —`eje_diametro`,
  `pasador_diametro`, `poste_diametro`—. La herramienta de círculo de Onshape
  acota el **diámetro**, así que meter `#cota.radio_base` ahí da una leva de
  27,5 mm de radio en vez de 55: **la mitad, y sin un solo aviso**. Pasó en la
  primera prueba.

  Resuelto en el exportador: `con_gemelos` saca las dos formas de cada cota
  circular —`radio_base` 55 y `radio_base_diametro` 110, `eje_diametro` 10 y
  `eje_diametro_radio` 5—, así que se escribe la que pida el campo y no hay
  nada que multiplicar ni que recordar. Son siete filas de más. Cambiar la
  cota a radio con el botón derecho también valdría, pero eso es disciplina,
  y la disciplina falla una vez de cada veinte. Es el patrón del pasador de
  índice: no hacer el error improbable, hacerlo imposible.

  El gemelo lleva «derivada de …» en la descripción, para que nadie lo
  corrija a mano creyendo que es una cota del contrato.
- **Un CSV escrito pegando comas se rompe con el primer campo que lleve una.**
  La tolerancia del pasador de índice es «m6 en el plato metálico, deslizante
  en el POM». Sin comillas parte la fila en dos columnas de más, y no se ve
  porque las dos primeras —las que el CAD lee— quedan en su sitio. Se escribe
  con el módulo `csv`.
- **Mezclar precios con y sin IVA.** Medio catálogo español cotiza con IVA y
  los alemanes en neto. Sumados tal cual, el error es del 21 % en la parte
  que no se ve. En `bench/precios.json` cada línea declara `iva_incluido` y
  `compile/coste.py` lo normaliza. Se suma **con** IVA porque Arrels no lo
  repercute: el IVA soportado es coste, no un anticipo que se recupera.
- **Presupuestar el corte con el perímetro de la pieza.** La fresa va por
  fuera, desplazada su radio: en una curva cerrada eso alarga el camino en
  2·π·r_fresa exactamente. Y lo que manda no es el tiempo de corte, que son
  minutos, sino la **preparación**: las tres levas en un amarre cuestan la
  mitad que en tres.
- **Confundir una previsión con un precio.** El corte de las levas está
  externalizado a **precio cerrado por bloque**, y el número que hay puesto
  es nuestro, no de un taller: `PrecioCerrado.cerrado` es `False` y tanto el
  informe como el CLI lo rotulan «previsión». Cuando llegue el presupuesto,
  se cambia el importe, se pone el proveedor y se pasa a `true`. El cálculo
  por tarifa sigue ahí, y no es lo que se paga: es la vara para saber si un
  presupuesto es caro.
- **Unidades.** El bug más caro y el más fácil de cometer. Usa `core/units.py`.
  Cada magnitud lleva el rango más estrecho que sea plausible: `Longitud` llega
  a diez metros y por eso un espesor usa `Espesor`, que se queda en cien
  milímetros. Un rango ancho no caza el error de magnitud.
- **Sustituir texto en un fichero que `ruff format` ha tocado.** Si la
  sustitución no coincide, falla en silencio y parece aplicada. Lee el fichero
  antes de editarlo.
- **Ramas de la cinemática inversa.** Un varillaje tiene dos soluciones por punto.
  Elige una y mantenla en todo el ciclo, o la leva saldrá con un salto.
- **Offset con autointersección.** Si el radio de curvatura es menor que el del
  rodillo, el offset se cruza consigo mismo. Detéctalo: es undercutting, y la
  pieza no se puede fabricar.
- **Acortar una tangente para que la curva no se abombe rompe la continuidad
  C1, y eso es peor que el abombamiento.** El vuelo tenía las tangentes
  topadas a una vez y media el salto, para que la Hermite no formara un lazo.
  El tope disparaba en un solo empalme de «hola» —el lazo de la «o», cuyo
  salto al trazo anterior es corto— y dejaba la velocidad de aterrizaje un
  **5,4 %** por debajo de la que traía el trazo. Un codo de esos se le hereda
  a la leva como un escalón de curvatura: el radio mínimo que mide la
  envolvente pasaba de 15,6 a **9,2 mm** en cuanto el muestreo lo resolvía.

  Y el lazo que el tope evitaba no era un problema: el lápiz va levantado
  durante todo el vuelo. **Un lazo no es una cúspide**, la velocidad no se
  anula. Lo defiende `test_el_vuelo_aterriza_a_la_misma_velocidad_a_la_que_
  arranca_el_trazo`, que mide el desajuste en cada empalme y no en la pista
  muestreada: a un lado y otro del empalme el paso es el mismo, así que una
  diferencia finita no distingue un salto del 5 % del redondeo.

- **Una esquina de la polilínea es curvatura infinita, y sin redondearla
  ningún veredicto de curvatura significa nada.** Con «hola», al doblar las
  muestras el radio de curvatura mínimo del peor perfil iba 13,5 → 7,5 → 4,4
  → 1,9 mm: **se dividía por dos cada vez**, que no es un mínimo sino una
  esquina que el muestreo redondeaba por accidente. `Capacidad.
  radio_de_esquina` la redondea a un radio declarado, 1 mm por defecto, y el
  número se queda en 13,0 (relación 720/5760 de 1,04).

  **El radio tiene que ser varios pasos de muestreo.** La leva se corta como
  un polígono de `muestras` puntos; a 720 la punta avanza 0,26 mm por
  muestra, así que un arco de 0,2 mm no recibe ni una muestra entera y el
  redondeo existe en el modelo pero no en la pieza. Por eso 0,2 y 0,3 mm
  apenas mejoran y 1,0 sí.

- **`interpolar` se pasa de largo con una polilínea escasa, y no lo veía
  nadie.** Es una cúbica natural por los puntos capturados: con cinco puntos
  desiguales sobrepasa la polilínea **3,7 mm** en «hola», treinta veces el
  error de trazo que se citaba. Era invisible porque la simulación compara el
  recorrido de las levas contra el programa, que está hecho con esa misma
  interpolación: se comparaba consigo misma. Lo mide ahora
  `desviacion_de_lo_capturado`, y redondear las esquinas lo arregla de paso
  porque densifica el trazo donde gira.

- **`radio_de_curvatura` amplifica por 1/h² cualquier salto de curvatura.**
  Toma dos diferencias finitas de la curva de paso muestreada con paso
  h = 2π/N, así que en un punto donde la curvatura da un escalón lee un pico
  de tres muestras cada vez más profundo según sube N. Con la leva izquierda
  a 20.000 muestras marcaba 9,2 mm donde la curvatura real vale 39,9 a un
  lado y 56,9 al otro: **ese radio no existe en ningún punto de la pieza**.
  Evaluando con paso físico fijo el número se queda quieto (17,502 mm a
  cualquier N), y eso es lo que distingue un defecto de geometría de uno de
  medida. Antes de rediseñar nada por un radio que se desploma, comprueba
  cuál de los dos es.

- **Diagnosticar por la nota de ayer en vez de por la medida de hoy.** Esta
  investigación estuvo parada un día sobre un diagnóstico escrito con
  seguridad y falso: que el vuelo formaba una **cúspide**. No la formaba
  —|dP/dθ| vale 1,79 mm/rad en el punto malo y no se anula— y la cúspide
  llevó a diseñar una quíntica con curvatura impuesta que, una vez medida, no
  cambiaba **ni un dígito**. El fallo estaba en otro sitio y en otra capa: el
  trazo, no el vuelo. Cuando una nota diga «localizado», vuelve a medirlo.
- **Un golden de una pieza sintética no vigila el compilador.** El de
  `tests/emit/test_dxf.py` guarda una leva sintética: mira el escritor de DXF
  y no la geometría que sale de compilar un pedido. Con solo ese golden, el
  front-end de escritura cambió **dos veces** —el arreglo del vuelo y el
  redondeo de esquinas— moviendo los tres perfiles de `demo/hola.json` sin
  que saltara ninguna comparación byte a byte, y E5 daba por cumplido un
  criterio que pedía «los DXF de los casos de referencia».

  Lo cubre `tests/golden/test_compilado.py` con **cuatro** casos
  (`tests/casos.py`), uno de ellos una frase que no cabe, para que el camino
  del veredicto negativo también esté vigilado. Guarda el sha256 de cada DXF
  **y los números de cabecera**: un golden que solo dice «ha cambiado»
  obliga a reconstruir el porqué a mano, y con los números el fallo dice
  «error_trazo_mm pasa de 0,0676 a 0,0675».
- **El error de la transmisión no lo divide la relación, y el del canto sí.**
  El error de perfil nace en la leva, antes del amplificador, así que lo
  atraviesa; el juego del amplificador nace dentro y ya está medido en el
  lado del brazo. Meterlo por el mismo sitio lo equivoca por el factor
  entero, que aquí son **seis veces**. Lo pinchan dos tests, uno en `core` y
  otro en `compile`.

  Y ahí la palanca a la punta son **172,5 mm**, no los 90 del brazo
  proximal, así que el mecanismo del amplificador decide más de lo que
  parece: un par de engranajes de calidad 8d llevaba el peor caso de 2,84 a
  **6,74 mm** y el coste de 119 a 309 €. Por eso es un cabestrante de cinta:
  una cinta anclada por los dos extremos no tiene juego, solo elasticidad, y
  son 0,092 mm.
- **La correa sale por donde el radio es perpendicular a ella, y abraza el
  lado de enfrente.** Dos cosas distintas que se confunden:

  El punto de tangencia cumple `cos t = (R−r)/a`, así que en el cabestrante
  cae a **54°** de la línea de centros, del lado del tambor. Y de los dos
  arcos que separan los dos puntos de tangencia, el que la cinta abraza es
  el de **252°**, que pasa por el lado **opuesto**. Lo confirma la fórmula
  de correa abierta, `π + 2γ` con `sin γ = (R−r)/a`.

  Así que la cinta toca el canto del lado contrario al tambor, y los
  anclajes van justo por fuera de los dos puntos de tangencia. El sector,
  al final, es un **disco entero**: la muesca en el lado libre no daba
  holgura a nada —el ramal sale tangente y se aleja— y le ponía orientación
  a una pieza que, siendo un disco con un agujero, no la tiene.

  **Esto se escribió mal dos veces seguidas.** Primero con el seno en vez
  del coseno, que ponía la tangencia a 126°; después se «corrigió» poniendo
  el material en el lado libre, que es donde la cinta no toca. Las dos veces
  razonando sobre el dibujo en vez de imponer la perpendicularidad y
  resolver. La segunda llegó a entrar en este archivo como trampa, con el
  número equivocado. Lo caza ahora
  `test_la_cinta_abraza_el_lado_opuesto_al_tambor`, que comprueba las dos
  cosas por caminos distintos.
- **Un croquis importado llega exacto y suelto, y eso se ve bien.** Un DXF no
  lleva restricciones, y las cotas de la pieza no quitan los tres grados de
  libertad del plano: una barra acotada de 90 puede estar en cualquier sitio y
  a cualquier ángulo. Lo que el archivo sí puede aportar es el **sitio**: el
  rasgo datum en el origen y el centro siguiente sobre +X dejan el anclaje en
  dos coincidentes, los dos enganchados a geometría que ya está dibujada. El
  datum es un agujero y no el centro de la pieza porque un punto medio hay que
  construirlo, y lo que hay que construir se olvida. `FICHAS` en
  `scripts/comparar_dxf.py` lo declara por pieza; el bucle entero está en
  `docs/metodologia.md` §2d.

  **El comparador no lo caza**: un croquis exacto y suelto lo pasa entero. Ese
  paso es de la persona, mirando que Onshape diga «totalmente definida», y el
  informe lo recuerda cada vez.
- **Una cuerda no sitúa una cara plana.** En un agujero de Ø10 una cuerda de
  6 cae a 4 del centro, pero puede caer a **+4 o a -4**, y con la cara mirando
  al lado contrario el brazo se cala media vuelta girado: la misma pieza en el
  croquis y otra distinta montada. El comparador lo dejaba pasar, y lo enseñó
  el cruce entre `emit.plataforma.LISTADO` y `FICHAS`: el listado decía que
  `brazo_chaveta` se teclea y la ficha no la miraba nadie. Ahora se comprueba
  **con signo**.

  La lección general es la del cruce, no la de la cota: dos listas que
  describen lo mismo desde lados distintos se contrastan, y lo que aparece en
  una y falta en la otra es siempre algo.
- **Comparar contra el contrato entero no comprueba nada.** Con ochenta cotas,
  cualquier número redondo encuentra una que lo explique: la primera versión de
  `comparar_dxf.py` daba por bueno un radio de 6 en un brazo citando el ancho
  del tambor del cabestrante. Por eso se compara contra la **ficha de la
  pieza**, que declara qué rasgos tiene y con qué recuento —el distal tiene DOS
  cubos de 6, y uno solo sería otra pieza—. Así un rasgo que falta y uno que
  sobra son fallos distintos.
- **El calaje vive en la mordaza de la cinta, no mecanizado en el eje.** La
  cinta entra al tambor por R8 y el brazo mueve la punta con 172,5 de palanca:
  **1 mm de error en la longitud libre son 21,6 mm en la punta**, y un fleje
  anclado a mano no tiene esa longitud a la décima. Mecanizado, ese error sería
  invisible y permanente; en una ranura es visible y se corrige, y lo verifica
  la hoja de trazo patrón, que ya existía para eso.

  Consecuencia: el eje de pivote es una barra Ø10 h6 con una cara plana, igual
  en los tres sitios. Decidido en `docs/contratos.md`.
- **Una cinta no se arrolla a menos de cien veces su espesor**, así que con un
  fleje de 0,05 el radio mínimo son 5 mm. Eso descarta el pasador de arrastre
  pequeño que sería lo natural en un anclaje —tendría que ser de Ø10— y obliga
  a que la mordaza agarre por **rozamiento**. No es una pérdida: un M3 a
  0,3 N·m da 188 N contra una carga de unos pocos newton.
- **Un tensor de tornillo no puede tensar una cinta de acero.** Estirarla a 5 N
  son **5,8 µm**, y calar el brazo ±10° pide **1,4 mm** de recorrido: 241 a 1.
  Una vuelta de un M3 son 500 µm, o sea pasar de nada a 430 N. Y meter un
  muelle en serie devuelve la flexibilidad por la que se descartaron los
  engranajes. Lo que sí sirve es separar las dos cosas: la **ranura** da los
  milímetros, el **apriete** da las micras.
- **Comprobar cada rasgo contra el contorno no dice nada de los rasgos entre
  ellos.** La mordaza tenía un test que medía la pared de cada agujero contra
  los bordes del bloque, y ninguno que los mirara **entre sí**: entre el
  agujero de apriete y el principio de la ranura quedaban **1,5 mm** donde el
  propio contrato pide 3. El dibujo lo enseñaba acotado y nada protestaba.

  Lo encontró quien estaba dibujando la pieza, no el repo. Hacen falta las dos
  comprobaciones, y la de rasgos entre sí se escribe a mano: la ranura son dos
  arcos que no se tocan, y lo que hay entre ellos es la ranura y no una pared,
  así que deducir los tramos del perfil se equivoca.
- **Un datum que no está en el centro mueve el dibujo entero, y la hoja
  sigue saliendo.** La planta de una hoja se coloca por su `(0, 0)` de
  pieza, pero el alto reservado se medía contra la **semicaja**, como si el
  datum estuviera siempre centrado. En una barra, un disco o la mordaza lo
  está —son simétricos respecto de su datum— así que las dos cuentas daban
  lo mismo y la diferencia no existía. La base es la primera que no lo es:
  su datum es un poste y queda a 59 de un borde y a 216 del otro, así que
  la planta subía **43 mm** sobre su sitio, el segundo renglón de la
  leyenda salía escrito encima del borde de la tabla y abajo quedaba un
  hueco igual de grande.

  Es la familia del `text-anchor`: una comprobación que modela el render
  tiene que **mirar lo que el render mira**. Lo cierra
  `test_la_leyenda_de_arriba_no_se_mete_dentro_del_dibujo`, que lee el SVG
  y no las variables que lo colocan, y distingue los renglones de leyenda
  de los rótulos de cota porque solo los primeros llevan flecha.

- **Emparejar por valor funciona hasta que hay dos candidatos.** El informe
  de reimportación llama RENOMBRADA a la cota que se va y a la que llega
  con el mismo número. Al cerrar la base, `poste_diametro` (15) se renombró
  a `poste_obstaculo_diametro` y en el mismo paquete entró
  `base_poste_empotrado`, que también vale 15: emparejó la alfabéticamente
  primera y mandó reteclear dos cotas que no tienen nada que ver.

  **Mandar a reteclear una cota que está bien es peor que no decir nada**,
  porque el que dibuja va al croquis, no encuentra nada roto y a la
  siguiente deja de leer el renglón. Con una sola candidata el valor
  decide, como antes; con varias manda el nombre —palabras en común y
  luego prefijo— y si ninguna comparte una palabra no se elige ninguna.

- **Acotar contra un círculo da el canto, no el centro.** La herramienta de
  distancia del CAD mide lo más corto entre los dos rasgos que se pinchan,
  así que un círculo contra una línea da la **pared** del agujero y no su
  eje. La base volvió con el contorno corrido **4,0000 mm** —exactamente el
  radio del Ø8 del datum— en los dos bordes de Y, mientras el de X, acotado
  al punto central, salía clavado. El dibujo se ve impecable: el rectángulo
  mide sus 190 × 275 y los tres agujeros están en su triángulo; lo único
  movido es dónde cae uno respecto del otro.

  Es la familia del radio contra el diámetro: **el campo acepta un número
  razonable y no hay nada que mirar**. Hay que pinchar el PUNTO central, y
  por eso `voladizo`, `retranqueo` y `desde_datum` rotulan ahora «al CENTRO
  del datum» en la propia cota, donde se lee al teclearla y no en una nota
  al pie.

- **Un lazo cinemático cerrado montado todo con revolutes sale en rojo, y el
  mensaje no señala al culpable.** El cinco barras tiene cinco articulaciones
  y Onshape intenta satisfacerlas todas a la vez: un lazo plano con revolutes
  es redundante y solo consistente si la geometría es exacta hasta el último
  bit. Como no lo es, sale `Mate overdefines the assembly`, a veces sobre
  varios emparejamientos a la vez.

  La receta es del propio personal de Onshape, repetida en cuatro hilos:
  **el emparejamiento que CIERRA el lazo se pone cilíndrico**, nunca de
  revolución. El cilíndrico libera `Tz`, que es donde se acumula el desajuste
  fuera del plano; la articulación sigue girando igual. Aquí es el perno de
  la punta, y además es físicamente cierto: los dos distales trabajan en
  planos separados un milímetro.

  Y los emparejamientos del lazo se ponen **de uno en uno**, dejando el que
  cierra para el final. Si no, el rojo aparece sobre un grupo y hay que
  suprimir candidatos a ciegas para aislarlo. Onshape no tiene contador
  numérico de grados de libertad, solo un icono.

- **Onshape no detecta colisiones al moverse, así que el hueco al poste no lo
  vigila nadie.** No hay contacto, ni rodadura, ni parada al chocar: la
  relación de engranaje es, en palabras del blog oficial, *«a mathematical
  link»*. `Interference Detection` existe pero es **estática**, mira la
  posición de ahora. El hueco de 11,3 mm se comprueba congelando θ con
  **mate values** —`J`, doble clic sobre el valor, teclear— y repitiendo en
  una rejilla de ángulos. El número continuo lo sigue dando
  `compile/conjunto.py`.

  La misma familia: los límites de emparejamiento **no aceptan variables**,
  así que un tope del contrato se teclea a mano o no existe. Y Simulation
  excluye justo lo que mueve esta máquina —tangentes y **las cuatro**
  relaciones—, de modo que el conjunto que se mueve no es el que se simula.

  El plan entero está en `docs/ensamblaje.md`.

- **Un archivo que declara una unidad y lleva otra dentro se ve
  perfecto.** Las catorce envolventes del catálogo salían **mil veces
  pequeñas**: `emit/catalogo.py` construía el sólido con las cotas en
  metros —el poste con radio 0,004 y largo 0,195— y `export_step` escribía
  una cabecera que declara `SI_UNIT(.MILLI.,.METRE.)`. Es la regla 3 rota
  en un emisor, y el ayudante que debía cruzar la frontera se llamaba
  `_mm` y devolvía metros: **el nombre decía que convertía y no
  convertía**.

  Lo grave es por qué sobrevivió días con tres tests encima:

  1. `caja_envolvente` devolvía metros y se comparaba contra la ficha, que
     también está en metros. **Metros contra metros: el factor se cancela.**
  2. El test de ida y vuelta pasa por `import_step`, que **comete el mismo
     error que el exportador**. Escribe y relee el mismo número y la
     cabecera le da igual. Dos caminos que comparten la equivocación no son
     dos caminos.
  3. `uv run pytest` **desinstala build123d** —el grupo `cad` no entra en
     el sync por defecto— así que el módulo entero se saltaba con
     `importorskip` y nadie leía el aviso. Para que corran: `uv run
     --group cad pytest`.

  Y sobre todo: **nadie había abierto nunca uno de esos STEP.** Se generan,
  se guardan y se arrastran al CAD. Un visor en el bucle lo caza el primer
  día.

  Lo cierra `test_el_step_mide_lo_mismo_leido_con_la_unidad_que_declara`,
  que lee el archivo **como texto**, saca el prefijo de `LENGTH_UNIT` y
  cruza la mayor coordenada contra la envolvente. Es la familia del
  `text-anchor`: una comprobación que modela al lector tiene que leer como
  lee él, no como escribe quien escribió. Cuidado al escribirla: un punto
  del espacio de parámetros de una superficie también es un
  `CARTESIAN_POINT`, y el de una circunferencia llega a 2π, así que un
  cilindro de Ø6 parecía medir 6,283. Solo valen los de tres componentes.

  `emit/step.py` —el cartucho— **nunca tuvo el fallo**: usa `a_mm` de
  `core/units.py` y lo dice en el docstring. Ahora el catálogo usa el
  mismo.

- **`connect_to()` de build123d construye un ÁRBOL, no un grafo.** Coloca
  el hijo respecto del padre y no reconcilia dos caminos que llegan al
  mismo sitio: no hay solucionador. De esta máquina no cabe **ninguna** de
  las tres cosas que la definen —el cinco barras es un lazo cerrado, el
  contacto leva-rodillo no es una articulación y no existe `CamJoint`, y
  el cabestrante es una relación entre dos giros—. Lo que sí cabe es una
  cadena abierta: `poste → seguidor → sector`, `eje_pivote → tambor →
  brazo`.

  Así que **el compilador es el solucionador**, y no por falta de otro:
  es la regla 1 y la regla 2. La cinemática vive en `core/`, pura y en θ;
  `emit/montaje.py` solo **coloca**. Un solucionador en un emisor sería
  cinemática fuera del núcleo.

- **La distancia exacta entre dos sólidos de OCCT es lo caro de un
  barrido.** Diecinueve piezas dan unos ciento setenta pares móviles, y a
  veinticuatro ángulos eso es media hora: un test que se desactiva. Dos
  cosas lo dejan en segundos y las dos hacen falta: **construir cada
  sólido una vez** y recolocarlo —si no, cada ángulo vuelve a extruir las
  mismas planchas— y **filtrar por cajas envolventes** antes de pedir la
  distancia exacta.

  Y un barrido de todos contra todos **no significa nada sin declarar qué
  puede tocarse**: el poste atraviesa el agujero del plato por diseño, el
  árbol atraviesa las tres levas. Decir «nada se toca» es falso. Por eso
  el test va contra una lista corta de pares que de verdad no deben
  acercarse, y la tabla general de interfaces se queda para la máquina 2.

- **`_psi_desde_la_leva` no se puede llamar con un solo ángulo.**
  Reconstruye el spline de la curva de paso con **tantos nudos como
  ángulos se le pidan**, así que pedir uno da «hacen falta al menos 8
  muestras» y no la máquina en ese ángulo. `compile.conjunto.estados`
  toma la rejilla entera de golpe, y `piezas_en` redondea a grado para
  poder enseñar una posición suelta.

- **Una imagen no es un trazo, y una fuente normal tampoco.** El
  compilador quiere `Escritura`: trazos en orden, con el lápiz apoyado.
  Un canvas lo da; una imagen da píxeles y una fuente normal da
  **contornos** —la «o» son dos círculos cerrados y el trazo de la pluma
  es el anillo de en medio—. Pasar de ahí a una línea central pide
  esqueletizar, y en una escritura a mano además **ordenar los trazos**,
  que no tiene solución única: un lazo se recorre en los dos sentidos y
  en un cruce hay varias continuaciones plausibles.

  Por eso el camino barato no es el obvio: una **fuente monotrazo** ya
  trae las líneas centrales, dibujadas en 1967 para trazarlas con una
  pluma. De texto a leva no hace falta ni una línea de visión por
  computador.

- **Cada vuelo del lápiz se come grados de la vuelta, así que enlazar
  decide si una frase cabe.** En la Hershey cursiva los huecos entre
  trazos consecutivos de una palabra caen en dos grupos separados: de 0 a
  0,46 alturas de x —los enlaces que la letra inglesa ya trae— y de 0,8
  en adelante, que son levantadas de verdad. Medio es el valle, y es el
  `ENLACE` por defecto. Con enlace 0, «Arrels» sale en seis trazos y no
  cabe; con 0,5 sale en dos.

  **El techo medido está entre cinco y siete trazos**, y es más bajo de lo
  que parecía: «Arrels» (2) y «Juan Carlos» (5) caben; «Gracias» (7),
  «Montserrat» (10) y «Feliz cumpleanos» (10) no. Que no escriba
  «Montserrat» no es un caso raro de laboratorio, es el pedido probable.

  Y el deslizante de enlace **funciona demasiado bien**: a 1,1
  «Montserrat» pasa de diez trazos a tres y el vuelo baja de 187° a 90°,
  porque está uniendo siete huecos que la fuente declara levantadas.

  **Lo caro es que eso no se ve.** Medido: a 1,1 añade **64 mm de raya**
  que la letra no tiene, un 12 % más de tinta, y las dos capturas —a 0,5 y
  a 1,1— son indistinguibles a simple vista, porque los huecos forzados
  caen justo por donde el ojo espera que una cursiva enlace. Yo mismo había
  escrito aquí «la frase cabe porque ha dejado de ser la frase» y, al ir a
  enseñarlo, las dos imágenes salieron iguales: la afirmación era cierta y
  la comprobación, mirar, no la veía. Lo que la ve es medir la longitud
  añadida.

  Por eso el deslizante lleva una marca por cada hueco **de la frase
  escrita** —no del juego de caracteres— y la cuenta en milímetros de lo
  que se está inventando. Los huecos se miden entre los trazos crudos, así
  que **no se mueven al arrastrar**: `_enlazar` compara siempre contra el
  final del trazo crudo anterior, porque unir dos deja como final el del
  segundo.

  Y un hueco de **longitud cero se une siempre**, aunque el enlace sea 0.
  No es un enlace que la letra inglesa traiga: es el mismo recorrido de
  pluma guardado en dos trazos, que es como la fuente almacena una «n».
  Dejarlos sueltos hace levantar el lápiz y bajarlo en el mismo punto, 16°
  de la vuelta para dibujar lo mismo. Antes con enlace 0 salían separados,
  y «Arrels» pedía siete trazos donde cuatro dan la misma letra.

- **Un barrido que mueve dos cosas a la vez lee un patrón que no está.**
  Buscando hasta dónde puede crecer la caja de escritura, barrí ancho y
  alto juntos y salió limpísimo: 80 × 30 falla, 60 × 22 no, luego «el
  techo son unos 24 mm de alto escrito». Lo escribí con seguridad y es
  **falso**. Moviendo un eje cada vez, con «hola» tecleada una caja de
  75,7 × 30 falla y una de 85 × 33,7 —más grande en los dos lados— pasa.
  No hay umbral de tamaño.

  Lo que sí es monótono es la **relación de curvatura** de la leva: 2,34 a
  22 mm de alto, 2,13 a 24, 1,96 a 26, 1,07 a 30, 1,00 de 31 en adelante.
  Por debajo de 1 el rodillo no entra. Entre 28 y 30 el recorte de la
  envolvente **falla** y sale error; de 31 para arriba vuelve a funcionar y
  el veredicto dice «apto» con el rodillo justo sin entrar y la leva
  cortada. Ese «apto» es un filo, no un formato entregable.

  De ahí que el listón del catálogo no sea `apto` sino **que no haya que
  recortar ninguna leva**: una leva recortada escribe la letra redondeada y
  cuánto solo sale de recorrerla, así que ofrecer un formato que dependa de
  eso es ofrecerlo sin saber qué entrega.

- **La tarjeta no es la caja de escritura, y hasta ahora no había dónde
  decirlo.** La tarjeta es lo que el cliente se lleva; la caja es el
  rectángulo que la punta recorre dentro. El contrato ya lo tenía así para
  el único formato que había —A7 apaisado de 105 × 74, 12,5 de margen a los
  lados y 22 al fondo, que dan 80 × 30— pero los tres números vivían
  sueltos y nada decía que el tercero saliera de los dos primeros.

  `docs/tarjetas/` lo pone como dato, con el **margen** declarado y la caja
  **derivada**: declarar las dos cosas deja que se contradigan. Añadir un
  formato no es programar, igual que añadir una fuente o una pieza
  comercial.

  Y es la palanca de capacidad más grande de las cuatro, por encima del
  enlace y de los renglones: con 80 × 24 «Montserrat» hay que medirla y con
  40 × 14 sale limpia. Una decisión así se toma por pedido, así que no
  puede vivir en una constante.

  **Hecho el 2026-10-05: `caja_alto` baja de 30 a 24**, y el margen al
  fondo del A7 pasa de 22 a 25. El papel no se mueve, ni la base, ni nada
  más. Con 30, «hola» tecleada **no se podía fabricar**: la relación de
  curvatura de la leva derecha caía a 1,07 y el perfil se autointersecaba
  sin dejarse recortar; con 24 queda en 2,13 y el error de trazo se parte
  por la mitad, de 0,087 a 0,043 mm.

  Lo tranquilizador fue el golden: de los seis casos **solo se movieron
  dos**, `alta` y `hola`, que son los limitados por el alto. Los otros
  cuatro los limita el ancho y salieron byte a byte iguales, sha256 de los
  DXF incluidos. Una cota se puede bajar sin arrastrar lo que no la toca, y
  el golden es lo que lo demuestra en vez de prometerlo.

  Y se llevó por delante un test, por la razón buena:
  `test_del_socavado_decide_lo_que_escribe_la_leva_recortada` construía un
  escenario —un rodillo de 8 que no cabe en los lazos de «hola»— y con la
  curvatura mejorada **ese rodillo ya cabía**. No se ajustó el test al
  número nuevo: se reconstruyó el escenario con rodillos de 11 y 18. Un
  test que deja de fallar porque el mundo mejoró hay que releerlo, no
  recalibrarlo.

- **Un renglón es un cartucho, no una línea de texto.** Una vuelta del
  árbol escribe un renglón, así que partir una frase en dos cuesta **tres
  levas más** y obliga a cambiar el cartucho a media frase. Es una decisión
  de dinero, no de maquetación, y por eso la toma quien pide —un salto de
  línea— y no el programa por su cuenta.

  Lo que sí se mide solo es el **interlineado**: sale de lo que miden las
  letras que de verdad hay en el texto, ascendente más descendente más
  `HUECO_ENTRE_RENGLONES`, y no de un número elegido. En la Hershey cursiva
  el ascendente llega a 2,78 alturas de x y el descendente a 1,33, así que
  con mayúsculas y jotas el salto ronda las 4,4. El mismo salto en todos
  los pares, para que las líneas base queden en rejilla: calcularlo par a
  par dejaría un renglón pegado y el siguiente suelto según lleve o no una
  jota.

  Y se **enlaza por renglón**, no sobre la lista plana: ahí el último trazo
  de uno y el primero del siguiente son consecutivos, y con un enlace
  holgado se unirían en una diagonal que además metería un trazo en dos
  cartuchos a la vez.

- **`Simulacion.escritos` dibujado de una tirada inventa rayas.** Quita los
  puntos en vuelo y devuelve los demás seguidos, así que unirlos con una
  polilínea traza líneas de una letra a otra que la máquina no dibuja. Con
  dos renglones es peor: une dos cartuchos que ni comparten vuelta, y sale
  una diagonal cruzando la hoja.

  Lo llamativo es que **ya estaba resuelto en el otro emisor**:
  `emit/patron.py` parte el recorrido en tramos desde el primer día, y su
  propio docstring dice por qué —«sin partirlo, la hoja mostraría líneas
  que la máquina no dibuja»—. Dos renderizadores del mismo recorrido y solo
  uno miraba la altura. La web usa ahora `patron_de`, con lo que el vuelo
  sale punteado igual que en el papel.

- **Mirar la página no sirve si el servidor sirve el código de ayer.** La
  página se lee del disco en cada petición y el Python no: con uvicorn sin
  `--reload`, el HTML nuevo recibía la respuesta vieja, no encontraba los
  tramos y **no dibujaba ninguna simulación**. La captura salía «arreglada»
  —ni una raya falsa— porque no había nada pintado.

  Es la familia del `text-anchor` con una vuelta más: no basta con que la
  comprobación mire lo que mira el render; tiene que mirar **el render de
  ahora**. Si una captura mejora justo donde se esperaba, comprueba que lo
  que se ve es lo nuevo y no un hueco.

- **Lo que hace lenta la compilación es exactamente lo que hace incierto el
  veredicto.** Medido con «Gracias» (siete trazos): el reparto de θ, la
  cinemática inversa, sintetizar las tres levas y la envolvente de C3 tardan
  **5 ms** entre todas; recortar 0,18 s; verificar por contacto 0,30 s; y
  **recorrer las levas, 45 s**. Casi todo el veredicto es instantáneo.

  Y la simulación no sobra: es la que decide el `perfil_autointersecado` de
  una leva recortada, que **no es geometría imposible sino fidelidad** —la
  leva se puede cortar, y lo que falta por saber es cuánto redondea la
  letra—. Así que las dos cosas coinciden: sin recortes la respuesta ya está
  antes de simular, y con recortes hay que simular justo porque no está.

  De ahí `compilar(..., simular_el_trazo=False)`, que es la vista previa.
  **No es un predictor aparte**: es el mismo camino parado. Uno aparte diría
  que cabe algo que luego no cabe, y a la segunda vez nadie lo mira. Lo
  cruzan dos tests contra los cuatro casos de referencia: cada incidencia
  del camino corto tiene que estar en el largo, y `falta_medir_el_trazo`
  tiene que aparecer exactamente cuando el largo resuelve con
  `socavado_tolerable` o `perfil_autointersecado`.

- **«No he encontrado ningún error» no es «cabe», y un booleano no sabe
  decir la diferencia.** `Veredicto.apto` es honesto —no hay errores en la
  lista— pero en la vista previa faltan por medir las levas recortadas, que
  es justo por lo que «Gracias» no pasa. La interfaz tiene **tres** estados
  —`no`, `falta_medir`, `si`— y el del medio no se puede fabricar sin pedir
  el cartucho. Reducirlo a sí/no prometería el número que no se ha
  calculado.

- **Una barra de reparto que se dibuja cuando no hay reparto tranquiliza.**
  Con los mínimos desbordados, `repartir` deja de repartir y devuelve un
  corte proporcional «para poder enseñar cómo quedaría». Pintado como
  presupuesto, «Feliz aniversari Montserrat» salía con **281° de tinta y 78
  de vuelo** —más sana que la de «Montserrat», que casi cabe— justo encima
  de un «no cabe». El número que manda ahí es `arco_minimo_necesario`, que
  el núcleo ya publica: 484° contra los 360 que hay.

- **La hoja de estilo le volvió a ganar a la clase que yo creía poner.**
  `.barra div{color:#fff}` es más específico que `.vuelo{color:#555}`, así
  que el rótulo del vuelo salía blanco sobre el rayado claro e ilegible. Es
  la familia del `text-anchor`, y las dos veces se ha visto **mirando la
  página**, no leyendo el CSS. Un visor en el bucle, otra vez.

- **Fase.** Un cartucho montado desfasado escribe basura. La marca física y la
  verificación van en el dossier, no solo en el código.

---

## Cómo trabajar en este repo

- Antes de un cambio grande, propón el plan y espera. Después implementa.
- Cambios en `core/`: test primero.
- Si un cambio toca un contrato congelado (`docs/contratos.md`), párate y avísalo.
- No metas dependencias nuevas sin justificarlo en el mensaje de commit.
- No refactorices a "framework genérico" mientras solo exista una máquina. La
  regla del proyecto es **concreto ahora, marco en la máquina 2**.
- Al terminar, ejecuta lint, tipos y tests, y di qué comprobaste.

## Dónde está lo demás

| Documento | Contenido |
| --- | --- |
| **`docs/expediente.md`** | **La puerta de entrada**: qué es, cómo se hace, qué falta y en qué orden |
| `docs/baseline.md` | Principios, ontología, núcleos, módulos, hitos, negocio |
| `docs/contratos.md` | Por qué cada cota es la que es, y el registro de cambios |
| `docs/contratos.json` | Los números de esos contratos, que es de donde los lee todo |
| `docs/ficha-producto.md` | Despiece, proveedores, coste de material y decisiones de fabricación |
| `docs/metodologia.md` | Cómo se diseña, se prueba antes de gastar, y qué lleva el dossier |
| `docs/ensamblaje.md` | Cómo se monta: en Onshape a mano, y en 3D desde el compilador |
| `docs/modulos/` | Una ficha por módulo del catálogo |
| `docs/piezas/` | Una ficha por pieza comercial: cotas de interfaz, fuente y sustitutos |
| `bench/README.md` | Protocolo del banco de ensayo y datos medidos |

## El escribiente concreto (E5)

`compile/escribiente.py` fija la máquina: brazo de cinco barras con los dos
pivotes anclados, palanca para el lápiz y tres levas apiladas. Tres números
que se decidieron midiendo y no eligiendo:

- **Hueco al poste: 11,3 mm** con «hola» (9,7 antes de escalonar la pila). Los tres
  postes de seguidor están a 71 mm del árbol y atraviesan los tres planos, así
  que la leva de cada canal gira bajo los postes de los otros dos. **Ese hueco
  encoge cuando la frase crece**, y es el límite de conjunto que decide qué
  frases caben: no lo ve ninguna envolvente de C3, que juzga una leva sola.
  Y lo que mide el hueco **no es el poste, es la valona de su casquillo**:
  `Cartucho.radio_poste` es el radio del obstáculo. Con postes de Ø16 y
  casquillo de bronce de valona Ø28 quedaban 3,0 mm y saltaba el aviso; con
  Ø8 y un igus GFM-0810, cuya valona es **Ø15**, quedaban 9,7; con la pila
  escalonada, 11,3.
- **La pila es escalonada** (2026-10-04): elevador abajo con R 55, derecho
  R 48,4, izquierdo arriba R 39,6. El eje de cada rodillo baja junto a las
  levas de encima, y con tres iguales el de abajo las atravesaba. Los postes
  no se mueven: cambian los brazos de seguidor (45 / 52 / 59, una pieza con
  tres agujeros) y el izquierdo va al revés para dejar salir el cartucho.
  `compilar` lo vigila con `eje_de_rodillo_contra_leva`.
- **Relación seguidor → brazo, 6:1.** Con relación 1 y un barrido de brazo de
  26°, mantener el ángulo de presión por debajo de 30° exige un radio base de
  110 mm: levas de 240 mm, tres apiladas. Con 6:1 el seguidor barre un sexto
  y la leva baja a 108 mm.
- **Rodillo Ø6 mm: un MR63ZZ (3×6×2,5).** Las dos letras importan: el MR63
  abierto mide 2,0 de ancho y dejaría 0,5 mm de juego axial, y un 2RS con Ø3
  de agujero arrastra tanto como el rozamiento que lo hace rodar —el rodillo
  deslizaría en vez de rodar—. Antes eran Ø4, un diámetro para el que
  no hay rodamiento decente. Subir a 6:1 fue lo que permitió usar uno normal:
  con 3:1 ni el MR63 pasaba la curvatura. **Y el error bajó en vez de subir**
  —de 0,058 a 0,040 mm en la punta—, porque un seguidor que barre menos
  describe un perfil más plano, y el polígono lo aproxima mejor. Lo que sí se
  duplica es la amplificación del **juego**, que no está modelado: eso lo mide
  E4, y es lo que impide subir más la relación.
- **Radio base 55 mm.** Con el MR63 la relación de curvatura queda en 2,74,
  por encima del 2,5 recomendado, y desaparece el aviso `curvatura_justa`.
- **Error de trazo simulado: 0,11 mm** con 720 muestras por vuelta, más
  0,040 mm que cuesta exportar el perfil como polígono en vez de como curva.
  **Ese no es el error de la máquina, es el del modelo.** Con C4 enchufado
  (`compile/tolerancias.py`), el presupuesto completo con «hola» da
  **2,79 mm en el peor caso y 1,64 mm cuadrático**, y lo domina el corte: los
  ±0,05 mm que se le piden al taller llegan a la punta como 1,16 mm. Desde el
  2026-10-04 se piden **±0,02** (rotulado en el plano de cada leva): 1,35 mm
  peor caso y 0,62 cuadrático. El corte sigue mandando y la cinta (0,18 mm)
  es la siguiente palanca. El «muestreo del modelo» es de **3 µm**: los
  0,108–0,144 mm que se daban eran de medir contra puntos sueltos y de contar
  como vuelo los arranques de los trazos (umbral de apoyo de 1e-9 m). El
  varillaje amplifica un error del canto unas 12 veces de cuenta corta —
  `relacion × proximal / brazo_seguidor`— y **23 veces según el jacobiano
  real del cinco barras**, que mueve la punta con una palanca efectiva mayor
  que el brazo proximal. La cuenta corta es optimista; sirve para hablar con
  el taller, no para prometer.
- **El cartucho pesa 185 g** y su momento de inercia respecto del árbol es de
  2,6 × 10⁻⁴ kg·m². Salen exactos del polígono, sin modelo 3-D: todas las
  piezas son prismas de plancha (`core/solido.py`).

El **calaje** de cada brazo —a qué ángulo se monta sobre el eje de su
seguidor— es una **constante de la máquina**: el ángulo del brazo con la
punta en el centro de la caja. Va en el informe y tiene que llegar al
dossier, porque montarlo mal escribe basura, pero **no cambia entre pedidos**
y por eso el brazo es pieza de stock. Congelado en `docs/contratos.md`.

Se calculaba como la media de los ángulos del ciclo, que da la leva más
pequeña posible. Pero la media depende de por dónde escriba el cliente —3,3°
de recorrido entre frases, 5 mm de trazo desplazado— y eso obligaba a calar
el brazo en cada pedido.

### La base, y el marco que la máquina no tenía

La planta está cerrada; la altura no. Todo lo vertical cuelga de
`base_al_plato`, **75 provisionales**, que no se puede decidir hasta saber
cómo se sujeta el portaminas.

**El marco de la base es el del cinco barras.** El centro de la caja de
escritura cae a 240° exactos del árbol en el marco de la leva —la caja está
sobre el eje +Y del cinco barras y ese marco va girado 150°—, así que visto
desde ahí todo sale simétrico: el árbol en (0, −32,451), los pivotes a ±60,
dos postes atrás y uno delante en (0, +38,61). No hace falta cota: la base
se sitúa por sus tres agujeros, que son los de los platos.

**La planta la cierran el plato por detrás y la tarjeta por delante**, con
10 mm de nogal a las cuatro puntas: 240 × 275 × 25 (a los lados mandan los
sectores, no el plato: con 190 se salían 14,5, auditoría A1). La ficha de producto
decía 210 × 160 y se quedaba **115 mm corta de fondo**; eso casi dobla la
línea del nogal, porque una tabla de 2 m da 7 bases y no 13.

**Los postes bajan hasta la base y hacen de pata.** Mismo argumento que el
tercer plato: un pilar propio obligaría al plato 1 a llevar agujeros que los
otros dos no tienen. `poste_largo` pasa a 195 y se deriva de la cadena
entera, que acaba con el «70 de antes» y saca a la luz `poste_vano`, los
58 mm entre el plato 1 y el plato 2 donde van la pila, los seguidores, el
sector y la cinta.

**Por dónde pasa la mano**: el volante gira entero dentro de la tabla, pero
el pomo de la manivela se sale 19 mm por la izquierda y cruza 29 mm sobre la
tarjeta, a 190 de altura. Viene de haber colocado el eje de la manivela en
el marco de la **leva** —a −90° allí, que son 120° en el de la base— sin
mirar dónde cae eso visto desde quien escribe. No choca con nada; la máquina
no se arrima a una pared por la izquierda. Corregirlo costaría redibujar la
platina, que ya está entregada.

### El cartucho es una sola pieza lógica

Cada leva lleva **dos** taladros: el del eje, que centra, y un pasador de
índice de Ø3 a 18 mm sobre +X, que orienta. El pasador está en el mismo
ángulo en las tres, así que enhebradas quedan caladas entre sí y el error de
fase deja de ser posible en vez de ser improbable. Está congelado en
`docs/contratos.md` y lo defienden cuatro tests.

### El reductor no es para el par

Los números de C6, C7 y C9 sobre el cartucho de «hola»:

| | |
| --- | --- |
| Par medio en el árbol | 22 mN·m |
| Par máximo | 48 mN·m |
| Lo que da una mano en una manivela | ~1,8 a 4 N·m |
| Trabajo por vuelta | 141 mJ |

Sobra un factor cuarenta. **El par nunca ha sido el problema**, y por eso la
relación mínima de manivela que exige el par es 1:1.

Lo que aprieta es la **suavidad**, y los números de aquí están **medidos
hoy** (2026-10-02) con `compile/energia.py`, no copiados de una nota: la
sección anterior decía 44 × 10⁻⁴ y un disco de 92 g, y ninguno de los dos
reproducía desde que el cartucho cambió a 6:1.

La inercia que hace falta **en el eje donde va el volante** es ΔE/(Cs·ω²), y
ω es la de **ese** eje. Puesto en la manivela, depende solo de a cuánto gire
la mano: **la relación no entra**. Con 90 rpm en la manivela y Cs = 15 %:

| | ΔE | Volante en la manivela |
| --- | --- | --- |
| «hola» | 3,4 mJ | 2,28 × 10⁻⁴ kg·m² |
| «puntos» | 4,8 mJ | 3,33 × 10⁻⁴ |
| **«firma»** | **5,2 mJ** | **3,62 × 10⁻⁴** |

**Dimensionar sobre el demo deja el volante un tercio corto.** «firma» —un
trazo cursivo largo— pide un 59 % más que «hola», y es justo el pedido más
probable. Lo defiende `test_el_volante_del_contrato_cubre_el_peor_caso_de_
referencia`.

**Entonces, ¿para qué el reductor?** No para el par, que sobra por cuarenta,
y tampoco para encoger el volante a igualdad de manivela: a 60 rpm de mano
el volante sale igual con 1:1 que con 3:1 (algo peor, incluso, porque el
cartucho cuenta dividido por la relación al cuadrado). Sirve para **separar
las dos velocidades**: la mano gira deprisa —que es lo que baja el volante—
y el árbol despacio, que es lo que deja ver cómo se escribe la frase. Con
3:1 y 90 rpm, el árbol va a 30 y la frase tarda dos segundos.

### Dónde se apoya el eje de la manivela

El reductor **no puede ir entre los platos**: el entre-ejes son 28 y la leva
tiene radio base 55, así que el eje de la manivela caería dentro del disco de
leva. Y **tampoco debajo**, que es donde están los brazos y el lápiz bajando
al papel. Va arriba, y eso de paso pone la manivela donde se gira cómodo,
como un molinillo, con el volante a la vista.

Un eje necesita **dos apoyos**: con uno solo queda en voladizo cargando los
294 g del volante y los 40 N de la mano. Los dan el plato 2 y un **tercer
plato**, y entre los dos caben el piñón y el volante —las dos masas entre
rodamientos, y fuera solo la manivela—.

**Ese tercer plato es la misma pieza.** Con un séptimo agujero en la platina
—otro Ø19 H7 a 28 del árbol, a -90°, detrás— los tres platos son idénticos.
En el plato de abajo ese agujero no sujeta nada: es una ventana más. El coste
es un poste más largo (70 → 105) y dos rodamientos; piezas nuevas, ninguna.

Dos números que salieron al dibujarlo y que ahora vigila un test:

- **El volante gira dentro de la silueta.** Centrado a 28 y con Ø104 llega a
  80 del árbol, contra los 85 de radio del plato. No fue buscado, pero es la
  diferencia entre una máquina y un aparato con cosas colgando.
- **Las patas no pueden ir delante.** El papel empieza a 85 del árbol y el
  plato llega a 85: una pata bajo el borde delantero aterriza encima del
  papel. Van detrás y a los lados.

Y el ángulo es **-90°** y no 270 porque un campo de ángulo no acepta ni el
signo ni más de media vuelta: se teclea el gemelo en positivo, 90 bajo +X.

### El volante que hay, y lo que no es el engranaje grande

**Ø104 × 6 en latón, aligerado con seis agujeros de Ø24 a 30 del centro:
4,51 × 10⁻⁴ kg·m² y 294 g**, un 24 % por encima del peor caso. Aligerado
porque la inercia vive en el borde: los seis agujeros quitan 100 g y solo un
9 % de inercia. Cala con la misma cara plana que los brazos, sobre la misma
barra Ø10 h6, y sin prisionero: un taladro radial no sale de una plancha
cortada. Está en el contrato, en el grupo `accionamiento`, y es la **única
cota de la máquina que no sale de un encaje sino de un requisito**.

La rueda Z60 va en el árbol, que es el lento, así que su inercia cuenta tal
cual y no multiplicada: **ayuda poco, no es el volante**. `Accionamiento`
tiene `inercia_en_el_arbol` e `inercia_en_la_manivela` para contarlas, y la
segunda entra multiplicada por la relación al cuadrado; por defecto trae el
volante del contrato, para que el informe de un pedido no pida uno que ya
está dibujado.
