# Registro de cambios de los contratos del reloj

El equivalente de `docs/contratos.md` para el reloj: **por qué** cada número
se movió. Los números vivos están en `docs/reloj/contratos.json` y no se
copian aquí.

Una cota que cambia después de haberse dibujado obliga a redibujar, y eso
cuesta. Lo que hace que el coste merezca la pena es que se sepa por qué: si
el motivo no cabe en una línea, el cambio no estaba entendido.

---

## 1.1 · Varilla del péndulo

Tres revisiones, y **ninguna fue una corrección de un error de cálculo**: las
tres son la misma cota que deja de ser una estimación en cuanto la pieza de al
lado tiene ficha. `varilla_largo` es **derivada**, no elegida:

```
varilla_largo = longitud_pendulo_nominal
              - muelle_flexion_a_varilla      (lo que la suspensión se come arriba)
              - lenteja_centro_bajo_varilla   (lo que la lenteja se come abajo)
```

| Fecha | Valor | Qué lo movió | Qué se sabía que no se sabía antes |
| --- | --- | --- | --- |
| 2026-10-02 | 1080 mm | Primer trazo | Nada por abajo ni por arriba: el largo era la longitud del péndulo más holgura |
| 2026-10-02 | 990 mm | Ficha de la **lenteja** (1.2) | El centro de masas de la lenteja cae 44 mm bajo el extremo de la varilla, y el vástago M6 roscado ocupa ese tramo. Desaparece `varilla_sobrante` |
| 2026-10-02 | **935 mm** | Ficha del **muelle** (1.4) | El punto de flexión de un fleje plano está a **mitad del tramo libre**, no en el amarre: 15 mm y no los 40 que decía `varilla_sobre_flexion`, que era un marcador de posición |

**La cadena cierra en 994 exactos**, y lo exige
`tests/reloj/test_contratos_reloj.py`. Mientras falte una ficha aguas arriba o
aguas abajo, el largo seguirá siendo provisional: por eso la varilla no se
corta hasta cerrar la tanda 1 entera.

### Lo que no cambió, y conviene que se vea

| Cota | Valor | Por qué aguanta |
| --- | --- | --- |
| `varilla_ancho` | 15 mm | No entra en la cadena de longitud. Lo decide el rozamiento con el aire, y eso lo mide R1 |
| `varilla_espesor` | 8 mm | Igual: no participa en los 994 |
| `varilla_taladro_cerca` / `_lejos` | 15 / 35 mm | Ambos caen dentro del solape de 40 mm del fleje sobre la varilla, y hay un test que lo comprueba |
| `varilla_vastago_diametro` | 6,2 mm | Paso del M6 con holgura para la cola. Lo fija la pieza comercial |
| `varilla_vastago_profundidad` | 40 mm | Cinco diámetros de empotramiento. La unión trabaja a flexión |

**Qué hay que rehacer**: solo el largo. La pieza es un listón recto, así que
los dos taladros de arriba y el agujero de abajo no se mueven respecto de sus
extremos. En el CAD basta con que `#cota.varilla_largo` esté enlazada: si lo
está, el modelo se regenera solo al subir el CSV nuevo.

---

## 1.4 · Soporte de suspensión

Contrato `suspension` nuevo, 12 cotas. Tres decisiones que no se leen en el
dibujo y que son el motivo de que las cotas sean esas:

- **Los dos tornillos pasan a los lados del fleje, no por él.** De ahí
  `soporte_tornillo_separacion` = 24 con un fleje de 12. Taladrar un fleje de
  0,1 mm es dibujarle la línea por donde va a romper.
- **La placa de apriete existe porque dos tornillos aprietan en dos puntos.**
  Sin ella, el fleje flexa desde donde cada tornillo lo pellizca y el punto de
  flexión deja de estar donde dice el contrato.
- **El canto de abajo del bloque es el datum del péndulo entero.** Montarlo
  1 mm más arriba son 43 s/día. Va rotulado en el boceto, no solo aquí.

`muelle_flexion_a_varilla` está declarada como **aproximación**: el pivote
efectivo de un muelle de suspensión no es exactamente el centro del tramo
libre, depende de la carga. Lo mide R1 en el banco. Si sale distinto, se
corrige ahí y `varilla_largo` se recalcula sola — que es precisamente para lo
que se derivó en vez de elegirse.

**Queda PENDIENTE el anclaje al bastidor**, que es la pieza 1.5 y la primera
cota del reloj que toca algo que todavía no existe.
