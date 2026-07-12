# 🎯 Estrategia para Pablo — Polla Mundialera Colomas y Asociados

**Estado:** cuartos de final jugados (12-jul-2026). Quedan 2 semifinales, 3er
puesto y final, más los premios especiales (campeón/subcampeón/3º, goleador y
mejor jugador), que **todavía no se otorgan**.

**Tu situación:** vas **#12 con 107 pts**. El líder es **Jaime con 136** (+29).

Todo este análisis lo genera el toolkit de agentes en
[`agentes_polla.py`](./agentes_polla.py). Corre `python3 estrategia/agentes_polla.py`
para reproducir cada tabla. Hay un tablero visual de una página en
[`tablero.html`](./tablero.html) (ábrelo en el navegador). Los informes para los
demás jugadores (Martín, José Pablo, Benja, Coni, Caro, Carola Puga) están en
[`INFORMES.md`](./INFORMES.md).

> **Reglas usadas:** puntaje del **reglamento** (Campeón 20 · Subcampeón 15 · 3º 10
> · Goleador 10 · Balón de Oro 10) y **un jugador no puede ganar Goleador y Balón de
> Oro a la vez**. Esto último es clave para Pablo (ver §5).

---

## 1. El cuadro que queda

Semifinalistas: **Francia, España, Inglaterra, Argentina**. Todo lo demás
(incluido tu **Brasil**) ya está eliminado.

| Instancia | Partido | Fecha |
|---|---|---|
| Semifinal 1 | 🇫🇷 Francia vs España 🇪🇸 | 14 jul |
| Semifinal 2 | 🏴 Inglaterra vs Argentina 🇦🇷 | 15 jul |
| 3er lugar | perdedor SF1 vs perdedor SF2 | — |
| Final | ganador SF1 vs ganador SF2 | — |

> Dato clave del cuadro: **España y Francia están en la MISMA semifinal**. Solo
> una de las dos llega a la final; la otra juega por el 3er puesto.

---

## 2. Tus especiales (bloqueados desde el arranque, no se pueden cambiar)

| Predicción | Estado | Vale |
|---|---|---|
| 1º **España** 🇪🇸 | ✅ VIVO (favorito) | tu pilar |
| 2º **Brasil** 🇧🇷 | ❌ **MUERTO** — eliminado | 0 pts, un hueco de −15 permanente |
| 3º **Francia** 🇫🇷 | ✅ VIVO | +10 si Francia termina 3ª |
| Goleador **Mikel Oyarzabal** | ✅ VIVO pero longshot | la bala de plata (ver §5) |
| MVP **Kylian Mbappé** | ✅ VIVO (favorito) | tu mejor especial |

Tu gran lastre es **Brasil de subcampeón**: ese casillero ya no suma nada, y
casi todos tus rivales sí tienen un 2º vivo. Es −15 que arrastras fijo.

---

## 3. La cruda verdad probabilística

Con el Monte Carlo (puntaje del reglamento, regla goleador≠MVP, supuestos
editables en el código):

| Métrica | Pablo |
|---|---|
| P(ganar la polla) | **~0,1 %** |
| P(top-3) | ~0,7 % |
| P(top-5) | ~3,5 % |
| Puesto medio esperado | ≈ #16 |

Ganar la polla **es un tiro muy largo**: vas 12º, 29 abajo, con un especial
muerto (Brasil) y con tus dos cartas de especiales atadas a que Mbappé **no** sea
goleador. Sé realista: el objetivo alcanzable es **escalar al top-5**, y el premio
grande solo llega con la combinación exacta de §5.

> Buenas noticias: **no corres ningún riesgo del último lugar** (la polera de San
> Marino). Estás 32 pts por encima del colista y por encima de media tabla.

---

## 4. Qué debes ALENTAR (esto es lo que de verdad mueve la aguja)

El podio tiene solo 16 desenlaces posibles; enumerándolos exacto, los brackets
que más te sirven son:

1. **España campeón · Inglaterra subcampeón · Francia 3ª** ← tu mejor bracket
2. España campeón · Argentina subcampeón · **Francia 3ª**
3. Inglaterra campeón · España subcampeón · **Francia 3ª**

El patrón que se repite y que tienes que gritar en el sofá:

