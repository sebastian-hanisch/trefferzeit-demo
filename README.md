# Hin ist nicht zurück – Trefferzeit einer Irrfahrt auf Netzen – Streamlit-Demo

Erste Demo der Reihe „Irrfahrten auf Netzen: von der Trefferzeit bis zum lokalen Schnitt“ (Bereich Graphentheorie), ihr Ausgangspunkt. Eine **Irrfahrt** (random walk) geht in jedem
Schritt gleich wahrscheinlich zu einem Nachbarn; die **Trefferzeit** (hitting time) H(u,v) ist die erwartete Zahl der Schritte von u bis zum ersten Besuch von v. Die Demo zeigt,
dass Hin- und Rückweg im Allgemeinen verschieden lang sind, dass sich trotzdem alle Plätze widerspruchsfrei reihen lassen, was eine neue Kante ändert und warum Probeläufe
mit Abbruch den Mittelwert verfälschen.

## Warum dieses Problem

Auf einem ungerichteten Netz ist jede Verbindung in beide Richtungen gleich. Man erwartet deshalb leicht, dass auch der Weg von u nach v so lang ist wie der Rückweg. Für die
Irrfahrt stimmt das im Allgemeinen nicht: Auf dem Handnetz „zwei Hallen“ sind es von Platz 0 nach Platz 2 im Mittel 2 Schritte, zurück 22/3. Dieselbe Frage entscheidet, ob eine
neue Tür jeden Weg verkürzt und wie viele Probeläufe man braucht, wenn man H nur schätzen kann.

## Modell

Einfaches, ungerichtetes, zusammenhängendes Netz; in jedem Schritt jeder Nachbar gleich wahrscheinlich, die Irrfahrt bleibt nie stehen (nicht träge). Alle Zeiten sind erwartete
Schritte. Netze:

- **Handnetz „zwei Hallen“:** Dreiecke {0,1,2} und {3,4,5}, eine Tür 2–3 (Grade 2, 2, 3, 3, 2, 2; 7 Verbindungen). Zweite Tür: 5–0.
- **Zwei Gitterhallen a×a** (a = 3 bis 10, 18 bis 200 Plätze, Vierernachbarschaft), eine Tür in Zeile a // 2. Eine zweite Tür ist eine **Ergänzung**: Die vorhandene bleibt.
- **Saal mit Stichgang 21 + 11** als Kontrast (Lutscher-Netz): 21 Plätze, die alle miteinander verbunden sind, daran ein Gang mit 11 Plätzen.
- **Weg mit Schlussstein:** ein Weg, dessen Enden verbunden werden.

Die Hallen sind eine Kulisse; eine belegte Lagerweg-Anwendung gibt es nicht.

## Methodik

- **Trefferzeiten:** Fundamentalmatrix Z = (I − P + 1πᵀ)⁻¹ mit π ∝ Grad, H(u,v) = (Z_vv − Z_uv) / π(v); jedes Ergebnis wird an der Gleichung H(u,v) = 1 + Mittel der H(w,v) über die Nachbarn w geprüft.
- **Gegner zur Schätzung:** H(u,v) ≈ 2m / d_v, roh, mit dem besten Vorfaktor und mit einem eigenen Wert je Zielgrad. Fehlermaß: Median von |Schätzung − H| / H über alle geordneten Paare. Die Faktoren werden auf den bewerteten Paaren selbst angepasst (zugunsten des Gegners), und zwar so, dass genau dieser Median kleinstmöglich wird (bei gerader Anzahl, wie bei den n(n−1) geordneten Paaren immer, ist er das Mittel der beiden mittleren Fehler).
- **Gegner zur Reihung:** mehr Nachbarn; kleinerer π-gewichteter mittlerer Abstand; mehr Nachbarn, bei Gleichstand kleinerer Abstand (Abstände in ganzen Zahlen verglichen). Ein offen gelassenes Paar zählt als nicht richtig.
- **Probeläufe:** Variationskoeffizient (CV) aus zwei Gleichungssystemen, Läufe-Vorgabe R = ⌈(1,96·CV / 0,1)²⌉ (±10 % bei 95 %, Normalnäherung), E[min(T,K)] aus der K-ten Potenz der Übergangsmatrix; abgebrochene Läufe zählen mit K = c·H (gerundet). **Gegner:** der zensurbewusste Schätzer Σ min(T,K) / Zahl der beendeten Läufe. Die Simulation zieht mit SplitMix64 (`trz_irrfahrt_sim.py`).
- **Vorgerechnet** (`tools/vorrechnen.py` → `daten/vorgerechnet.json`): die Zählung über alle kleinen Netze, die Abbruch-Tabelle über alle Paare, der Deckungsgrad der Läufe-Vorgabe und die Streuung der Abbruch-Schätzer.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen dieser Tabellen rechnet `tests/test_claims.py` nach.

