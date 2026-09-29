# Cierre de etapa E2 · Núcleo geométrico
Fecha: 2026-09-29

## Entregable
De una trayectoria salen perfiles de leva con veredicto de viabilidad, sin
tocar el disco.

- `core/actors/` — C1. Registro de cinemáticas inversas: `BrazoCincoBarras`
  (dos seguidores, canales x e y) y `PalancaElevadora` (canal z).
- `core/cam/curves.py` — spline periódico, rejilla uniforme, derivada cíclica.
- `core/cam/synth.py` — C2. Curva de paso por inversión cinemática, tangente
  analítica y desplazamiento por el radio del rodillo.
- `core/cam/envelope.py` — C3. Ángulo de presión, radio de curvatura,
  autointersección y `LimitesLeva` como juez enchufable.
- `core/tolerance.py` — C4. Amplificación del perfil al seguidor y del
  seguidor a la punta, con peor caso y composición cuadrática.
- `scripts/dibujar_perfiles.py` — SVG de revisión, sin dependencias nuevas.

## Verificación automática
Comando: `uv run ruff check . && uv run ruff format --check . && uv run mypy core compile && uv run pytest`
Resultado: VERDE — **166 tests** (95 en E1), mypy estricto sin errores en 17
ficheros, lint y formato limpios.

| Requisito del ROADMAP | Dónde |
| --- | --- |
| Cierre periódico en posición, velocidad y aceleración | `test_el_perfil_cierra_en_*` |
| Continuidad de la segunda derivada | `test_la_segunda_derivada_no_da_saltos` |
| Invarianza a la velocidad | tres tests: densidad de muestreo, resolución de salida y ausencia estructural de toda noción de velocidad |
| Rama única | `test_la_rama_no_cambia_a_lo_largo_del_ciclo`, más el cierre de ψ |
| Undercutting con veredicto, no perfil cruzado | `test_un_rodillo_demasiado_grande_produce_undercutting_y_se_detecta` |
| Determinismo | cien ejecuciones comparadas byte a byte, en C1 y en C2 |
| Propiedades con hypothesis | cierre y no autointersección, monotonía del círculo base, distancia exacta al desplazar |

Contrastes contra geometría conocida: con el seguidor quieto la leva es una
circunferencia de radio exacto `base − rodillo`, su radio de curvatura es el
radio base y el ángulo de presión es cero.

## Verificación humana
Criterio fijado antes: diez perfiles dibujados junto a su trayectoria de
origen; ¿tienen forma de leva razonable y el ángulo de presión está donde se
esperaba?

Evidencia: `docs/etapas/E2-perfiles.png`.

Lo que enseña la lámina, que es lo que había que comprobar:

- El ángulo de presión crece de forma monótona con la amplitud pedida al mismo
  círculo base: 8°, 16°, 25°, 34°, 49°. La frontera de 30° cae entre ±12° y ±16°.
- Agrandar el círculo base rescata un caso que no pasaba: ±16° va de 34° con
  base de 40 mm a 26° con base de 60 mm, a cambio de una leva de 145 mm en vez
  de 105. Es la palanca de diseño principal, y se ve.
- El radio del rodillo **no** cambia el ángulo de presión —25° con 4, 10 y 18 mm—
  pero sí come margen de curvatura: ρ/r baja de 9,3 a 3,7 y a 2,1.
- La ley cicloidal enseña sus dos reposos en ψ(θ) y da una leva de forma sana.

Quién lo comprobó: PENDIENTE — firma de la puerta

## Decisiones tomadas
1. **El brazo es un cinco barras**, no un brazo serie hombro-codo. Con las
   levas apiladas en un eje vertical los seguidores pivotan en postes fijos,
   así que los dos ejes motrices tienen que estar anclados a tierra. En un
   brazo serie el codo va montado sobre el hombro y accionarlo desde un poste
   fijo exige un varillaje añadido. Queda enchufable por el registro.
2. **ψ sale desenrollada** de la cinemática inversa. Aguas abajo se interpola
   con un spline y se deriva dos veces; un salto de 2π de `arctan2` destrozaría
   el perfil.
3. **La tangente de la curva de paso es analítica**, no por diferencias
   finitas. La normal que sale de ella desplaza el perfil que se corta, así que
   un error de discretización ahí es material de más o de menos.
4. **El spline es periódico**, no natural. Un spline natural impone segunda
   derivada nula en los bordes, que en un ciclo cerrado es falso y mete un
   artefacto justo en θ=0.
5. **La normal exterior se deduce del sentido de giro** de la curva, no de
   suponer que el centro de la leva queda dentro: una leva muy excéntrica
   puede no encerrar su propio eje.
6. **La autointersección se comprueba sobre el perfil real** con shapely,
   además de la curvatura. La curvatura dice dónde y por qué; shapely dice sí
   o no.
7. **`Seguidor.bien_puesto()`** entra en la librería como constructor. Ver el
   hallazgo de abajo.

## Hallazgo
Dos fallos, ninguno del código, los dos de trazado, y los dos encontrados al
mirar números que no cuadraban.

El primero: con el pivote del seguidor **alineado con el centro de la leva**,
el ángulo de presión sale exactamente 90° en todo el ciclo, para cualquier
amplitud. No era un error de cálculo: el rodillo queda sobre la recta que une
el centro con el pivote, la fuerza de contacto pasa por el pivote y el momento
es cero. Es el error de trazado clásico de un seguidor oscilante y no se ve
hasta que se calcula. La regla —el brazo debe quedar perpendicular al radio,
así que el pivote va a `hypot(radio_base, brazo)` del centro— está ahora en el
constructor `Seguidor.bien_puesto()`, que es donde no se puede olvidar.

El segundo: el test de invarianza a la resolución falló por 0,14 µm. Físicamente
es nada, el kerf del láser es setecientas veces mayor, pero venía de calcular la
normal por diferencias finitas. Se pasó a tangente analítica y el error bajó a
la precisión del coma flotante.

## Deuda aceptada
- La curvatura sigue por diferencias finitas. Solo alimenta un umbral de aviso
  y contrasta contra la circunferencia con 1e-3 de tolerancia relativa. La
  normal, que sí mueve geometría, es analítica.
- No hay optimización ni reparto de grados por curvatura: es de E5, como dice
  el roadmap.
- `cairosvg` se usó solo para mirar el SVG durante el desarrollo. No es
  dependencia del proyecto: el script escribe el SVG a mano.

## Puerta
Automática: CERRADA.
Humana (revisión visual de los diez perfiles): PENDIENTE de firma.
