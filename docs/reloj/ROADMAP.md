# ROADMAP del reloj

Diez etapas, cada una con entregable, verificación automática, verificación
humana y puerta de salida. Misma estructura y mismas reglas que `ROADMAP.md`
del escribiente, porque la dinámica de trabajo no cambia.

Complementa a `docs/reloj/expediente.md` (qué es), `docs/reloj/metodologia.md`
(cómo se diseña) y `docs/reloj/piezas.md` (qué se fabrica y en qué orden).

---

## Cómo funciona este roadmap

Las mismas tres reglas del escribiente:

**La regla de las dos comprobaciones.** Ninguna etapa se cierra con una sola.
Claude no puede juzgar si un tictac suena parejo; una persona no puede
comprobar a mano que cien trenes dan la relación exacta.

**Verde no es opinión.** La verificación humana tiene un criterio escrito antes
de mirar, no después.

**Cada etapa dice qué NO hacer.** Aquí la forma más rápida de hundir esto es
cortar ruedas antes de haber medido el par.

**Protocolo de sesión**, igual que en el escribiente: decir en qué etapa
estamos, proponer plan y esperar si el cambio es grande, test primero en
`core/`, cerrar con lint, tipos y tests, y parar si se toca un contrato.

**El cierre de cada etapa** se copia a `docs/reloj/etapas/RN-cierre.md` con la
plantilla de `docs/etapas/PLANTILLA.md`.

---

## R0 · Andamiaje y contratos

**Objetivo.** Que el reloj exista en el repositorio sin molestar al escribiente.

**Entregable.** `core/reloj/` con su `__init__.py` y los modelos vacíos,
`docs/reloj/contratos.json`, `compile/reloj/` y `tests/reloj/`. La excepción de
la regla del tiempo, escrita en `CLAUDE.md`. Esta rama fusionada a `main`.

**Verificación automática**
```bash
uv run ruff check . && uv run mypy core compile emit && uv run pytest
```
- `tests/test_arquitectura.py` sigue en verde: `core/reloj/` no importa disco ni red.
- `tests/reloj/test_arquitectura_reloj.py`: ningún módulo de `core/reloj/` salvo
  `pendulo.py` menciona unidades de tiempo.
- Todos los tests del escribiente pasan sin cambios.

**Verificación humana.** Leer `docs/reloj/contratos.json` y comprobar que no hay
ningún número del reloj escrito en otro sitio.

**Puerta.** Automática, más la fusión a `main`.

**No hacer.** Empezar a generalizar el núcleo. El refactor a marco es R9, con
las dos máquinas delante.

**Duración.** 3 días. **Riesgo.** Ninguno relevante.

---

## R1 · Péndulo físico (C11)

**Objetivo.** Saber predecir el periodo de un péndulo real, no de uno ideal.

**Entregable.** `core/reloj/pendulo.py`: periodo de un péndulo compuesto desde
la geometría de varilla y lenteja, usando `core/solido.py` para la inercia.
Sensibilidad del periodo a la longitud y a la temperatura. Y el péndulo colgado
en el taller.

**Verificación automática**
- Un péndulo con toda la masa concentrada a distancia L da el periodo del
  péndulo simple, dentro del 0,1 %.
- La varilla sola da el periodo de una barra que pivota por un extremo.
- `dT/T = ½·dL/L` sale del modelo, no se teclea.
- Determinismo e idempotencia.

**Verificación cruzada.** Se cuelga el péndulo, se cronometran 100 oscilaciones
y Claude compara con lo predicho.

**Verificación humana.** Medir cuántos segundos por día corrige una vuelta de
tuerca, y comprobar que el recorrido útil cubre ±5 min/día.

**Puerta.** Firma humana con las dos medidas escritas: *"100 oscilaciones = X s;
predicho = Y s"*, y el Q anotado en `bench/reloj/pendulo.json`.

**No hacer.** Compensación de temperatura. Primero medir cuánto deriva de verdad.

