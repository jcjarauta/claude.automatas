# Expediente del reloj

Qué es, por qué está en este repositorio y en qué punto está.

Este documento es **la puerta de entrada del reloj**, como `docs/expediente.md`
lo es del escribiente.

Fecha de este estado: **2026-10-02**. Rama: `reloj`.

| Si buscas | Ve a |
| --- | --- |
| Cómo se diseña, se prueba y se documenta | `docs/reloj/metodologia.md` |
| Qué piezas hay, en qué orden se hacen y de qué parámetro sale cada una | `docs/reloj/piezas.md` |
| Los números que no se tocan | `docs/reloj/contratos.json` |
| Las etapas y sus puertas | `docs/reloj/ROADMAP.md` |
| Los principios comunes a todas las máquinas | `docs/baseline.md` |

---

## En una frase

Un **reloj de pared de péndulo, en madera**, diseñado por una app paramétrica,
cuyo producto no es solo el reloj: es **un eje que gira a una velocidad conocida
y sobra par**, para que otras máquinas del proyecto se cuelguen de él.

De ahí el nombre interno: **órgano temporal**.

## Por qué una rama y no un repositorio aparte

Se valoró separarlo. Estar en el mismo repositorio gana por tres razones
concretas, y no son de comodidad:

1. **El paquete `core` ya existe aquí.** En un repositorio aparte habría dos
   paquetes llamados `core` y habría que renombrar uno, o empaquetar el
   escribiente y fijarlo a un commit. Dentro, el reloj es `core/reloj/` y no
   hay nada que empaquetar.
2. **`tests/test_arquitectura.py` ya vigila el núcleo.** Prohíbe que `core/`
   importe disco, red, `compile` o `emit`. El reloj hereda esa vigilancia el
   día que entra, gratis.
3. **El reloj es la máquina 2.** La regla del proyecto es *concreto ahora,
   marco en la máquina 2*. Ese refactor solo puede ocurrir con las dos
   máquinas delante, en el mismo árbol.

**La rama no debe vivir mucho.** Una rama larga diverge y acaba sin poder
fusionarse. El plan es cerrarla pronto:

- Se fusiona a `main` al cerrar **R0**, cuando solo hay documentos, el
  esqueleto de `core/reloj/` y sus tests en verde. Entonces el reloj pasa a ser
  una parte más del repositorio.
- A partir de ahí, ramas cortas por etapa, como cualquier otro trabajo.

El escribiente no se entera: el reloj no toca ninguno de sus archivos.

## La regla del tiempo

La regla 1 de `CLAUDE.md` dice que si aparece un `dt` dentro de `core/`, algo
está mal planteado. El reloj necesita una excepción, declarada y acotada:

> **El tiempo entra en el núcleo solo por el oscilador, y solo como periodo.**
> `core/reloj/pendulo.py` es el único módulo del repositorio donde un segundo
> es una magnitud legítima. Todo lo que hay aguas abajo —tren, dentado,
> platinas— vuelve a ser geometría y relaciones adimensionales.

Es lo mismo que decía la ontología del baseline y nunca se había construido: la
capa **0c, base de tiempo**, que genera θ. En el escribiente esa capa es una
mano girando una manivela. Aquí es un péndulo, y por eso aquí sí hay segundos.

Un test lo defiende: `tests/reloj/test_arquitectura_reloj.py` comprueba que
ningún módulo de `core/reloj/` salvo `pendulo.py` menciona unidades de tiempo.

## Qué lo hace órgano temporal, y no solo un reloj bonito

Un reloj que da la hora es un objeto. Lo que lo convierte en pieza de este
proyecto es que **declara su salida en una ficha legible por máquina**, igual
que cualquier otro módulo del catálogo.

`ficha_tiempo.json`, que emite el compilador con cada diseño:

```json
{
  "ejes": [
    {"nombre": "escape",  "vueltas_por_hora": 60.0, "par_sobrante": 0.0009, "sentido": "horario"},
    {"nombre": "central", "vueltas_por_hora": 1.0,  "par_sobrante": 0.0052, "sentido": "horario"},
    {"nombre": "programa","vueltas_por_hora": 0.0417,"par_sobrante": 0.0310, "sentido": "horario"}
  ],
  "contrato_eje": "eje_v1",
  "autonomia_horas": 30
}
```

Cualquier máquina futura declara en su `FichaModulo` lo que necesita —un eje a
tantas vueltas por hora con tanto par— y `core/module.py` comprueba el
acoplamiento **con el código que ya existe**, sin escribir un validador nuevo.

Ese es el entregable de verdad. El reloj es la primera implementación de la
ficha, no la ficha misma.

## Qué está decidido

| Decisión | Estado |
| --- | --- |
| Reloj de pared, no de sobremesa | Cerrada |
| Péndulo de segundos: periodo 2 s, longitud ~994 mm | Cerrada |
| Pesa como motor; nada de muelle real | Cerrada |
| Escape de áncora de retroceso, con paletas regulables | Cerrada |
| Madera y plantillas impresas como vía de fabricación | Cerrada |
| 30 horas de autonomía en la primera generación | Propuesta |
| El acople a autómatas se diseña como contrato, no se construye | Cerrada |
| Rama `reloj`, fusionada a `main` al cerrar R0 | Cerrada |

## Qué no está decidido, y quién lo decide

- **La masa de la pesa.** Hay una **previsión de 3,5 kg**, anclada en relojes de
  madera comparables y rotulada como tal, para poder pedir material. La medida
  real sale del banco de escape (R2). Lo que sí está decidido es el **techo de
  diseño, 5 kg**: cuerda, polea, eje de la rueda grande y anclaje se calculan
  con ese número, porque la pesa se cambia llenando un tubo y el anclaje no.
- **El módulo del dentado.** Sale del compromiso entre holgura de corte a mano
  y tamaño de las platinas. Lo propone C12 y lo cierra la primera rueda que se
  corte.
- **El material definitivo de la rueda de escape.** Abedul para empezar; si el
  canto se marca antes de 10.000 ciclos, se pasa a latón o a impresión 3-D.
- **Treinta horas u ocho días.** Ocho días son una rueda más y un tambor mayor.
  La primera generación va a 30 h.

## Cómo saber que algo está mal

- Un número del reloj aparece escrito en dos sitios. Tiene que estar en
  `docs/reloj/contratos.json` y en ningún otro.
- Un segundo aparece fuera de `core/reloj/pendulo.py`.
- Se está dibujando una platina antes de haber medido la pesa mínima en el
  banco. Las distancias entre centros dependen del tamaño de las ruedas, y el
  tamaño de las ruedas depende del par.
- Alguien propone subir la precisión del dentado para que el reloj ande mejor.
  Lo que hace que un reloj ande no es la precisión: es la **constancia** del
  rozamiento. Ver `docs/reloj/metodologia.md`, §1.
