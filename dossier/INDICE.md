# Dossier del escribiente

Generado por `uv run --group cad python scripts/dossier_completo.py` · versión **commit e96e892**.

Todo lo que hay en esta carpeta sale de los comandos de abajo; nada se
edita a mano. Las hojas dicen «No medir sobre esta hoja»: lo que se corta
a escala 1:1 son las plantillas (`python -m compile.cli`), que van aparte.

## Comandos y resultado

| Comando | Resultado | Qué es |
| --- | --- | --- |
| `uv run --group cad python scripts/dossier.py` | [dossier.pdf](dossier.pdf) (17 págs.) | Dossier de montaje: portada, índice, explosión de conjunto, vistas, despiece, secuencia, procedimientos, comprobación final |
| `uv run --group cad python scripts/fichas.py bastidor` | [fichas_bastidor.pdf](fichas_bastidor.pdf) (6 hojas) | Lo que no se mueve: base, postes, platos y rodamientos |
| `uv run --group cad python scripts/fichas.py cinco_barras` | [fichas_cinco_barras.pdf](fichas_cinco_barras.pdf) (7 hojas) | El brazo que lleva la punta por el papel |
| `uv run --group cad python scripts/fichas.py entre_puntos` | [fichas_entre_puntos.pdf](fichas_entre_puntos.pdf) (5 hojas) | Lo que sujeta, arrastra y pone en fase el cartucho |
| `uv run --group cad python scripts/fichas.py seguidores` | [fichas_seguidores.pdf](fichas_seguidores.pdf) (5 hojas) | Lo que lee las levas: seguidores, rodillos, sus ejes, topes y muelles |
| `uv run --group cad python scripts/fichas.py amplificador` | [fichas_amplificador.pdf](fichas_amplificador.pdf) (7 hojas) | El cabestrante 8:1: sectores, tambores y ejes de pivote |
| `uv run --group cad python scripts/fichas.py accionamiento` | [fichas_accionamiento.pdf](fichas_accionamiento.pdf) (6 hojas) | La manivela, el volante y el reductor 3:1 |
| `uv run --group cad python scripts/fichas.py levantamiento` | [fichas_levantamiento.pdf](fichas_levantamiento.pdf) (16 hojas) | Del seguidor 3 a la mesa: balancín, bieleta, tirante y mesa |
| `uv run --group cad python scripts/fichas.py portalapiz` | [fichas_portalapiz.pdf](fichas_portalapiz.pdf) (7 hojas) | La punta: tubo, horquilla, pinza, láminas y portaminas |
| `uv run --group cad python scripts/fichas.py cartucho` | [fichas_cartucho.pdf](fichas_cartucho.pdf) (4 hojas) | El metal que enhebra las levas y viaja con ellas: igual en todos los pedidos |
| `uv run --group cad python scripts/fichas.py levas` | [fichas_levas.pdf](fichas_levas.pdf) (2 hojas) | Lo único que se fabrica para cada pedido: la frase del cliente en tres levas |
| `uv run --group cad python scripts/numeracion.py` | [numeracion.txt](numeracion.txt) | Registro de marcas contra lo que existe: 0 diferencias |
| `uv run --group cad python scripts/dibujable.py --todo` | [dibujable.txt](dibujable.txt) | Lo que falta para dibujar cada pieza desde cero: 0 faltas |
| `uv run --group cad python scripts/ver.py --conjunto` | visor OCP CAD | La máquina montada, por grupos |
| `uv run --group cad python scripts/ver.py --conjunto --explosion` | visor OCP CAD | La explosión de conjunto del dossier, en 3D |

## Dónde está cada pieza

En el orden de montaje. La hoja 1 de cada documento de fichas es la de
grupo: comerciales, tornillería y despiece. La 2, el despiece explosionado
pieza a pieza, con el número de cada una. Las fichas de pieza, desde la 3.

### 1. bastidor · G-BAS · [fichas_bastidor.pdf](fichas_bastidor.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-BAS-01 | base | 3 |
| P-BAS-02 | tubo_separador | 4 |
| P-BAS-03 | platina_levas | 5 |
| P-BAS-04 | collar | 6 |
| C-BAS-01 | poste_pivote | 1 |
| C-BAS-02 | rodamiento_arbol | 1 |
| T-BAS-01 | DIN 7991 M3 × 10 · punta roscada de cada poste, sobre el plato 3 | 1 |
| T-BAS-02 | DIN 913 M3 × 4, punta plana · collares | 1 |
| — | sin ficha: plato, rodamiento_manivela | — |

### 2. cinco_barras · G-CBR · [fichas_cinco_barras.pdf](fichas_cinco_barras.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-CBR-01 | brazo_distal | 3 |
| P-CBR-02 | perno_codo | 4 |
| P-CBR-03 | casquillo_punta | 5 |
| P-CBR-04 | brazo_proximal | 6 |
| P-CBR-05 | anillo_proximal | 7 |
| T-CBR-02 | DIN 988 6 × 12 × 0,5 · arandela de cada codo del cinco barras | 1 |
| T-CBR-03 | DIN 913 M3 × 3, punta plana · anillos bajo los proximales | 1 |

### 3. entre_puntos · G-ENT · [fichas_entre_puntos.pdf](fichas_entre_puntos.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-ENT-01 | munon | 3 |
| P-ENT-02 | garra | 4 |
| P-ENT-03 | eje_motriz | 5 |
| C-ENT-01 | arbol_de_levas | 1 |
| C-ENT-02 | muelle_garra | 1 |
| T-ENT-01 | DIN 6799 para eje Ø10 · bajo el muñón y sobre el muelle de la garra | 1 |
| T-ENT-02 | DIN 7 Ø2 × 16 · pasador de la garra | 1 |

