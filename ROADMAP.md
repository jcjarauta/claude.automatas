# ROADMAP

Guía de desarrollo de la aplicación. Diez etapas, cada una con entregable,
verificación automática, verificación humana y puerta de salida.

Complementa a `CLAUDE.md` (reglas técnicas) y a `docs/baseline.md` (concepto).

---

## Cómo funciona este roadmap

**La regla de las dos comprobaciones.** Ninguna etapa se cierra con una sola.

| Tipo | Quién | Qué responde |
| --- | --- | --- |
| **Automática** | Claude, con un comando | ¿El código hace lo que dice que hace? |
| **Humana** | Una persona, mirando o midiendo | ¿Lo que dice es lo que queremos? |
| **Cruzada** | Persona mide, Claude compara | ¿El modelo coincide con la realidad? |

Claude no puede juzgar si un trazo se parece a tu letra, si una manivela gira
agradable o si un dossier se entiende. Una persona no puede comprobar a mano que
cien perfiles cierran con continuidad C². Por eso van juntas.

**Verde no es opinión.** Una verificación automática devuelve código de salida 0
o no lo devuelve. Una verificación humana tiene un criterio escrito antes de
mirar, no después.

**Cada etapa dice también qué NO hacer.** Es tan importante como lo que hay que
hacer: la forma más común de hundir este proyecto es construir el marco genérico
antes de tener dos máquinas.

**Protocolo de sesión con Claude**

1. Decir en qué etapa estamos y qué tarea concreta toca.
2. Claude propone el plan y espera aprobación si el cambio es grande.
3. Implementar con test primero si toca `core/`.
4. Cerrar con `ruff check . && mypy core compile && pytest` y decir qué se comprobó.
5. Si un cambio toca un contrato congelado, parar y avisar.

---

## E0 · Andamiaje

**Objetivo.** Que exista un repositorio donde todo lo demás pueda crecer sin fricción.

**Entregable.** Repo con `uv`, ruff, mypy, pytest, estructura de carpetas vacía
según `CLAUDE.md`, y CI que ejecuta las tres cosas en cada push.

**Verificación automática**
```bash
uv sync && uv run ruff check . && uv run mypy core compile && uv run pytest
```
Debe pasar en verde sobre el proyecto vacío. CI en verde sobre un PR de prueba.

**Verificación humana.** Clonar el repo en otra máquina y dejarlo funcionando en
menos de cinco minutos siguiendo solo el README. Si hace falta preguntar algo, el
README está incompleto.

**Puerta.** Automática.

**No hacer.** Docker, cola de trabajos, base de datos, despliegue. Nada de eso hace falta aún.

**Duración.** 1 día. **Riesgo.** Ninguno relevante.

---

## E1 · Contrato de datos

**Objetivo.** Fijar cómo se representan un programa, un módulo y un veredicto.
Todo lo demás dependerá de esto, así que se hace pronto y bien.

**Entregable.** Modelos Pydantic en `core/program.py` y `core/module.py`:
`Programa`, `Pista`, `Evento`, `FichaModulo`, `Veredicto`, `Maquina`.
Más `core/units.py` con constructores con unidad.
Esquema JSON exportado a `docs/schema/`.

**Verificación automática**
- Ida y vuelta: todo modelo serializa a JSON y vuelve idéntico.
- Un `Programa` con un canal continuo y otro con canal de evento validan ambos.
- Un valor sin unidad o con unidad equivocada es rechazado por el validador.
- `mypy --strict` limpio sobre `core/`.

**Verificación humana.** Leer la ficha de módulo y comprobar que se puede
rellenar para tres módulos muy distintos: el brazo del escribiente, una leva de
resistencia y una estación de pedal. Si algún campo sobra o falta, se corrige ahora.

**Puerta.** Firma humana: el modelo de datos se revisa con papel antes de escribir
código encima.

**No hacer.** Implementar todavía las pistas de evento más allá de que el modelo
las admita. El escribiente no las usa.

**Duración.** 2–3 días. **Riesgo.** Un contrato mal puesto aquí se paga en todas
las etapas siguientes.

---

## E2 · Núcleo geométrico

**Objetivo.** Que de una trayectoria salgan tres perfiles de leva válidos, con
veredicto de viabilidad.

**Entregable.** C1 (cinemática inversa del brazo), C2 (síntesis de perfil y offset
por rodillo), C3 (ángulo de presión y curvatura), C4 (cadena de tolerancias).
Sin ninguna salida a archivo todavía: entra dato, sale dato.

