# Banco de ensayo

Datos medidos, versionados y con fecha. Nunca incrustados en el código.

| Archivo | Qué contiene | Estado |
| --- | --- | --- |
| `kerf.json` | Ancho de corte por material y espesor | **sin medir**, se mide en E4 |
| `impresoras/` | Un perfil por impresora: factores de escala x e y | sin medir, se mide en E3b |

## kerf.json

El kerf es lo que la herramienta se lleva. Si no se compensa, la pieza sale
pequeña justo ese ancho: el láser quema medio kerf a cada lado de la línea, y
una sierra de cinta se lleva el doble. Se compensa en `emit/`, nunca en
`core/` —el núcleo no sabe con qué se va a cortar—, y solo cuando está medido:
con `medido: false` el sistema emite a la línea nominal y lo dice.

Se mide cortando un cuadrado de dimensión conocida en cada material y espesor,
midiendo la pieza resultante y restando. Una medida por combinación, con
fecha: el mismo material en otra máquina da otro número.