### Hin und zurück, eine Reihenfolge

| Frage | Befund |
|---|---|
| Handnetz | H(0,2) = 2, H(2,0) = 22/3; Türschritt H(2,3) = 7 |
| Reihenfolge auf dem Handnetz | 48 von 720 Reihenfolgen sind stimmig („u vor v“ ⇒ H(u,v) ≤ H(v,u)) |
| Zeit zu einem stationär gezogenen Ziel, Handnetz | von jedem Start 323/42 ≈ 7,69; mittlere Trefferzeit über alle geordneten Paare 49/5 = 9,80 (nicht dasselbe) |
| Zwei Hallen a = 8, größere durch kleinere Richtung über alle Paare | Median 1,25, 90-%-Quantil 2,18, Maximum 4,96 |
| Zwei Hallen a = 3 bis 10 | Median 1,23 bis 1,28; 90-%-Quantil fällt von 3,17 (a = 3) auf 2,08 (a = 10); Maximum 4,8 bis 5,5 |
| Saal mit Stichgang 21 + 11 | Median-Verhältnis 13,91, größtes 441 (vom Gangende führt der erste Schritt zwingend zurück) |
| Faustformel 2m/d_Ziel, a = 8 | Median-Fehler 73 %; mit bestem Vorfaktor 39 %; mit eigenem Wert je Zielgrad 31 % |
| Faustformel 2m/d_Ziel, a = 3 bis 10 | roh 61 bis 76 %; mit Vorfaktor 31 bis 39 %; mit Wert je Zielgrad 24 bis 32 % |
| Faustformel 2m/d_Ziel, Saal mit Stichgang | 69 % / 55 % / 11 % |
| Gradregel, a = 8 | von 8 060 asymmetrischen Paaren haben 3 696 (46 %) gleiche Grade; unter denen mit verschiedenen Graden ist die Regel in 90 % richtig (a = 3 bis 10: 89 bis 93 %) |
| Grad, bei Gleichstand π-gewichteter Abstand, a = 8 | 91,3 % aller asymmetrischen Paare richtig, 72 bleiben offen (a = 3 bis 10: 88 bis 92 %) |
| nur der π-gewichtete Abstand, a = 8 | 89,0 % |
| H(π,·) | ordnet auf jedem geprüften Netz (zwei Gitterhallen a = 3 bis 10, Saal mit Stichgang, Handnetz) jedes asymmetrische Paar richtig (Satz) |

### Eine neue Kante

| Frage | Befund |
|---|---|
| Zweite Tür 5–0 auf dem Handnetz | 6 von 30 Trefferzeiten länger (H(0,2): 2 → 64/15); H(0,5): 49/3 → 28/5; mittlere Trefferzeit 49/5 → 508/75; Zeit zum stationär gezogenen Ziel 323/42 → 107/20 |
| Alle 9 182 Ergänzungen der 994 zusammenhängenden, nicht isomorphen Netze mit 3 bis 7 Plätzen (jede fehlende Kante einzeln) | mindestens eine Trefferzeit länger in 9 182 Fällen; zwischen den Endpunkten nie länger oder gleich (0 Fälle) |
| dieselbe Zählung, Mittelwerte | mittlere Trefferzeit länger in 1 490 Fällen (16,2 %), Zeit zum stationär gezogenen Ziel länger in 850 (9,3 %); größter Faktor einer Trefferzeit 9,18; kleinstes Netz mit längerer mittlerer Trefferzeit: 5 Plätze, 7,20 → 7,333 |
| dieselbe Zählung, Anteil länger gewordener geordneter Paare | 60,6 % als Mittel der Anteile je Ergänzung, 60,8 % über alle 374 770 Paare zusammen |
| Zweite Tür auf den Hallen, a = 3 bis 10, jede Zeile außer a // 2 | 25 bis 30 % der geordneten Paare länger; die mittlere Trefferzeit sinkt (a = 8: 555 → 439 bis 468); größter Faktor bis 2,2 (a = 8: bis 2,1) |
| a = 8, neue Tür in Zeile 0 | zwischen ihren Endpunkten 996 → 184 |
| Frei gewählte Kanten (auch nicht gitterförmig), alle fehlenden, a = 3, 4, 5 | die mittlere Trefferzeit wird in 27 %, 17 %, 12 % der Fälle länger (128, 447, 1 144 Ergänzungen) |
| Weg mit Schlussstein | H(Ende, Nachbar) wird von 1 zu n − 1 (der Start ist ein Blatt, der Schritt vorher also erzwungen) |

