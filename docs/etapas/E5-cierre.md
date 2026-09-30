# Cierre de etapa E5 · Compilador extremo a extremo
Fecha: 2026-09-29

## Entregable
De un archivo con una escritura sale un paquete de fabricación con un comando:

```bash
uv run python -m compile.cli demo/hola.json --out build/
```

- `core/escritura.py` — normalizar, reparametrizar por arco, repartir θ,
  capacidad. Las tres pistas del programa.
- `compile/escribiente.py` — la máquina concreta, la compilación y la
  simulación inversa.
- `compile/informe.py`, `compile/cli.py` — el informe y el comando.
- `emit/dxf.py` — corte digital, con compensación de kerf.
- `bench/kerf.json`, `bench/README.md` — el dato, todavía sin medir.
- `demo/hola.json` — un pedido de ejemplo que compila.

## Verificación automática
Comando: `uv run python scripts/check.py`
Resultado: VERDE — **410 tests** (319 al cerrar E3b), mypy estricto sin
errores sobre `core`, `compile` y `emit`, lint y formato limpios.

| Requisito del ROADMAP | Cómo se comprueba |
| --- | --- |
| Golden de DXF, byte a byte | `tests/golden/leva.dxf`, y además un test de que cuatro escrituras seguidas dan la misma huella |
| Cien frases al azar, ninguna inválida en silencio | Las aptas tienen tres levas y error bajo umbral; las no aptas tienen error **con sugerencia**, comprobado una por una |
| Simulación inversa por debajo del umbral | 0,108 mm frente a 0,5 mm de límite |
| Menos de 10 s por frase típica | Mide el test; tarda dos órdenes de magnitud menos |
| Idempotente y determinista | Programa, piezas y métricas iguales en dos compilaciones; y los cuatro archivos de salida iguales byte a byte |

Un test comprueba además que la simulación **no se engaña sola**: se le pasan
las levas de una frase y la escritura de otra, y el error se dispara. Sin eso,
comparar el resultado consigo mismo daría cero siempre.

## Desviaciones
**La leva se sintetizaba para el ángulo absoluto del brazo.** El brazo derecho
del cinco barras trabaja hacia los -177°, así que el seguidor entraba en la
síntesis a un cuarto de vuelta de su punto de diseño: ángulos de presión de
68° y perfiles autointersecados. La leva tiene que sintetizarse para la
**desviación**; el resto es el calaje del brazo sobre el eje del seguidor, que
ahora es un resultado de la compilación y va en el informe. Lo cazó la
envolvente, que para eso está.

**Con relación 1:1 las levas salían de 240 mm.** Mantener el ángulo de presión
por debajo de 30° con un barrido de 26° exige un radio base de 110 mm. Se
añadió la relación seguidor → brazo: con 3:1 la leva baja a 114 mm. No es
gratis, y el informe lo dice.

**El DXF no era determinista entre procesos.** Dentro de una misma ejecución
salía idéntico; en la siguiente, distinto. La biblioteca declara las clases
recorriendo un conjunto, y un conjunto de Python no tiene orden estable entre
procesos. Los tests de determinismo pasaban y el golden fallaba, que es la
peor combinación posible. Anotado en las trampas.

## Decisiones tomadas
1. **Reparametrizar por longitud de arco**, no por número de puntos. La
   velocidad de la mano no se captura y no debe reproducirse.
2. **Los vuelos pesan la mitad que los trazos** al repartir θ. No se ven, y el
   ángulo que se les quita se lo queda el papel.
3. **El levantamiento sube y baja con ley cicloidal.** Una rampa lineal es
   aceleración infinita al arrancar: un golpe en cada trazo.
4. **La leva se sintetiza para la desviación del seguidor**, y el calaje es un
   resultado que va al dossier.
5. **Relación seguidor → brazo de 3:1** por defecto, con el coste de
   amplificar el error por tres declarado en el informe.
6. **Un DXF por pieza.** En el láser cada una se corta por su cuenta.
7. **El kerf se aplica en `emit/` y solo si está medido.** Sin medida se corta
   por la línea nominal y el archivo lo dice en su rótulo.
