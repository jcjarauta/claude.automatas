# Perfiles de impresora

Un JSON por impresora. Lo genera la interfaz a partir de una medida humana; no
se escribe a mano salvo para corregir una errata.

Una impresora no imprime a escala. El error típico está entre el 0,2 y el 1 %,
y es **sistemático**: la misma máquina con el mismo papel se equivoca siempre
igual. Eso se compensa. La deriva —humedad, fusor, arrastre— no, y por eso el
cuadro de 100 × 100 mm sigue en todas las hojas aunque haya perfil cargado.

## Protocolo

1. Imprimir la hoja patrón **sin ajuste de página**, al 100 %.
2. Medir las reglas largas, la horizontal y la vertical por separado.
   - Con **pie de rey**: la regla de 150 mm. Resolución 0,05 mm → 0,03 %.
   - Con **cinta métrica**: la de 250 mm. Resolución 1 mm → 0,4 %.
   - Nunca sobre el cuadro de 100 mm: leer 100 mm con una regla da ±0,25 mm,
     un 0,25 %, del mismo orden que el error que se busca.
3. Medir también las tres bandas repetidas. Si difieren entre sí más que la
   resolución del instrumento, el error **no es uniforme** y no hay factor que
   lo arregle: esa impresora se rechaza y se dice por qué.
4. Introducir las medidas en la interfaz. El factor es
   `nominal / medido`, uno por eje.
5. **Reimprimir** y comprobar el cuadro. Esto es lo que cierra la puerta: no
   que la impresora sea buena, sino que el sistema sabe corregir la que haya.

## Campos

| Campo | Qué es |
| --- | --- |
| `nombre` | Cómo se la reconoce: copistería, modelo, sala |
| `fecha` | Cuándo se midió. Un perfil viejo se vuelve a medir |
| `formato` | Formato de la hoja patrón usada |
| `papel` | Gramaje y tipo. Papel distinto, arrastre distinto |
| `factor_x`, `factor_y` | Dos, no uno: el avance deforma más que el ancho |
| `medido_con` | `pie_de_rey` o `cinta_metrica`. Fija la incertidumbre |
| `notas` | Lo que no cabe en los demás campos |

Sin perfil el sistema emite igual, con factores 1,0 y el aviso en la hoja de
que no está calibrada.