**Satz und Herleitung** (im Ausklapper „📐 Mathematische Formulierung“): Auf jedem zusammenhängenden, einfachen, ungerichteten Netz ab 3 Knoten wird durch eine neue Kante zwischen bisher
nicht verbundenen Knoten mindestens eine Trefferzeit länger, und die zwischen ihren Endpunkten wird kürzer. Die zwei Schritte folgen aus der mittleren Rückkehrzeit 2m/d_c und aus
H'(a,b) = (H(a,b) + R_ab) / (1 + R_ab) mit R_ab = 1 / (d_a · Fluchtwahrscheinlichkeit). Beide sind hier als kurze Folgerungen hergeleitet; ob sie so in der Literatur stehen, ist nicht geprüft.

### Probeläufe und Abbruch

| Frage | Befund |
|---|---|
| CV über alle geordneten Paare, a = 3 bis 10 | Median 0,98 bis 1,05 (366 bis 428 Läufe) |
| Größte Streuung, a = 8: L(1,0) → L(1,1) | H = 74,86, CV 3,93, 5 940 Läufe; Abbruch nach 3·H: 6,9 % abgebrochen, Erwartungswert 42,0 % des Mittels (zensurbewusst 45,1 %); nach 10·H: 70,9 % |
| Größte Streuung, a = 3 und a = 10, Abbruch nach 3·H (K gerundet, bei genau halben Schritten aufwärts) | 60,1 % des Mittels bei 8,1 % abgebrochen (a = 3); 38,0 % bei 6,9 % (a = 10) |
| Wo liegt das Paar mit der größten Streuung? | a = 3: L(0,0) → L(1,0); a = 4 bis 6: L(0,0) → L(0,1); a = 7 bis 10: L(1,0) → L(1,1) (jeweils das kleinste unter gleich großen) |
| Türschritt, a = 8 | H = 225, CV 1,53, 904 Läufe |
| Saal mit Stichgang, vorletzter → letzter Gangplatz | H = 441, CV 4,48, 7 721 Läufe; Abbruch nach 3·H: 25,5 % des Mittels bei 7,0 % abgebrochen (zensurbewusst 27,4 %); nach 10·H: 61,3 % |
| Handnetz 0 → 1 | H = 14/3, CV 1,83, 1 286 Läufe; Abbruch nach 14 Schritten (3·H): 74,2 % bei 8,7 % abgebrochen; nach 47 Schritten: 97,8 % |
| Drei Paare ferner Ecken, Abbruch nach 3·H | Handnetz 0 → 5: 97,4 %; Gitter 8×8 Ecke zur Gegenecke: 96,6 %; zwei Hallen 8×8 L(0,0) → R(7,7): 97,2 %; abgebrochen 3,1 bis 3,8 % |
| Alle geordneten Paare, zwei Hallen 8×8, Abbruch nach 3·H | kleinster Anteil ab Abstand 4: 59,1 %; ab 8: 74,6 %; ab 10: 79,2 %; ab 12: 83,6 %; ab 14: 88,2 %; ab 15 (Durchmesser 23): 96,5 % |
| Trifft die Läufe-Vorgabe ±10 %? (Paare „größte Streuung“ und „Türschritt“ auf allen angebotenen Netzen, 20 Fälle, je 4 000 Wiederholungen aus der exakten Verteilung) | in 94,7 % bis 95,8 % der Wiederholungen lag das Mittel höchstens 10 % neben H |
| Helfen mehr Läufe gegen den Abbruch-Fehlbetrag? (a = 8, größte Streuung, c = 3, je 4 000 Wiederholungen) | 100 Läufe: der Schätzer mit Abbruch liegt in 90 % der Wiederholungen zwischen 28 % und 57 % von H; 5 000 Läufe: zwischen 40 % und 44 % |

Die Prozentwerte mit Abbruch sind **Erwartungswerte**; eine einzelne Messreihe streut darum. Der Abbruchanteil sagt nicht, wie viel fehlt: bei 6,9 % (Hallen) und 7,0 % (Saal) abgebrochenen
Läufen bleiben 42 % bzw. 26 % des Mittels.