**Duración.** 2 semanas, de las cuales la mayor parte es esperar a que la
amplitud caiga para medir el Q. **Riesgo.** Bajo.

---

## R2 · Escape y banco de escape

**Objetivo.** Saber cuánta pesa hace falta. **Es el número que dimensiona todo
lo demás y hoy es una incógnita.**

**Entregable.** `core/reloj/escape.py`: geometría del áncora de retroceso
—ángulos de reposo, impulso y caída— y energía por impulso. El banco físico
construido: péndulo, áncora, rueda de escape y una platina provisional.

**Verificación automática**
- El áncora abarca `dientes_escape/4 + 0,5` dientes y las dos paletas son
  simétricas respecto al eje.
- Con reposo cero el modelo devuelve veredicto negativo: un escape sin reposo
  se dispara solo.
- La energía por impulso cubre la pérdida por oscilación del Q medido en R1,
  con el margen declarado.
- Invarianza: la geometría no cambia si se recorre el ciclo al doble de
  velocidad.

**Verificación cruzada.** Se mide el par mínimo con el que el escape arranca y
mantiene la amplitud, y Claude lo compara con lo predicho. **La diferencia es
todo lo que el modelo no sabe del rozamiento de la madera.**

**Verificación humana.** Escuchar. El tictac tiene que sonar parejo; si suena
cojo, las paletas no están simétricas. Y anotar la posición buena de las
paletas como cota de puesta a punto.

**Puerta.** **Firma humana con el par mínimo medido escrito.** Es la puerta más
importante del proyecto: a partir de aquí el tren se dimensiona con un número
real o con uno inventado.

**No hacer.** Seguir a R3 con esta puerta abierta. Todo lo que se corte después
hereda el error.

**Duración.** 2 semanas. **Riesgo.** Descubrir que el abedul no aguanta el
canto de la rueda de escape y hay que pasar a latón.

---

## R3 · Tren y dentado (C12)

**Objetivo.** Que de cinco números salga un tren completo con veredicto.

**Entregable.** `core/reloj/tren.py` y `core/reloj/dentado.py`: búsqueda de
combinaciones de dientes que den la relación exacta, perfil cicloidal de rueda
contra piñón de linterna, distancias entre centros. Las seis envolventes de
`docs/reloj/metodologia.md` §2b, más la de separación entre pernos.
`compile/reloj/` orquestando, con CLI.

**Verificación automática**
- La relación total es **exacta**, sin redondeo: un tren que redondea atrasa.
- Ningún piñón baja de 8 pernos; ninguna separación entre pernos baja del doble
  del diámetro.
- Un caso construido a propósito con relación de contacto < 1 devuelve veredicto
  negativo, no un tren que salta.
- El par llega al escape por encima del mínimo medido en R2, en cada eje.
- Choque rueda-eje: un caso con módulo exagerado devuelve veredicto negativo.
- Cien configuraciones al azar: ninguna produce salida inválida en silencio.
- Determinismo e idempotencia.

**Verificación humana.** Mirar diez trenes dibujados. ¿Las ruedas tienen tamaño
razonable? ¿Las platinas caben en una pared? Un tren absurdo se ve antes de
calcularlo.

**Puerta.** Automática, más revisión visual de diez trenes.

**No hacer.** Optimizar. Que dé trenes válidos basta; elegir el mejor de entre
los válidos es trabajo de R7.

**Duración.** 3 semanas. **Riesgo.** El más técnico. El perfil de rueda contra
linterna no es el cicloidal de manual y hay que deducirlo bien.

---

## R4 · Emisores y plantillas

**Objetivo.** Que el tren calculado salga por la impresora a 1:1.

**Entregable.** `emit/reloj/`: ruedas, piñones, platinas y esfera como `Pieza`,
reutilizando `emit/layout.py` y `emit/template.py`. **La plantilla de taladrado
de platinas**, que comparte con el escribiente. Las galgas, cortadas con las
mismas plantillas.