**Verificación automática**
- **Cierre periódico**: perfil(0) = perfil(2π) en posición, velocidad y aceleración.
- **Continuidad**: la segunda derivada no salta por encima del umbral.
- **Invarianza a la velocidad**: el perfil no cambia si se recorre la trayectoria
  al doble de velocidad. Es la comprobación de que θ manda y el tiempo no existe.
- **Rama única**: la cinemática inversa no cambia de rama a mitad de ciclo.
- **Undercutting**: un caso construido a propósito con curvatura menor que el
  rodillo debe devolver veredicto negativo, no un perfil autointersectado.
- **Determinismo**: mil ejecuciones del mismo input dan el mismo resultado.
- Tests de propiedad con hypothesis sobre trayectorias generadas.

**Verificación humana.** Mirar diez perfiles dibujados en pantalla junto a su
trayectoria de origen. ¿Tienen forma de leva razonable? ¿El ángulo de presión
está donde se esperaba? Una leva con un pico absurdo se ve antes de calcularla.

**Puerta.** Automática, más una revisión visual de perfiles.

**No hacer.** Optimización. Primero que funcione y dé veredictos correctos; el
reparto fino de grados por curvatura viene en E5.

**Duración.** 1–2 semanas. **Riesgo.** El más técnico del proyecto. Es donde hay
que ir despacio.

---

## E3 · Plantilla en papel

**Objetivo.** Cerrar por primera vez el recorrido completo de digital a físico,
por la vía más barata: copistería y carpintero.

**Entregable.** `emit/template.py`. PDF a escala 1:1 con cuadro de calibración,
semántica de línea, metadatos por pieza, teselado con marcas de registro y modo
de hoja única para plóter.

**Verificación automática**
- El PDF declara tamaño de página y unidades correctas.
- El cuadro de calibración mide exactamente 100 mm en coordenadas del documento.
- Cada pieza lleva sus siete metadatos obligatorios; falta uno y falla el test.
- Las teselas solapan lo declarado y las marcas de registro coinciden.
- Comparación contra PDF de referencia guardado (golden).

**Verificación humana.** **Imprimir de verdad**, en la copistería que se vaya a
usar, y medir el cuadro con un calibre o una regla metálica. Después cortar una
pieza siguiendo la plantilla y comprobar que encaja donde debe.

**Puerta.** Firma humana con la medida escrita: *"cuadro impreso = 100,0 mm ± 0,3"*.

**No hacer.** El dossier completo. Aquí solo la plantilla de corte.

**Duración.** 3–5 días. **Riesgo.** El escalado de impresora. Por eso se verifica
con una regla y no con un test.

---

## E4 · Banco de ensayo y calibración

**Objetivo.** Saber cuánto miente el modelo, y corregirlo con datos propios.

**Entregable.** Banco físico construido. `bench/` con el protocolo escrito y los
datos medidos: kerf por material y espesor, coeficiente de fidelidad, curva de
desgaste. `tests/bench/` que contrasta predicción contra medida.

**Verificación automática**
- Los datos de `bench/` validan contra su esquema y llevan fecha y condiciones.
- El test de contraste pasa: predicción dentro de la tolerancia declarada.
- El kerf se aplica en `emit/`, nunca en `core/`. Test que lo comprueba.

**Verificación cruzada.** Se corta una leva patrón, se monta en el banco, se mide
el movimiento real del seguidor en veinte posiciones y Claude genera el mapa de
error contra lo predicho.

**Verificación humana.** Girar el banco a mano. ¿El seguidor sigue el perfil sin
saltar? ¿Se oye o se nota algún golpe? Eso no sale en ninguna medida.

**Puerta.** Firma humana con el mapa de error adjunto. **Esta es la puerta más
importante del proyecto**: a partir de aquí el modelo es creíble o no lo es.

**No hacer.** Seguir construyendo funcionalidad mientras esta puerta esté abierta.
Si el modelo no predice, todo lo que se apile encima hereda el error.

**Duración.** 2 semanas, de las cuales buena parte es esperar a que se corten y
desgasten piezas. **Riesgo.** Descubrir que hay que rehacer C2 o C3.

---

## E5 · Compilador extremo a extremo

**Objetivo.** Que de un archivo con una escritura salga un paquete de fabricación
completo, con un solo comando.

**Entregable.** `compile/` con CLI. Entrada: trayectoria normalizada. Salida:
tres DXF, la plantilla en PDF, el informe de veredicto y la simulación del trazo.
Incluye el reparto de grados por curvatura y el cálculo de capacidad.