## Befunde und Korrekturen

- **Gleichstände in der Reihungsregel:** Vergleicht man den π-gewichteten Abstand als Gleitkommazahl, entscheidet Rundungsrauschen einen Teil der exakten Gleichstände zufällig. Die Demo rechnet mit der ganzzahligen Summe Σ d_w·Abstand(w,v); bei a = 8 bleiben 72 Paare offen und zählen als nicht richtig.
- **Anpassung der Faktoren:** Bei gerader Anzahl reicht es nicht, den oberen der beiden mittleren Fehler zu minimieren: Im Saal mit Stichgang blieben so mit einem Vorfaktor 57 % statt 55 %. Die Demo minimiert die Summe beider; die Tests vergleichen das auf allen Netzen und Größen der App mit dichten Rastersuchen.
- **Halbe Schritte beim Abbruch:** Auf den Hallen 3×3 ist H beim gezeigten Paar genau 12,5, also 3·H = 37,5. Ohne feste Regel entschiede das letzte Bit des Rechenwegs zwischen K = 37 (59,5 % des Mittels) und K = 38 (60,1 %); die Demo rundet aufwärts.
- **Orakel:** `networkx.resistance_distance` (Version 3.7) wich auf einem dichten Zufallsnetz mit 12 Knoten um rund 0,8 % vom exakten Wert ab (gegen Brüche geprüft). Das Orakel nutzt deshalb eine Spannbaumzählung in Brüchen.

## Ehrliche Grenzen

- Auf dem Handnetz und den Gitterhallen ist die Asymmetrie im Median mäßig; deutlich ist sie auf dem Saal mit Stichgang.
- Die Zahlen zu Asymmetrie, Faustformeln, Reihungsregeln, zweiter Tür und Abbruch gelten für diese Netze. Allgemein gelten nur die Sätze (Reihenfolge, Zufallsziel, neue Kante) unter den Modellannahmen.
- Andere Faustformeln oder Reihungsregeln sind nicht geprüft; die geprüften Reihungsregeln sind Grad, ein Abstandsmittel und ihre Hintereinanderschaltung.
- Die Abbruchzeit ist ein Vielfaches des wahren H, das man in der Praxis vorab nicht kennt.
- Gerichtete oder gewichtete Netze, andere Irrfahrten (etwa mit Neustart) und die Mischzeit sind nicht Teil dieser Demo; bei der trägen Irrfahrt (mit ½ stehen bleiben) werden alle Trefferzeiten doppelt so lang.
- Die Wahl von Start und Ziel per Klick auf die Karte ist nicht mit einem echten Mausklick bestätigt: Geprüft wurde die Verarbeitung eines im Browser ausgelösten Auswahl-Ereignisses; der automatisierte Klick löste keine Auswahl aus. Die Auswahlfelder tun dasselbe.
- **Netze abtasten:** Wer Knoten zieht, indem er eine Irrfahrt laufen lässt, zieht sie auf lange Sicht proportional zum Grad; Umgewichten mit 1/Grad oder Metropolis-Hastings korrigiert das (Gjoka u. a., *A Walk in Facebook*). Dazu die Demos „Raten und Gewichte“, „Metropolis im kleinen Raum“ und „Eindämmung“ des Portfolios.

## Verifikation

- **Handrechnungen** auf dem Handnetz (alle Brüche oben) in `tests/test_trefferzeit.py` und `tests/test_abbruch.py`.
- **Orakel** (`tests/test_oracle_trefferzeit.py`): Trefferzeiten aus Gleichungssystemen in exakten Brüchen und aus der Spektralformel gegen die Fundamentalmatrix, den dünn besetzten Löser und die Widerstandsformel (Tetali) auf 40 Zufallsnetzen; Pendelzeit = 2m·R mit R aus einer Spannbaumzählung in Brüchen (30 Netze); CV und E[min(T,K)] gegen die Momente der Verteilung P(T > t) (30 Netze).
- **Eigenschaften** (`tests/test_eigenschaften_trefferzeit.py`, 30 Zufallsnetze je Eigenschaft): Zyklusidentität, Reihung, Zufallsziel, träge Kette doppelt, Umnummerieren, neue Kante (Rückkehrzeit, Fluchtwahrscheinlichkeit, Kante am Ziel).
- **Simulation:** Blockgenerator gleich SplitMix64, vektorisierte Läufe gleich einer einfachen Schleife, Mittel im Band von vier Standardfehlern.
- **Gegner:** Reihungsregeln gegen eine einfache Schleife; Faktoren am angezeigten Median gegen dichte Rastersuchen auf allen Netzen und Größen der App und gegen ein zweidimensionales Raster auf kleinen Zufallsbeispielen.
- **Claims, Verdikte, Oberfläche:** jede Zahl der Befundtabellen in `tests/test_claims.py` (die Deckungsmessung vollständig neu), Verdikte als reine Funktionen, AppTest (Standard, jeder Button, jedes Preset mit seiner Verdikt-Zeile, Permalink, Randfälle), Layout, Footer, Laufzeit-Importe.
- **Testzahl:** 400 Tests.