8. **Código de salida 1 si el veredicto es negativo**, pero los archivos se
   escriben igual: un pedido que no cabe también hay que poder mirarlo.

## Deuda aceptada
- El reparto de θ es proporcional a la longitud, **no por curvatura**. El
  ROADMAP lo pedía; con el error de trazo en 0,1 mm no hace falta todavía, y
  meterlo ahora sería optimizar sin un problema que resolver.
- ~~La simulación lee la curva de paso, no el perfil cortado.~~ **Saldada el
  2026-09-29** con `core/cam/contacto.py`: se apoya el rodillo en el polígono
  que se va a cortar y se recupera ψ sin usar la curva de paso ni las
  normales. Es una derivación independiente de la síntesis, así que caza un
  error sistemático —un desplazamiento del revés— que a la simulación se le
  escapa por compartir fórmulas.

  Del **socavado** sigue ocupándose la envolvente, y hay que decirlo claro: es
  un defecto local, de unos pocos grados, y cazarlo por contacto exigiría
  muestrear todo el ciclo, que cuesta diez veces lo que este paso puede
  gastar. El contacto muestrea también alrededor de la curvatura mínima y el
  número sube cuando hay socavado, pero el juez es C3, que lo calcula exacto.

  Y un número nuevo que antes no teníamos: **el perfil exportado es un
  polígono, no una curva**, y esa discretización vale 0,21 mrad en el seguidor
  y, amplificada por el varillaje, **0,058 mm en la punta**. Es la mitad del
  error de trazo simulado. Subir las muestras por vuelta lo baja.
- El kerf sigue sin verse en ninguna simulación: eso es E4.
- El empalme entre un trazo y el vuelo siguiente tiene una esquina. El spline
  la suaviza, pero la aceleración ahí es la más alta del ciclo. Se mirará con
  datos del banco antes de tocar nada.
- `Escribiente` es una clase, no una ficha de catálogo en `docs/modulos/`. La
  regla del proyecto es concreto ahora, marco en la máquina 2.

## Puerta
Automática: CERRADA.
Humana: PENDIENTE. **El prototipo escribe una palabra legible** — requiere
levas cortadas, y eso depende de E3b y de la copistería.

---

# Reauditoría de E5 · 2026-09-30

E5 se cerró el 29 con 410 tests. Hoy hay **672** y, sobre todo, el front-end
de escritura es otro: el vuelo dejó de ser una recta, la interpolación pasó a
C2 y apareció un agujero en la envolvente que no se había visto al cerrar.
Esto revisa la etapa **contra su propia especificación**, que está íntegra en
`ROADMAP.md` §E5 y no se ha perdido nada de ella.

## Punto por punto

| Lo que pedía el spec | Hoy |
| --- | --- |
| Un comando: escritura → paquete de fabricación | **Sí**, y de más: `informe.md`, `plantillas.pdf`, `patron.pdf`, tres `leva_*.dxf`, `programa.json` y `cartucho.step` |
| «Incluye el **reparto de grados por curvatura**» | **No.** Nunca se implementó; `repartir()` reparte en proporción a la longitud |
| «…y el cálculo de capacidad» | Sí |
| Golden byte a byte de **los casos de referencia** | **A medias**, y menos de lo que parece: ver abajo |
| Cien frases al azar, ninguna inválida en silencio | Sí — `test_cien_frases_al_azar_o_compilan_o_dicen_por_que` |
| Simulación inversa por debajo del umbral | Sí — **0,092 mm** frente a 0,5 (era 0,108 al cerrar; bajó con el vuelo nuevo) |
| Menos de 10 s por frase | Sí, dos órdenes de magnitud de margen |
| Idempotente y determinista | Sí — en el compilador y en los archivos |
| **El prototipo escribe una palabra legible** | **No.** No hay prototipo: no se ha cortado ni comprado nada |
| Puerta | Automática cerrada **con una reserva nueva**; humana abierta |

## Lo que se ha degradado desde el cierre

