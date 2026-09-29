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
uv run pytest                # tests
uv run pytest -m core        # solo el núcleo (rápido)
uv run ruff check --fix .    # lint
uv run ruff format .         # formato
uv run mypy core compile emit  # tipos (estricto en core/)

uv run python scripts/export_schema.py        # esquema JSON tras tocar un modelo
uv run python scripts/dibujar_perfiles.py     # lámina de perfiles para revisar
uv run python scripts/plantillas_demo.py      # plantillas 1:1 de muestra
uv run python scripts/regenerar_golden.py     # SOLO si el cambio es intencionado

uv run python -m compile.cli demo/hola.json --out build/   # compilar un pedido
uv run uvicorn api.main:app --reload                       # API en local
npm --prefix web run dev                                   # frontend en local
```

Antes de dar por terminado un cambio: `uv run ruff check . && uv run mypy core compile emit && uv run pytest`.

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
compile/              # Orquesta: intención -> piezas + informe. I/O permitido.
  escribiente.py      #   La máquina concreta: compilar y simular
  conjunto.py         #   El cartucho montado: interferencias, pila, masa
  energia.py          #   ¿Puede girarlo una persona, y sale limpio?
  informe.py          #   El informe del pedido, en markdown
  cli.py              #   Un pedido, un comando
emit/
  pieza.py            #   Pieza y sus siete metadatos, compartida por los tres
  layout.py           #   Maquetación 1:1 en mm: cabecera, colocación, troceado
  calibracion.py      #   Perfil de impresora: factores x/y, hoja patrón
  paquete.py          #   Qué archivos salen y qué lleva cada uno
  template.py         #   PDF 1:1 para copistería          <- ver abajo
  dxf.py              #   Corte láser / CNC
  dossier.py          #   Dossier de montaje
  step.py             #   3D
  onshape.py          #   Gemelo paramétrico (1 llamada por pedido)
api/                  # FastAPI
web/                  # React + Vite + TypeScript
bench/                # Datos del banco de ensayo y calibraciones medidas
  impresoras/         #   Un perfil por impresora, con fecha, papel e instrumento
docs/
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
fase— viven en `docs/contratos.md`, que para eso está.

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
- `tests/golden/` — comparación byte a byte de DXF contra referencias guardadas.
  Detecta regresiones silenciosas en geometría.
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
| `docs/baseline.md` | Principios, ontología, núcleos, módulos, hitos, negocio |
| `docs/contratos.md` | Contratos congelados: eje, bastidor, fase |
| `docs/modulos/` | Una ficha por módulo del catálogo |
| `bench/README.md` | Protocolo del banco de ensayo y datos medidos |

## El escribiente concreto (E5)

`compile/escribiente.py` fija la máquina: brazo de cinco barras con los dos
pivotes anclados, palanca para el lápiz y tres levas apiladas. Tres números
que se decidieron midiendo y no eligiendo:

- **Hueco al poste: 5,9 mm** con la caja de escritura por defecto. Los tres
  postes de seguidor están a 71 mm del árbol y atraviesan los tres planos, así
  que la leva de cada canal gira bajo los postes de los otros dos. **Ese hueco
  encoge cuando la frase crece**, y es el límite de conjunto que decide qué
  frases caben: no lo ve ninguna envolvente de C3, que juzga una leva sola.
- **Relación seguidor → brazo, 3:1.** Con relación 1 y un barrido de brazo de
  26°, mantener el ángulo de presión por debajo de 30° exige un radio base de
  110 mm: levas de 240 mm, tres apiladas. Con 3:1 el seguidor barre un tercio
  y la leva baja a 114 mm. Se paga amplificando por tres el error del perfil y
  el juego: es la cadena de tolerancias de C4 y es lo que limita subir más.
- **Radio base 55 mm, rodillo 2 mm.** Es la combinación más pequeña que pasa
  la envolvente sin autointersecarse.
- **Error de trazo simulado: 0,11 mm** con 720 muestras por vuelta, más
  0,058 mm que cuesta exportar el perfil como polígono en vez de como curva.
- **El cartucho pesa 185 g** y su momento de inercia respecto del árbol es de
  2,6 × 10⁻⁴ kg·m². Salen exactos del polígono, sin modelo 3-D: todas las
  piezas son prismas de plancha (`core/solido.py`).

El **calaje** de cada brazo —a qué ángulo se monta sobre el eje de su
seguidor— es resultado de la compilación, no un parámetro. Va en el informe y
tiene que llegar al dossier: montarlo mal escribe basura.

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

Lo que aprieta es la **suavidad**. La energía de fluctuación son 6,5 mJ, y
para que la velocidad no varíe más de un 15 % a 30 vueltas por minuto hacen
falta 44 × 10⁻⁴ kg·m²: un disco de acero de 3,3 kg. Inaceptable en una pieza
de sobremesa.

La inercia necesaria va con 1/ω², así que el volante se pone **en el eje
rápido**. Con reductor de 3:1 y 60 vueltas por minuto de manivela, el mismo
trabajo lo hace un disco de **75 g**.

**Ese es el motivo de llevar reductor: no el par, el volante.** Y de paso
sube la velocidad del árbol, que vuelve a bajar la inercia necesaria.