## Quellen

- L. Lovász, *Random Walks on Graphs: A Survey* (1993; die Fassungen haben verschiedene Seitenzahlen): Zyklusidentität (Satz 2.4), Reihung (Korollar 2.5), Beispiele zur Monotonie, startunabhängige Zeit zum stationär gezogenen Ziel (Gl. 3.3).
- D. Levin, Y. Peres, E. Wilmer, *Markov Chains and Mixing Times*, 2. Auflage: Zufallsziel-Lemma (Lemma 10.1).
- P. Tetali (1991): Trefferzeiten aus effektiven Widerständen; die Formel ist hier über die Tests geprüft, die Originalarbeit nicht eingesehen.
- M. Gjoka, M. Kurant, C. Butts, A. Markopoulou, *A Walk in Facebook*: Verzerrung der Irrfahrt beim Abtasten, Umgewichten (Zusammenfassung, Abschnitte I und III).

Ein eigener Test gegen Literaturwerte fehlt; die Beispiele (Weg mit Schlussstein, Kreis) sind durch Handrechnung und die Orakel geprüft.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-App: Ansicht, Kernfragen, vier Experimente |
| `trz_netze.py` | **Baustein:** Netze (Handnetz, Gitterhallen mit beiden Türregeln, Saal mit Stichgang, Gitter, Wege) |
| `trz_trefferzeit.py` | **Baustein:** Trefferzeiten (Fundamentalmatrix, je Ziel dicht und dünn besetzt, Widerstandsformel), Rückkehr- und Fluchtgrößen, Prüfung |
| `trz_irrfahrt_sim.py` | **Baustein:** vektorisierte Simulation mit blockweisem SplitMix64 |
| `trz_karte.py` | **Baustein:** Netzkarte (Plotly) |
| `trz_rng.py` | Hausgenerator SplitMix64 (Kopie der Vorlage) |
| `trz_abbruch.py` | Streuung, Läufe-Vorgabe, Abbruch, Schätzer, Verteilung von T |
| `trz_asymmetrie.py` | Asymmetrie, Reihung, Gegner zur Reihung und zur Schätzung |
| `trz_evaluation.py` | Kennzahlen, Verdikte, Kernfragen-Texte |
| `trz_szenario.py` | Netz und neue Kante aus den Einstellungen |
| `trz_daten.py`, `daten/vorgerechnet.json` | vorgerechnete Messwerte |
| `trz_constants.py`, `trz_presets.py`, `trz_layout.py`, `trz_visualization.py` | Regler, Presets und Permalink, fester Kopf, Figuren |
| `tools/vorrechnen.py` | erzeugt `daten/vorgerechnet.json` |
| `tests/` | siehe „Verifikation“ |
| `requirements.txt`, `requirements-dev.txt` | Laufzeit (streamlit, numpy, scipy, plotly); Tests zusätzlich pytest und networkx (Graphen-Atlas) |
| `.github/workflows/tests.yml`, `.gitignore`, `.streamlit/config.toml` | CI, Ausschlüsse, Einstellungen |

## Bewusst nicht umgesetzt

- Mischzeit und Spektrallücke (eigene Demos „Mischzeit exakt“ und „Meinungsbildung“), dazu die weiteren Demos der Reihe: „Pendelzeit“ (Pendelzeit und effektiver Widerstand), „Etiketten“ (zwei Ziele), „Überdeckungszeit“, „Streife“ und „Lokaler Schnitt“ (Irrfahrt mit Neustart).
- Verbund aus mehreren Hallen (nicht gemessen); gerichtete und gewichtete Netze.
- PDF-Export.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Entwickelt mit Python 3.14; die Tests der CI laufen mit Python 3.12.

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Irrfahrten auf Netzen: Trefferzeit bis Schnitt](https://sebastianhanisch.net/konzepte-irrfahrten.html).