**1. El golden no cubre lo que se creía.** `tests/golden/leva.dxf` guarda una
leva **sintética** (`tests/emit/piezas_de_prueba.leva`), así que vigila el
escritor de DXF y no la geometría que sale del compilador. El spec pedía «los
DXF de **los casos de referencia**». El arreglo del vuelo movió los tres
perfiles de `demo/hola.json` y no saltó ninguna comparación byte a byte: el
criterio estaba dándose por cumplido sin estarlo. Y además solo hay un caso de
referencia, `demo/hola.json`.

**2. El riesgo que el ROADMAP anotó para E5 se ha materializado, pero no por
donde decía.** El texto era: «que el reparto de grados no baste y haya que
volver a la optimización». Lo que pasa es que el **veredicto de curvatura
depende del muestreo** —el radio mínimo del perfil va de 13,5 mm a 720
muestras a 1,05 mm a 11.520— y la causa está localizada: el vuelo forma una
**cúspide** donde un trazo acaba alejándose de donde empieza el siguiente.

Conviene decirlo sin adornos: **repartir θ por curvatura no arregla eso**. Una
cúspide tiene curvatura infinita se le den los grados que se le den. El
reparto por curvatura compra margen en todas partes menos ahí, que es
exactamente donde hace falta. Así que el spec tenía razón en pedirlo y la
deuda aceptada tenía razón en aplazarlo; lo que ninguno de los dos vio es que
el problema iba a estar en la curva de vuelo.

Mientras esto no se cierre, **la pregunta «¿cabe esta frase?» no tiene
respuesta fiable**, porque es una pregunta de curvatura. El paquete que sale
hoy es fabricable —el polígono a 720 muestras redondea la esquina a 13,5 mm,
muy por encima del rodillo de 3— pero lo es por accidente del muestreo y no
por diseño.

## Qué queda de E5, en orden

1. **Una curva de vuelo que admita invertir el sentido sin cúspide.** Quíntica
   con curvatura impuesta en los extremos, o dos arcos empalmados. Es diseño,
   no un parámetro: recortar la tangente contra la cuerda quita la cúspide y
   devuelve una esquina, y darle más θ al vuelo alivia sin garantizar nada.
   **Bloquea el veredicto de curvatura, y con él la capacidad.**
2. **Un golden del perfil compilado**, no de la leva sintética, y más de un
   caso de referencia. Es lo que habría cazado el punto 1 al introducirlo.
3. **El reparto de θ por curvatura**, que es lo único del entregable escrito
   que no existe. Después del 1, no antes: con la cúspide dentro, el número
   que optimizaría no significa nada.
4. **Enchufar `suavizar` al compilador.** Está implementado y probado desde el
   commit del vuelo, sin conectar. Cuesta fidelidad, así que el radio de
   redondeo tiene que ser una cota declarada y no un valor escondido.
5. **La puerta humana.** Cortar las levas, montar y escribir una palabra
   legible. No depende de código: depende de E3b, de la copistería y de
   comprar las piezas (~120 € el conjunto, más el portaminas y el MDF del
   cartucho de calibración).

Del 1 al 4 son código y se pueden hacer aquí. El 5 no.

## Puerta

Automática: **cerrada con reserva**. Los cinco criterios pasan, pero dos de
ellos valen menos de lo que su enunciado promete —el golden no mira el perfil
compilado, y el veredicto de curvatura no converge—. No se reabre la etapa: se
anota que el punto 1 es condición para creerse el cálculo de capacidad, que es
lo que E5 le entrega a E6 y a la interfaz.

Humana: **abierta**. Sin prototipo no hay nada que firmar.

---

# Cierre de los cuatro puntos · 2026-09-30

La reauditoría de esta mañana dejó cinco cosas. Las cuatro de código están
hechas; la quinta es la puerta humana y no depende de código.

## Lo que se ha arreglado, y no era lo que decía la nota

| | antes | ahora |
| --- | --- | --- |
| Radio mínimo del peor perfil, 720 → 5.760 muestras | 13,5 → **1,9 mm** (÷2 cada vez) | 13,5 → **13,0** (×1,04) |
| Lo que se aparta la curva de lo que dibujó el cliente | **3,7 mm**, sin medir | **0,29 mm**, en el informe |
| Continuidad en el aterrizaje del vuelo | rota un 5,4 % en un empalme | 0,02 % |
| Casos de referencia con golden | 1, y de una leva sintética | 4, del perfil compilado |