- ✅ **España gana la semifinal a Francia** (así Francia baja al partido por el 3er puesto).
- ✅ **Francia gana el partido por el 3er puesto** → **Francia 3ª**.
- ✅ **España sale campeona.**
- ✅ **Mbappé se lleva el premio a mejor jugador.**

**Por qué "Francia 3ª" es tan importante:** el líder **Jaime tiene Francia de
subcampeón**. Si Francia llega a la final, Jaime se lleva +15 y se escapa. Si
Francia termina **3ª**, Jaime saca 0 de ahí y **tú** sumas +10. Ese cruce es el
que te acerca. Por eso tu peor pesadilla es **Francia finalista**.

---

## 5. 🔑 La llave maestra: la Bota de Oro

Este es **el** hallazgo del análisis, y la regla de que **el goleador no puede
ser también mejor jugador** lo vuelve aún más filoso. Aun con tu bracket perfecto
(España campeón, Francia 3ª):

| Si el goleador es… | Tu resultado |
|---|---|
| **Mbappé** (lo más probable) — te anula el goleador **y** el MVP | terminas **~#14** |
| **Mikel Oyarzabal** (tu pick) — libera a Mbappé para el Balón de Oro | **terminas #1** 🏆 |

La clave: si **Mbappé gana la Bota de Oro**, no solo falla tu goleador (Oyarzabal),
sino que además **ya no puede ser tu MVP** (nadie gana ambos) → pierdes tus dos
cartas de golpe. Por eso **lo único que te corona campeón de la polla es que
Oyarzabal sea el máximo goleador**: eso te da el goleador *y* deja a Mbappé libre
para el Balón de Oro. Es de baja probabilidad (Mbappé lidera con 8 goles), pero es
tu único camino real al 85 % del pozo, y encaja: si **España gana el título,
Oyarzabal juega 2 partidos más y puede pasar a Mbappé**.

**Tu parlay ganador completo:** España campeón + Francia 3ª + **Oyarzabal máximo
goleador** (que a su vez habilita **Mbappé MVP**).

---

## 6. Lo único que SÍ controlas: tus pronósticos pendientes

Todavía no enviaste pronóstico de semis/final. Envíalos **antes del inicio de
cada partido** (regla 1 del reglamento) y hazlos coherentes con el mundo en que
ganas. En semis acertar el marcador exacto vale 6; en 3er puesto y final, 8.

| Partido | Pronóstico recomendado | Motivo |
|---|---|---|
| SF1 · Francia vs España | **1 – 2** (gana España) | Francia debe caer al 3er puesto |
| SF2 · Inglaterra vs Argentina | **2 – 1** (gana Inglaterra) | Inglaterra subcampeón es tu mejor bracket |
| 3er lugar · Francia vs perdedor SF2 | **2 – 1** (gana Francia) | Francia 3ª: +10 para ti, 0 para Jaime |
| Final · España vs ganador SF2 | **2 – 1** (gana España) | España campeón es tu pilar |

Apostar tus marcadores al escenario donde ganas es la jugada correcta del que
va detrás: si ese mundo ocurre, además te llevas los puntos de partido; si no
ocurre, igual ya estabas fuera de pelea.

---

## 7. Puntaje usado y una nota

Este análisis usa el **reglamento oficial**: Campeón 20 · Subcampeón 15 · 3º 10 ·
Goleador 10 · Balón de Oro 10, y partidos con escala por ronda (semis 3/6, 3er
puesto y final 4/8). Además se aplica la regla de que **un mismo jugador no puede
ganar el Goleador y el Balón de Oro** a la vez.

*(Nota técnica: el pie del ranking del sitio describe otro esquema —MVP 20,
goleador 15— y el `data.json`/`update.py` del repo quedó congelado en fase de
grupos con un tercer esquema. Si el organizador confirma que el MVP vale más de
10, tu Mbappé pesa todavía más. El análisis usa las posiciones reales del ranking
live y el puntaje del reglamento.)*

---

### TL;DR
Vas 12º y ganar es un tiro largo (~0,1 %). Para tener chance: **alienta a España a
ganarlo todo, a que Francia termine 3ª (no finalista) y —la llave— a Oyarzabal
como máximo goleador (que de paso habilita a Mbappé como mejor jugador).** Manda
tus pronósticos pendientes acordes (España y Francia ganando sus partidos).
