# Procedimientos de taller

Lo que se hace a mano al montar la plataforma y al cambiar de cartucho. El
dossier de montaje (`uv run --group cad python scripts/dossier.py`) lo lee
de aquí tal cual: este archivo es su única fuente. Cada número viene del
contrato, y entre paréntesis va el nombre de la cota.

## Herramientas

| | Para qué |
| --- | --- |
| **Cartucho de calibrar** (C-001…C-003) | Tres discos de POM redondos al radio de diseño de cada canal. Con él puesto, cada seguidor queda en su punto de diseño. Se genera con `uv run python scripts/cartucho_de_calibrar.py` |
| **Galga de láminas de 1,20** (`tope_galga`) | Orientar el collar de cada seguidor |
| Llave Allen de 1,5 | Prisioneros M3 de los collares y del casquillo de la rueda |
| Hoja de trazo patrón (`emit/patron.py`) | Comprobar la fase y el calaje al final |

## 1. Montar los seguidores y orientar los collares

En cada poste, de abajo arriba:

1. **Collar de latón** con su prisionero flojo, y el **muelle de torsión**
   enrollado alrededor:
   - el izquierdo es un muelle **a izquierdas**, porque ese seguidor va al
     revés;
   - la pata fija va en el agujero de la placa de tope, a 14 del poste
     (`muelle_pata_radio`).
2. **Placa de tope**, ya soldada sobre el collar, con el pasador de tope de pie.
3. El **seguidor** con su casquillo igus. La pata móvil del muelle entra en
   su agujero de 12 (`seguidor_muelle_radio`). Encima va el sector, en los
   canales izquierdo y derecho.
4. Monta el **cartucho de calibrar** en fase cero (apartado 3) y gira la
   manivela a la marca FASE 0. Cada rodillo queda apoyado en su disco: el
   seguidor está en su punto de diseño.
5. Gira el collar, con el muelle, hasta que **la galga de 1,20 entra justa**
   entre el pasador de tope y el canto del seguidor. Aprieta el prisionero.
   - Cada 0,3 mm de error son 1° de tope.
   - El tope deja girar el seguidor 4° hacia dentro (`tope_giro`); ninguna
     frase llega a él, porque el compilador lo vigila (`seguidor_contra_tope`).

**Comprobación.** Saca el cartucho de calibrar. Cada seguidor gira hacia
dentro hasta su pasador y se queda ahí. El rodillo no debe entrar en el
pasillo de salida.

## 2. Calar los brazos

Con el cartucho de calibrar todavía puesto, cada seguidor está en su punto
de diseño. Para cada brazo, el procedimiento de `docs/contratos.md` («Dónde
vive el calaje»):

1. Sujeta el brazo a su calaje.
2. Tensa la cinta tirando, desliza la mordaza y apriétala.
3. Comprueba con la hoja de trazo patrón (apartado 4).

## 3. Cambiar el cartucho

El cartucho entra y sale **por detrás**, entre los postes 1 y 2, deslizando.
No hace falta levantar la garra:
- la ranura de la cabeza del eje y la U del muñón van a lo largo de la
  dirección de salida;
- **solo entran en fase cero**;
- girado media vuelta, el cartucho choca con la lengüeta de la garra y no
  entra.

1. Gira la manivela hasta la marca **FASE 0**.
2. Tira del cartucho hacia atrás, recto. Los seguidores se quedan en sus
   topes.
3. Mete el nuevo con el pasador de índice a la vista, mirando como la marca
   grabada. Las levas empujan los rodillos fuera de sus topes en el último
   tramo, de 1 a 3 mm.
4. Comprueba que el cubo apoya en el muñón y que la garra está abajo, con el
   muelle extendido.

Si el cartucho no entra en el último tramo, no está en fase: sácalo, gira
la manivela a la marca y vuelve a meterlo. **No se fuerza.**

## 4. Comprobar la fase cero y el calaje

Pon la hoja de trazo patrón bajo la punta y gira la manivela una vuelta. El
lápiz tiene que caer sobre la línea. Si sale girada o espejada, el cartucho
está mal calado. Si sale desplazada, el que está mal es el calaje de un
brazo: repite el apartado 2.