Tres causas, y **ninguna era la cúspide del vuelo** que la nota daba por
localizada:

1. **Las esquinas de la polilínea.** `suavizar` llevaba desde el arreglo del
   vuelo escrito y probado, sin enchufar. Es el término gordo: la leva
   `derecho` pasa de 4,4 a 22,4 mm.
2. **El tope de la tangente del vuelo** rompía la continuidad C1 para evitar
   un lazo que, con el lápiz levantado, no se ve. Compraba un lazo invisible
   al precio de una esquina real.
3. **`interpolar` se pasaba de largo** 3,7 mm con una polilínea escasa, y era
   invisible porque la simulación compara el recorrido contra el programa,
   hecho con esa misma interpolación: se comparaba consigo misma.

La cúspide no existía —`|dP/dθ|` vale 1,79 mm/rad en el punto malo y no se
anula— y la quíntica con curvatura impuesta que se dedujo de ella, una vez
implementada y medida, **no cambia ni un dígito**. No entra.

Y una lección de método que vale más que el arreglo: **`radio_de_curvatura`
amplifica por 1/h² cualquier salto de curvatura.** A 20.000 muestras marcaba
9,2 mm donde la curvatura real vale 39,9 a un lado y 56,9 al otro: un radio
que no existe en ningún punto de la pieza. Evaluando con paso físico fijo el
número no se mueve. Antes de rediseñar por un número que se desploma hay que
saber si el que falla es la geometría o el metro.

## El reparto de θ por curvatura: medido y descartado

Era lo único del entregable escrito de E5 que no existía. **No se va a
hacer**, y esta vez no por falta de tiempo sino porque la medida dice que no
sirve.

La cuenta dice que el reparto que iguala el error de cuerda va con **L·√κ**.
Medido sobre los cuatro casos de referencia, a 720 muestras:

| caso | por longitud | L·√κ | mezcla suave, la mejor |
| --- | --- | --- | --- |
| `hola` | 0,144 mm | 0,913 mm, **y deja de ser apto** | 0,134 mm |
| `firma` | 0,068 | 0,068 | 0,047 |
| `puntos` | 0,125 | 0,133 | 0,096 |
| `apretada` | 0,242 | 0,368 | 0,241 |

Tres razones para no hacerlo:

1. **Optimiza la magnitud equivocada.** El error de cuerda del camino no es
   lo que domina el error de trazo: lo que domina es la discretización del
   **perfil** de la leva, que depende de cómo de rápido se mueve el seguidor
   y no de cómo de curvado va el camino. Por eso `hola` empeora seis veces.
2. **El peso es inestable con un trazo recto.** Con κ = 0 el cociente κ/κ_ref
   lo decide el ruido de coma flotante de la segunda derivada, y el reparto
   se vuelve aleatorio. Se ve en `puntos`, cuyos ocho trazos son rectos y aun
   así cambian de resultado con el parámetro.
3. **No hay nada que ganar.** El error de trazo son 0,14 mm frente a un
   presupuesto de tolerancias de **1,65 mm cuadrático y 2,84 en el peor
   caso**. Afinar un 25 % de 0,14 mm son 0,035 mm sobre un presupuesto de
   1,65: no se mide ni en el banco.

Si algún día hace falta, la vía buena no es la curvatura del camino sino la
**velocidad angular del seguidor**, que es lo que fija la discretización del
perfil. Eso exige compilar dos veces y no se plantea hasta que E4 diga que el
error de trazo importa frente a las holguras, que hoy lo tapan por diez.

## Qué queda de E5

Solo la **puerta humana**: cortar las levas, montar y escribir una palabra
legible. No depende de código. Depende de E3b, de la copistería y de comprar
las piezas (~120 € el conjunto, más el portaminas y el MDF del cartucho de
calibración).

La parte automática deja de estar «cerrada con reserva» y queda **cerrada**:
los cinco criterios pasan y ya ninguno vale menos de lo que su enunciado
promete. El golden mira el perfil compilado de cuatro casos, uno de ellos una
frase que no cabe, y el veredicto de curvatura converge.
