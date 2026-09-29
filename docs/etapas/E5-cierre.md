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
