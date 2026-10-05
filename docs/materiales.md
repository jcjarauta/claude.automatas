# Materiales de la plataforma

<!-- generado por scripts/lista_materiales.py, no editar a mano -->

**23 materiales** para una plataforma. Cada pieza fabricada remite a uno (`emit/materiales.py`), y un test lo exige: el mismo material con dos nombres sale en la lista como dos compras.

Barra, tubo y alambre se piden por largo: el de cada pieza más 2 mm de corte. La chapa, por superficie: la caja de cada perfil más 3 mm alrededor, sin anidar. Las levas del cartucho salen de la misma plancha de POM y no cuentan aquí: son del pedido.

| Material | Forma | Se pide | Cantidad | Piezas |
| --- | --- | --- | ---: | --- |
| POM-C negro, plancha de 5 | chapa | plancha 1000 × 1000 × 5; la misma que las levas | 32 741 mm² | sector ×2, seguidor ×3 |
| contrachapado de abedul de 9 | chapa | tablero de abedul de 9, calidad B/BB | 92 928 mm² | platina_levas ×3 |
| nogal americano macizo de 25 | tabla | tabla cepillada de 25, 240 de ancho útil | 73 622 mm² | base ×1 |
| aluminio 5083, chapa de 4 | chapa | chapa de 4 | 12 096 mm² | mesa ×1 |
| chapa de latón de 2 | chapa | chapa CuZn39Pb3 de 2 | 6 917 mm² | separador ×2, placa_tope ×3 |
| chapa de latón de 3 | chapa | chapa CuZn39Pb3 de 3 | 126 566 mm² | brazo_proximal ×2, brazo_distal ×2, palanca_lapiz ×1, manivela ×1, balancin ×1, biela_mesa ×4, brazo_horquilla ×1, calzo_sector ×2 |
| chapa de latón de 4 | chapa | chapa CuZn39Pb3 de 4 | 1 532 mm² | soporte_mesa ×4, poste_horquilla ×1 |
| chapa de latón de 6 | chapa | chapa CuZn39Pb3 de 6 | 13 860 mm² | mordaza ×2, volante ×1, apoyo_balancin ×2 |
| fleje 1.4310 de 0,15 | fleje | fleje inoxidable de muelle, 0,15 | 1 476 mm² | lamina_flexura ×2 |
| barra W10 h6 rectificada | barra | eje de precisión Ø10 h6 CF53, cortado a medida | 277 mm | eje_pivote ×2, eje_manivela ×1, munon ×1, eje_motriz ×1 |
| acero plata Ø1,5 | barra | acero plata Ø1,5 h9 | 324 mm | eje_mesa_movil ×2, eje_mesa_fijo ×4 |
| acero plata Ø4 h6 | barra | acero plata Ø4 h6 | 99 mm | eje_balancin ×1 |
| acero plata Ø6 | barra | acero plata Ø6 h9 | 28 mm | bulon_tirante ×1, perno_codo ×2 |
| cuerda de piano Ø2 | alambre | cuerda de piano Ø2, recta | 86 mm | bieleta ×1 |
| latón, barra de Ø4 | barra | barra de latón Ø4 | 116 mm | tirante ×1 |
| latón, barra de Ø16 | barra | barra de latón CuZn39Pb3 Ø16 | 113 mm | tambor ×2, casquillo_rueda ×1, collar ×9, garra ×1 |
| latón, barra de Ø25 | barra | barra de latón CuZn39Pb3 Ø25 | 35 mm | casquillo_punta ×1, eje_cartucho ×1 |
| latón, barra cuadrada de 16 | barra | barra cuadrada de latón de 16 | 30 mm | pinza ×1 |
| latón, barra de 6 × 5 | barra | pletina de latón 6 × 5 | 84 mm | orejeta_mesa ×2 |
| latón, tubo 13/10,6 | tubo | tubo de latón 13 × 1,2 | 18 mm | tubo_punta ×1 |
| latón, tubo 4/3,1 | tubo | tubo de latón 4 × 0,45 | 37 mm | casquillo_rodillo ×3 |
| latón, tubo 3,2/2 | tubo | tubo de latón 3,2 × 0,6 | 7 mm | casquillo_bieleta ×1 |
| latón, tubo 12/9 | tubo | tubo de latón 12 × 1,5 | 252 mm | tubo_separador ×6 |

## Tornillería y retención

Las cantidades salen de las piezas del listado: si cambia cuántos sectores o collares hay, cambia aquí. Todo inox A2.

| Designación | Cantidad | Para |
| --- | ---: | --- |
| DIN 912 M3 × 16 | 4 | sector, calzo y seguidor |
| DIN 912 M3 × 16 | 2 | apoyos del balancín, del plato 2 |
| DIN 7991 M3 × 30, cortado a 12,5 / 19,5 / 26,5 | 3 | ejes de rodillo |
| DIN 7991 M3 × 10 | 3 | punta roscada de cada poste, sobre el plato 3 |
| DIN 439 M3 (tuerca fina) | 4 | unión del sector |
| DIN 439 M3 (tuerca fina) | 3 | ejes de rodillo |
| DIN 912 M4 × 16 | 2 | mordaza al sector, por su ranura |
| DIN 439 M4 (tuerca fina) | 2 | bajo el sector |
| DIN 913 M3 × 6, punta plana | 2 | aprieta la cinta en la mordaza |
| DIN 913 M3 × 4, punta plana | 9 | collares |
| DIN 913 M3 × 4, punta plana | 1 | casquillo de la rueda |
| DIN 913 M3 × 4, punta plana | 1 | pinza del portaminas |
| DIN 912 M2 × 3 | 2 | extremos de la cinta en el tambor |
| DIN 912 M2 × 5 | 4 | pestañas de las láminas |
| DIN 912 M2 × 8 | 2 | mesa a sus orejetas |
| DIN 912 M2 × 30 | 4 | soportes de la mesa, desde bajo la base |
| DIN 705 Ø10, anillo de ajuste | 2 | bajo cada brazo proximal |
| DIN 6799 para eje Ø10 | 2 | sobre cada tambor |
| DIN 6799 para eje Ø10 | 2 | bajo el muñón y sobre el muelle de la garra |
| DIN 6799 para eje Ø6 | 1 | bulón del tirante |
| DIN 6799 para eje Ø4 | 2 | eje del balancín, por fuera |
| DIN 6799 para eje Ø1,5 | 8 | ejes de la mesa |
| DIN 7 Ø2 × 16 | 1 | pasador de la garra |
| DIN 988 6 × 12 × 0,5 | 2 | arandela de cada codo del cinco barras |
| DIN 7 Ø3 × 6 | 3 | pasadores de tope, de pie en la placa |
| arandela de presión Ø2 | 1 | bieleta en el balancín |
| **total** | **72** | |