**Verificación automática**
- El cuadro de calibración mide 100 mm exactos en coordenadas del documento.
- Cada pieza lleva sus siete metadatos.
- La plantilla de taladrado y la galga de centros salen de la **misma** cota:
  un test lo cruza.
- Golden: las plantillas no cambian byte a byte sin querer.

**Verificación humana.** Imprimir en una copistería **distinta** a la del
escribiente, medir la hoja patrón, cargar los factores, reimprimir y medir.
**Esto cierra de paso la puerta pausada de E3b**, que pide dos perfiles de dos
impresoras.

**Puerta.** Firma humana con el segundo perfil de impresora medido.

**No hacer.** Anidado óptimo de piezas. Agrupar lo que cabe.

**Duración.** 1,5 semanas de código; la espera es la copistería. **Riesgo.**
Bajo.

---

## R5 · El movimiento en madera

**Objetivo.** Que ande 30 horas sin pararse.

**Entregable.** Tandas 0 a 3 de `docs/reloj/piezas.md` fabricadas y montadas:
platinas definitivas, tren completo, tambor y pesa. Sin esfera ni agujas.

**Verificación automática.** Ninguna. Esta etapa es física.

**Verificación cruzada.** La pesa real frente a la prevista en R2. Si hace falta
mucha más, el rozamiento del tren completo es mayor que el del banco, y esa
diferencia entra en `bench/reloj/`.

**Verificación humana.** **30 horas seguidas sin pararse.** Binario. Si se para,
se anota en qué punto del ciclo: siempre en el mismo sitio es un pivote o un
engrane; al azar es falta de pesa.

**Puerta.** Firma humana con las 30 horas y la pesa real anotadas.

**No hacer.** Montar la esfera para ver si funciona. Un tren que no anda desnudo
no anda vestido, y con esfera cuesta más diagnosticar.

**Duración.** 3 semanas, buena parte de taller. **Riesgo.** Que un pivote
agarrote y haya que rehacer una platina.

---

## R6 · El reloj completo en la pared

**Objetivo.** Que dé la hora.

**Entregable.** Tanda 4 montada: esfera, agujas, tren de esfera, polea, caja y
tabla de pared. Colgado y regulado.

**Verificación automática.** Ninguna.

**Verificación humana.** **±1 minuto al día durante 7 días**, comparando con el
móvil a la misma hora. Criterio fijado antes de empezar. Se regula con la
tuerca el primer día y se deja correr seis más.

**Puerta.** **Firma humana con la hoja de marcha de 7 días adjunta.** Es la
puerta que valida el proyecto: aquí el reloj existe o no existe.

**No hacer.** Perseguir el segundo. Un reloj de madera a ±1 min/día es un buen
reloj de madera.

**Duración.** 2 semanas, de las cuales 7 días son esperar. **Riesgo.** El de
producto, no el técnico.

---

## R7 · La app

**Objetivo.** Que alguien configure un reloj sin saber de relojería.

**Entregable.** Tres pantallas: configurar (cinco campos), comprobar (el tren
dibujado, los números derivados y el veredicto) y fabricar (descargar el
paquete). Sobre la API y el frontend que ya existen.

**Verificación automática**
- Test extremo a extremo: configurar, previsualizar, descargar.
- Una configuración imposible devuelve el motivo y la sugerencia, no un error.
- El paquete descargado es idéntico al del CLI con los mismos cinco números.

**Verificación humana.** **Tres personas del taller configuran un reloj sin
instrucciones** mientras alguien mira en silencio. Criterio escrito antes: dos
de tres llegan a descargar el paquete sin preguntar nada. Se anota dónde dudan,
no lo que dicen.

**Puerta.** Firma humana con las notas de las tres sesiones.

**No hacer.** Cuentas de usuario, pasarela de pago, panel de administración.

**Duración.** 2 semanas. **Riesgo.** Bajo: son cinco campos, no un lienzo
táctil.

