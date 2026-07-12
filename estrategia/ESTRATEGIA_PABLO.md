# 🎯 Estrategia para Pablo — Polla Mundialera Colomas y Asociados

**Estado:** cuartos de final jugados (12-jul-2026). Quedan 2 semifinales, 3er
puesto y final, más los premios especiales (campeón/subcampeón/3º, goleador y
mejor jugador), que **todavía no se otorgan**.

**Tu situación:** vas **#12 con 107 pts**. El líder es **Jaime con 136** (+29).

Todo este análisis lo genera el toolkit de agentes en
[`agentes_polla.py`](./agentes_polla.py). Corre `python3 estrategia/agentes_polla.py`
para reproducir cada tabla. Hay un tablero visual de una página en
[`tablero.html`](./tablero.html) (ábrelo en el navegador).

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

Con el Monte Carlo (40.000 simulaciones, supuestos editables en el código):

| Esquema de puntaje | P(ganar) | P(top-2) | P(top-3) | Puesto medio |
|---|---|---|---|---|
| Reglamento (MVP=10) | **~0,1 %** | ~0,3 % | ~0,7 % | ≈ #15 |
| Dashboard (MVP=20) | **~0,3 %** | ~0,6 % | ~2,5 % | ≈ #15 |

Ganar la polla **es un tiro muy largo**: vas 12º, 29 abajo, con un especial
muerto y compartiendo tus mejores aciertos (España 1º, Mbappé MVP) con varios
rivales, así que esos no te despegan de ellos. Sé realista: el objetivo
alcanzable es **escalar al top-5/7**, y el premio grande solo llega con la
combinación exacta de §5.

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

Este es **el** hallazgo del análisis. Aun con tu bracket perfecto (España
campeón, Francia 3ª) y con Mbappé de MVP:

| Si el goleador es… | Tu resultado |
|---|---|
| **Mbappé** (lo más probable, y es el pick de Jaime y Juanco) | terminas **~#5** |
| **Mikel Oyarzabal** (tu pick) | **terminas #1** 🏆 |

Traducción: tu podio + MVP te suben hasta el 5º puesto, pero **lo único que te
corona campeón de la polla es que Oyarzabal gane la Bota de Oro**. Es de baja
probabilidad (Mbappé lidera con 8 goles), pero es tu único camino real al 85 %
del pozo, y encaja con lo demás: si **España gana el título, Oyarzabal juega 2
partidos más y puede pasar a Mbappé** como goleador.

**Tu parlay ganador completo:** España campeón + Francia 3ª + Mbappé MVP +
**Oyarzabal máximo goleador**.

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

## 7. ⚠️ Acción #1: aclarar el puntaje de especiales

Hay una **contradicción entre las fuentes** que cambia cuánto vale tu Mbappé MVP:

| | Campeón | Subc. | 3º | Goleador | **MVP** |
|---|---|---|---|---|---|
| **Reglamento PDF** | 20 | 15 | 10 | 10 | **10** |
| **Pie del ranking (app)** | 25 | 15 | 10 | 15 | **20** |

Te conviene muchísimo que rija el esquema del **dashboard** (MVP=20), porque tu
Mbappé es favorito. **Pregúntale al organizador cuál manda** — no cambia lo que
debes alentar, pero sí cuánto pesa tu mejor carta.

*(Nota técnica: el `data.json`/`update.py` del repo quedó en fase de grupos y usa
un tercer esquema, más simple, distinto al del sitio live. El análisis usa las
posiciones reales del ranking live.)*

---

### TL;DR
Vas 12º y ganar es un tiro largo (~0,1–0,3 %). Para tener chance: **alienta a
España a ganarlo todo, a que Francia termine 3ª (no finalista), a Mbappé como
mejor jugador y —la llave— a Oyarzabal como goleador.** Manda tus pronósticos
pendientes acordes (España y Francia ganando sus partidos) y confirma con el
organizador si el MVP vale 10 o 20.