### 4. seguidores · G-SEG · [fichas_seguidores.pdf](fichas_seguidores.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-SEG-01 | casquillo_rodillo | 3 |
| P-SEG-02 | placa_tope | 4 |
| P-SEG-03 | seguidor | 5 |
| C-SEG-01 | casquillo_pivote | 1 |
| C-SEG-02 | muelle_seguidor | 1 |
| C-SEG-03 | rodillo_seguidor | 1 |
| T-SEG-01 | DIN 7991 M3 × 30, cortado a 12,5 / 19,5 / 26,5 · ejes de rodillo | 1 |
| T-SEG-02 | DIN 439 M3 (tuerca fina) · ejes de rodillo | 1 |
| T-SEG-03 | DIN 7 Ø3 × 6 · pasadores de tope, de pie en la placa | 1 |
| T-SEG-04 | DIN 913 M2 × 3, punta plana · collares de los seguidores, bajo el muelle | 1 |

### 5. amplificador · G-AMP · [fichas_amplificador.pdf](fichas_amplificador.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-AMP-01 | eje_pivote | 3 |
| P-AMP-02 | calzo_sector | 4 |
| P-AMP-03 | tambor | 5 |
| P-AMP-04 | sector | 6 |
| P-AMP-05 | mordaza | 7 |
| C-AMP-01 | cinta_amplificador | 1 |
| T-AMP-01 | DIN 912 M3 × 16 · sector, calzo y seguidor | 1 |
| T-AMP-02 | DIN 439 M3 (tuerca fina) · unión del sector | 1 |
| T-AMP-03 | DIN 912 M4 × 16 · mordaza al sector, por su ranura | 1 |
| T-AMP-04 | DIN 439 M4 (tuerca fina) · bajo el sector | 1 |
| T-AMP-05 | DIN 913 M3 × 6, punta plana · aprieta la cinta en la mordaza | 1 |
| T-AMP-06 | DIN 912 M2 × 3 · extremos de la cinta en el tambor | 1 |
| T-AMP-07 | DIN 6799 para eje Ø10 · sobre cada tambor | 1 |

### 6. accionamiento · G-ACC · [fichas_accionamiento.pdf](fichas_accionamiento.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-ACC-01 | eje_manivela | 3 |
| P-ACC-02 | casquillo_rueda | 4 |
| P-ACC-03 | volante | 5 |
| P-ACC-04 | manivela | 6 |
| C-ACC-01 | pinon_reductor | 1 |
| C-ACC-02 | rueda_reductor | 1 |
| T-ACC-01 | DIN 913 M3 × 4, punta plana · casquillo de la rueda | 1 |

### 7. levantamiento · G-ELV · [fichas_levantamiento.pdf](fichas_levantamiento.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-ELV-01 | soporte_mesa | 3 |
| P-ELV-02 | biela_mesa | 4 |
| P-ELV-03 | orejeta_mesa | 5 |
| P-ELV-04 | tirante | 6 |
| P-ELV-05 | eje_mesa_fijo | 7 |
| P-ELV-06 | eje_mesa_movil | 8 |
| P-ELV-07 | mesa | 9 |
| P-ELV-08 | bieleta | 10 |
| P-ELV-09 | casquillo_bieleta | 11 |
| P-ELV-10 | apoyo_balancin | 12 |
| P-ELV-11 | balancin | 13 |
| P-ELV-12 | palanca_lapiz | 14 |
| P-ELV-13 | eje_balancin | 15 |
| P-ELV-14 | bulon_tirante | 16 |
| T-ELV-01 | DIN 912 M3 × 16 · apoyos del balancín, del plato 2 | 1 |
| T-ELV-04 | DIN 6799 para eje Ø6 · bulón del tirante | 1 |
| T-ELV-05 | DIN 6799 para eje Ø4 · eje del balancín, por fuera | 1 |
| T-ELV-06 | DIN 6799 para eje Ø1,5 · ejes de la mesa | 1 |
| T-ELV-07 | arandela de presión Ø2 · bieleta en el balancín | 1 |
| T-ELV-08 | DIN 912 M2 × 25 · soportes de la mesa, desde bajo la base | 1 |
| T-ELV-09 | DIN 912 M2 × 6 · mesa a sus orejetas | 1 |

### 8. portalapiz · G-POR · [fichas_portalapiz.pdf](fichas_portalapiz.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-POR-01 | tubo_punta | 3 |
| P-POR-02 | brazo_horquilla | 4 |
| P-POR-03 | poste_horquilla | 5 |
| P-POR-04 | pinza | 6 |
| P-POR-05 | lamina_flexura | 7 |
| C-POR-01 | anillo_lapiz | 1 |
| C-POR-02 | portaminas | 1 |
| T-POR-01 | DIN 913 M3 × 4, punta plana · pinza del portaminas | 1 |
| T-POR-03 | DIN 912 M2 × 4 · pestañas de las láminas | 1 |

### 9. cartucho · G-CAR · [fichas_cartucho.pdf](fichas_cartucho.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| P-CAR-01 | eje_cartucho | 3 |
| P-CAR-02 | separador | 4 |
| C-CAR-01 | pasador_indice | 1 |

### 10. levas · G-LEV · [fichas_levas.pdf](fichas_levas.pdf)

| Marca | Qué | Hoja |
| --- | --- | --- |
| C-LEV-01 | plancha_pom | 1 |