---

## R8 · Dossier y hoja de taller

**Objetivo.** Que alguien ajeno al proyecto monte el reloj.

**Entregable.** Los cinco cuadernos de `docs/reloj/metodologia.md` §4, con las
cotas de puesta a punto y la hoja de marcha de 7 días.

**Verificación automática**
- Todas las piezas del modelo están en la lista de materiales; ninguna sobra.
- Cada paso de montaje referencia piezas que existen.
- El dossier compila para tres configuraciones distintas sin tocar código.

**Verificación humana.** **La prueba del desconocido**: dar el dossier y las
piezas a alguien ajeno y cronometrar el montaje. Cada pregunta es un fallo del
dossier y se anota.

**Puerta.** Firma humana: montaje completado sin ayuda.

**No hacer.** Perseguir la perfección gráfica.

**Duración.** 2 semanas. **Riesgo.** Se subestima siempre.

---

## R9 · Órgano temporal

**Objetivo.** Demostrar que el reloj sirve de base de tiempo a otra máquina.
**Sin fecha: entra cuando haya un autómata que lo pida.**

**Entregable.** `ficha_tiempo.json` emitido con cada diseño, el contrato de eje
comprobado por `core/module.py`, y un autómata mudo —un disco que da una vuelta
y se para— disparado por el eje de 24 h.

**Verificación automática**
- Una `FichaModulo` que pide un eje que el reloj no ofrece es rechazada por
  `Maquina`, con el código que ya existe.
- El par sobrante declarado cubre el demandado por el módulo acoplado.

**Verificación humana.** Mirarlo: a la hora programada, el disco da una vuelta
y se para, y **el reloj no atrasa por ello**. Se comprueba con la hoja de marcha.

**Puerta.** Firma humana. Es la puerta que valida la tesis: una segunda clase de
máquina se acopla sin rehacer nada.

**No hacer.** Acoplar el escribiente como primera prueba. Un disco mudo cuesta
una tarde y aísla el problema.

**Duración.** 2 semanas cuando llegue. **Riesgo.** Que el disparo perturbe al
péndulo, que es justo lo que mide esta etapa.

---

## Resumen

| Etapa | Entregable | Puerta | Semanas |
| --- | --- | --- | --- |
| R0 | Andamiaje y contratos | Automática + fusión a `main` | 0,5 |
| R1 | Péndulo físico | Cruzada, con el periodo medido | 2 |
| R2 | Escape y banco | **Humana, crítica: el par medido** | 2 |
| R3 | Tren y dentado | Automática + visual | 3 |
| R4 | Emisores y plantillas | Humana, segundo perfil de impresora | 1,5 |
| R5 | Movimiento en madera | Humana, 30 h sin pararse | 3 |
| R6 | Reloj en la pared | **Humana, ±1 min/día en 7 días** | 2 |
| R7 | La app | Humana, tres personas del taller | 2 |
| R8 | Dossier y taller | Humana, prueba del desconocido | 2 |
| R9 | Órgano temporal | **Humana, valida la tesis** | sin fecha |

Unas 18 semanas hasta R8, con solape entre R4 y R5. Lo exhibible existe al
final de R6; la app, al final de R7.

**Las tres puertas que no se negocian:** R2 (se sabe cuánta pesa hace falta),
R6 (el reloj da la hora) y R9 (otra máquina se cuelga de él sin rehacer nada).

---

## Lo que el reloj le devuelve al escribiente

No es un proyecto que solo consume. Tres cosas vuelven:

| Qué | De qué etapa | Qué desbloquea allí |
| --- | --- | --- |
| Segundo perfil de impresora | R4 | **Cierra la puerta pausada de E3b** |
| Plantilla de taladrado + galga de centros | R4 | El utillaje que `docs/metodologia.md` pedía y nadie escribió |
| Generador de dentado | R3 | El reductor 3:1 del escribiente |