**Verificación automática**
- Golden files: los DXF de los casos de referencia no cambian byte a byte.
- Cien frases generadas al azar: ninguna produce salida inválida en silencio;
  las que no caben devuelven veredicto negativo con motivo.
- Simulación inversa: recorrer los perfiles generados reconstruye la trayectoria
  con error por debajo del umbral.
- Presupuesto de tiempo: compilar una frase típica en menos de 10 segundos.
- El compilador es idempotente y determinista.

**Verificación humana.** **El prototipo escribe una palabra legible.** Se monta
el cartucho, se gira la manivela y se mira el papel. Después se compara con la
escritura original: ¿la reconoce quien la escribió?

**Puerta.** Firma humana con la hoja escrita pegada al informe de la etapa.

**No hacer.** Interfaz. Todavía se trabaja con archivos y CLI.

**Duración.** 2–3 semanas. **Riesgo.** Que el reparto de grados no baste y haya
que volver a la optimización.

---

## E6 · Dossier de montaje

**Objetivo.** Que alguien que no ha estado en el proyecto pueda montar la máquina.

**Entregable.** `emit/dossier.py`. Vistas ortográficas e isométrica con líneas
ocultas, lista de materiales, lista de comercial, secuencia de montaje con vistas
explosionadas, marca de fase cero y hoja de comprobación final.

**Verificación automática**
- Todas las piezas del modelo aparecen en la lista de materiales; ninguna sobra.
- Cada paso de montaje referencia piezas que existen.
- Las vistas se generan sin aristas perdidas (contraste de longitud total de arista).
- El dossier compila para tres máquinas distintas sin tocar el código.

**Verificación humana.** **La prueba del desconocido**: dar el dossier y las
piezas a alguien ajeno al proyecto y cronometrar el montaje sin ayuda. Cada
pregunta que haga es un fallo del dossier, y se anota.

**Puerta.** Firma humana: montaje completado sin ayuda, con la lista de preguntas
resueltas en una segunda versión.

**No hacer.** Perseguir la perfección gráfica. Que se entienda basta.

**Duración.** 2 semanas. **Riesgo.** Bajo, pero se subestima siempre.

---

## E7 · Interfaz de captura y vista previa

**Objetivo.** Que un cliente pueda escribir, ver qué saldrá y aprobarlo, sin ayuda.

**Entregable.** Frontend React con las tres pantallas: escribir, vista previa con
simulación y comprobaciones, y pedido. Captura solo geometría.

**Verificación automática**
- Tests de componente y un test extremo a extremo con Playwright: escribir,
  previsualizar, aprobar.
- **Test de privacidad**: el payload enviado no contiene marcas de tiempo,
  presión ni velocidad. Se comprueba sobre la petición real, no sobre el código.
- Funciona con dedo y con lápiz, en móvil y en tableta.
- Accesibilidad básica: foco, contraste, tamaño de objetivo táctil.

**Verificación humana.** **Cinco personas ajenas al proyecto usan la app sin
instrucciones** mientras alguien mira en silencio. Criterio escrito de antemano:
cuatro de cinco llegan a aprobar un diseño sin preguntar nada. Se anota dónde
dudan, no lo que dicen.

**Puerta.** Firma humana con las notas de las cinco sesiones.

**No hacer.** Pasarela de pago, cuentas de usuario, panel de administración.

**Duración.** 3 semanas. **Riesgo.** Subestimar la captura táctil. Probar pronto
en dispositivo real, no en el navegador de escritorio.

---

## E8 · API, pedidos y producción

**Objetivo.** Que un pedido recorra el camino entero, del cliente al taller.

**Entregable.** FastAPI con persistencia, estado del pedido, cola de fabricación,
generación del paquete y hoja de ruta para el taller. SQLite. Síncrono.

**Verificación automática**
- Tests de integración sobre el flujo completo de pedido.
- Un pedido se puede reconstruir entero desde su registro guardado.
- Idempotencia: reenviar el mismo pedido no duplica nada.
- La llamada a Onshape ocurre **una sola vez** por pedido. Test que lo cuenta.

**Verificación humana.** Recorrer un pedido real de principio a fin cronometrando
cada paso del taller, y anotar los tiempos en la hoja de ruta. Verificar que la
muestra escrita de control acompaña al paquete.

**Puerta.** Firma humana con los tiempos reales medidos.

**No hacer.** Escalar. Un pedido cada pocos días no necesita cola asíncrona.

