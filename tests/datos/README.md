# Archivos que volvieron del CAD

No son datos de banco ni geometría generada: son **archivos reales que
volvieron de Onshape**, guardados tal cual para que el comparador se pruebe
contra lo que de verdad exporta el CAD y no contra lo que yo creo que
exporta. Un lector escrito con expresiones regulares se cae con la primera
variación de formato, y esa variación no aparece en un archivo sintético.

| Archivo | Qué trae | Por qué está |
| --- | --- | --- |
| `platina_levas_cambiada.step` | La platina con el tercer poste y el pivote izquierdo **cambiados de sitio** | Volvió así dos veces seguidas, 2026-10-02. El Ø8 estaba a -58,407° y el Ø10 a -120°, cada uno en el sitio del otro y con su radio correcto: el dibujo se ve perfecto. Es el fallo que justificó leer STEP |