**Duración.** 2–3 semanas. **Riesgo.** Confundir esta etapa con montar una tienda.

---

## E9 · Piloto con clientes reales

**Objetivo.** Descubrir lo que ningún test detecta.

**Entregable.** Diez pedidos reales entregados. Registro de incidencias,
devoluciones y comentarios. Ajustes derivados.

**Verificación automática**
- Cero pedidos con veredicto negativo que hayan llegado a fabricación.
- Todos los paquetes generados quedan archivados y son reproducibles.

**Verificación humana.** Hablar con los diez clientes. Criterio escrito antes de
empezar: ocho de diez dicen que se parece a su letra, y ninguna devolución por
calidad de fabricación.

**Puerta.** Firma humana con las diez conversaciones resumidas.

**No hacer.** Cambiar la arquitectura por una queja aislada. Esperar al patrón.

**Duración.** 4–6 semanas de calendario. **Riesgo.** El de negocio, no el técnico.

---

## E10 · Segunda clase de memoria y refactor a marco

**Objetivo.** Demostrar que la arquitectura era real, y solo entonces generalizarla.

**Entregable.** Pistas de evento en el modelo de datos, C5 (diagrama de tiempos),
compilador de MIDI a cilindro o disco, y el módulo musical acoplado al escribiente
en el mismo árbol. Después: refactor del núcleo a marco.

**Verificación automática**
- Un `Programa` mezcla pistas continuas y de evento y compila.
- El diagrama de tiempos detecta solapes de arco entre módulos incompatibles.
- **El escribiente sigue pasando todos sus tests sin cambios funcionales** tras el
  refactor. Golden files idénticos.

**Verificación humana.** **Escuchar y mirar a la vez**: la máquina escribe y suena
sincronizada. Y montar el módulo musical en el árbol sin modificar la base.

**Puerta.** Firma humana. Es la puerta que valida la tesis del proyecto.

**No hacer.** Refactorizar antes de que el segundo caso funcione. El orden es
primero que funcione, después generalizar.

**Duración.** 4 semanas. **Riesgo.** Tentación de reescribir el núcleo entero.

---

## Después de E10

La familia de máquinas impulsadas por personas (C6, C7, C8, C9, C10) entra como
etapas E11 en adelante, con la misma estructura. No se planifican en detalle
todavía porque lo aprendido en E1 a E10 va a cambiar sus supuestos.

---

## Plantilla de cierre de etapa

Copiar a `docs/etapas/EN-cierre.md` al terminar cada una.

```markdown
# Cierre de etapa EN · <nombre>
Fecha: <fecha>

## Entregable
<qué existe ahora que antes no>

## Verificación automática
Comando: <comando exacto>
Resultado: <verde / rojo>
Commit: <hash>

## Verificación humana
Criterio fijado antes: <criterio>
Quién lo comprobó: <nombre>
Resultado: <qué se observó, con números si los hay>
Evidencia: <foto, medida, archivo adjunto>

## Desviaciones
<qué salió distinto de lo previsto>

## Decisiones tomadas
<decisiones que afectan a etapas siguientes>

## Deuda aceptada
<qué se deja a medias a propósito y cuándo se retoma>

## Puerta
Abierta / Cerrada — firma: <nombre>
```

---

## Resumen

| Etapa | Entregable | Puerta | Semanas |
| --- | --- | --- | --- |
| E0 | Andamiaje | Automática | 0,2 |
| E1 | Contrato de datos | Humana | 0,5 |
| E2 | Núcleo geométrico | Automática + visual | 1,5 |
| E3 | Plantilla en papel | Humana, con medida | 1 |
| E4 | Banco y calibración | **Humana, crítica** | 2 |
| E5 | Compilador completo | **Humana, con la hoja escrita** | 2,5 |
| E6 | Dossier | Humana, prueba del desconocido | 2 |
| E7 | Interfaz | Humana, cinco usuarios | 3 |
| E8 | API y producción | Humana, tiempos reales | 2,5 |
| E9 | Piloto | Humana, diez clientes | 5 |
| E10 | Segunda memoria y marco | **Humana, valida la tesis** | 4 |

Unas 24 semanas hasta E10, con solape entre etapas. Lo vendible existe al final
de E9; lo que demuestra que esto es una metodología, al final de E10.

**Las tres puertas que no se negocian:** E4 (el modelo predice la realidad),
E5 (la máquina escribe) y E10 (un segundo tipo de máquina se acopla sin rehacer nada).
