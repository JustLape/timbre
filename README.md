# Timbre – panašiai skambančių dainų paieška

Kursinis darbas. Programų sistemų projektavimas, Vilnius Tech, 2026 m. rudens semestras.

Sistema pagal vieną pateiktą dainą suranda panašiai **skambančias** dainas – pagal pačios
dainos garsą, o ne pagal atlikėjo žanrą ar klausymo statistiką. Rezultatus galima susiaurinti
pagal tempą ir instrumentalumą, o kiekvienas pasiūlymas paaiškinamas, kodėl jis pateko į sąrašą.

**Būsena: II užduotis (veikiantis prototipas) padaryta.** Pagrindinis modulis – panašumo
rikiavimo modulis – įgyvendintas visas: penkių kriterijų svorinis balas, pasikartojimų šalinimas,
atlikėjo limitas, rezultatų įvairovė, dalinis rezultatas ir paaiškinimai. Sąsaja – komandinė eilutė.

Projekte vartojami ir žodžiai „I/II/III etapas" – tai tie patys dalykai kaip dėstytojo
„I/II/III užduotis" arba „kursinio darbo I/II/III dalis".

### Ką II užduotis pateikia pagal kiekvieną reikalavimą

| Reikalavimas | Kur tai yra |
|---|---|
| 1. Veikianti pagrindinė funkcija | `python -m timbre --song-id t-0000 --tenant bendras` grąžina surikiuotą sąrašą; verslo taisyklės – `domain/scoring.py` ir `domain/selection.py`; keturi klaidų kodai – `domain/errors.py` |
| 2. Aiškus kodas | `domain/` (logika) · `ports/` (sąsaja) · `adapters/` (duomenys) · `app/` (orkestracija) · `cli.py` (sąsaja). Pritaikytas šablonas – Strategy |
| 3. Automatiniai testai | **83 testai**, visi atmintyje: `tests/` aštuoni failai, įprastas, ribinis ir klaidos atvejai plius dešimt atskyrimo testų |
| 4. Kelių klientų palaikymas | Bendras katalogas `bendras` ir dvi paskyros `t-77`, `t-88` su savo įkeltomis dainomis; trys matomumo sritys vienoje vietoje – `adapters/in_memory.py` |
| 5. Paleidimas ir README | Šis failas: įrankiai, konfigūracija, viena paleidimo komanda, testų komanda, pavyzdiniai duomenys, šeši demonstravimo žingsniai |

Pilnas II užduoties aprašymas: [docs/2-uzduotis-prototipas.md](docs/2-uzduotis-prototipas.md).

---

## Reikalingi įrankiai ir versijos

| Įrankis | Versija | Kam |
|---|---|---|
| Python | ≥ 3.11 (išbandyta su 3.14.3) | paleidimui |
| `pytest` | ≥ 7.0 (išbandyta su 9.2.0) | tik testams |

**Paleidimo priklausomybių nėra nė vienos.** `pyproject.toml` turi `dependencies = []`:
kosinusas, `exp` ir `sqrt` skaičiuojami per standartinę biblioteką `math`. Nereikia nei
`numpy`, nei duomenų bazės, nei interneto.

## Konfigūracija

Konfigūruoti nieko nereikia. **API raktų sistema nenaudoja**, todėl jų nustatyti nereikia ir
konfigūracijos failo su raktais nėra. Vienintelis pasirenkamas dalykas – katalogo failo kelias
per `--catalog`; numatytai naudojamas `data/catalog.json`, kuris jau yra repozitorijoje.

## Pradinis paruošimas

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -e ".[dev]"
```

Linux ar macOS aplinkoje antroji komanda yra `source .venv/bin/activate`.

## Paleidimas viena komanda

Atlikus pradinį paruošimą, prototipas pasileidžia viena komanda:

```bash
python -m timbre --song-id t-0000 --tenant bendras
```

Pilnas pagrindinis scenarijus su filtrais:

```bash
python -m timbre --song-id t-0000 --tenant bendras --bpm-min 118 --bpm-max 130 --instrumental-only
```

### Visi argumentai

| Argumentas | Reikšmė |
|---|---|
| `--song-id` | užklausos dainos id. Privaloma nurodyti **arba** jį, **arba** `--title` |
| `--title` | užklausos dainos pavadinimas, kai `song_id` nežinomas |
| `--artist` | atlikėjas, tikslinantis `--title` |
| `--tenant` | **privalomas.** `bendras` – paieška be paskyros; `t-77` arba `t-88` – paskyra |
| `--limit` | rezultatų kiekis, numatyta 10 |
| `--artist-limit` | dainų iš to paties atlikėjo, numatyta 1 |
| `--bpm-min`, `--bpm-max` | tempo filtras |
| `--instrumental-only` | tik instrumentinės dainos |
| `--weights` | svoriai vardais, pvz. `vector=0.7,tempo=0.1` |
| `--catalog` | katalogo failas, numatyta `data/catalog.json` |
| `--json` | išvestis I etapo dokumento JSON forma |
| `--remove` | pašalina paskyros įkeltą dainą; bendro katalogo nepašalina niekas |

Išėjimo kodai: `0` pavyko · `1` sistemos klaida (į `stderr` spausdinama `[KODAS] žinutė`) ·
`2` argumentų klaida.

## Testai

```bash
python -m pytest -q
```

83 testai, visi atmintyje – be tinklo, failų sistemos ir duomenų bazės, todėl užtrunka
mažiau nei sekundę ir demonstracijos duomenų nepaveikia.

Testų skaičius išaugo nuo 37 iki 70 po to, kai testai buvo patikrinti **mutacijomis**: kodas
sąmoningai laužomas po vieną vietą ir tikrinama, ar testai tai pagauna. Pirmas bandymas parodė,
kad 15 iš 18 sulaužymų testai praleidžia – pavyzdžiui, bendro balo dalybos iš svorių sumos
pašalinimo niekas nepagaudavo, nes visuose testuose svorių suma buvo lygiai 1,0. Dabar tos
spragos uždarytos.

83 testai, visi atmintyje. Svarbiausias yra
`tests/test_scoring.py::test_dokumento_pavyzdys_atkuria_visus_sesis_balus`:
jis atkuria patvirtinto I etapo dokumento 3 skyriaus pavyzdį – visus šešis kandidatų balus
(0,908 · 0,900 · 0,883 · 0,877 · 0,720 · 0,945) su tolerancija 0,001. Laukiamos reikšmės
paimtos iš dokumento, ne iš kodo išvesties.

## Pavyzdiniai duomenys

`data/catalog.json` – 679 dainos trijuose kataloguose:

| Katalogas | Dainų | Kas tai |
|---|---|---|
| `bendras` | 607 | Vienintelis atsakymų šaltinis, matomas visiems |
| `t-77` | 52 | Paskyros įkeltos dainos, matomos tik jai |
| `t-88` | 20 | Kitos paskyros įkeltos dainos |

Failas **yra repozitorijoje** (apie 3 MB), todėl nuklonavus nieko generuoti nereikia.

Dokumento pavyzdys (`t-0000` ir kandidatai `t-0001`–`t-0006`) gyvena **bendrame**
kataloge, nes atsakymai imami tik iš jo.

Katalogą galima sugeneruoti iš naujo:

```bash
python scripts/seed_catalog.py
```

## Katalogai ir matomumas

Sistema turi **vieną bendrą katalogą** ir **paskyras**. Tai ne du vienodi dalykai: jie
atsako į skirtingus klausimus, todėl matomumas yra ne vienas, o trys.

| Klausimas | Kas matoma |
|---|---|
| Ką galiu paimti kaip **užklausą**? | bendrą katalogą ir savo įkeltas dainas |
| Ką galiu gauti **atsakyme**? | **tik** bendrą katalogą |
| Ką galiu **pakeisti**? | **tik** savo įkeltas dainas |

Iš vidurinės eilutės seka pagrindinė savybė: **paskyros įkelta daina gali būti tik
klausimas, bet niekada ne atsakymas.** Todėl ji nenuteka kitam net netiesiogiai – per
panašumo rezultatą. Bendras katalogas savo ruožtu yra **tik skaitomas**: jo nepašalina
niekas, nors jis matomas visiems.

Neprisijungęs žmogus paduoda patį `bendras` kaip `--tenant`. Jam „savų dainų" rinkinys
tiesiog tuščias, todėl atskiro „be paskyros" atvejo kode nėra, o `tenant_id` lieka
privalomas be numatytosios reikšmės.

Visos trys sritys sudaromos `adapters/in_memory.py` funkcijose `_readable()`,
`_searchable()` ir `_owned()`; visi kiti metodai kviečia tik jas, todėl „užmiršti
sąlygą vienoje užklausoje" fiziškai nebėra kur.

Tai atitinka patvirtintą I etapo dokumentą, kuriame jau buvo `katalogai: ["t-77",
"bendras"]` ir sakinys „Žyma `bendras` pažymi viešąjį katalogą, kurį mato visi".
**Ko neteigiu:** kad tai tas pats, kas dokumente – dokumentas leidžia ieškoti ir savame
kataloge, o čia atsakymai imami tik iš bendro. Tai sąmoningas nukrypimas.

Generatorius determinuotas (`random.Random(20261113)`), tad tas pats paleidimas visada duoda
baitas į baitą tą patį failą. Tai naudinga ir po demonstracijos: jei `--remove` pašalino
dainą, katalogas atstatomas arba šia komanda, arba `git checkout data/catalog.json`.

Kataloge sąmoningai yra:

- **dokumento rinkinys** – užklausa `t-0000` ir kandidatai `t-0001`…`t-0006` su dokumento 3
  skyriaus požymiais;
- **tyčinis dublikatas** – „Nightfield (Remix)" to paties atlikėjo, kad dublikatų taisyklė
  būtų matoma išvestyje;
- **du klientai** su atskiromis dainomis ir atlikėjais.

**Požymiai yra sugeneruoti, o ne išvesti iš tikro garso.** Formulės ir balų skaičiavimas yra
tikri ir vykdomi užklausos metu, bet vektoriai nėra neuroninio tinklo išvestis. Laukas
`feature_set` (`"synthetic-v1"`) tam ir yra – III etape kataloge galės būti abu rinkiniai.

---

## Demonstravimo žingsniai

1. **Pagrindinis scenarijus.** Filtrai pritaikomi paieškos metu, tada skaičiuojami balai,
   tada atranka, tada paaiškinimai.

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --bpm-min 118 --bpm-max 130 --instrumental-only
   ```

   Išvestyje tikrinama: visų tempas 118–130, visos instrumentinės, nė vienos užklausos
   atlikėjo (`A-1021`) dainos, ne daugiau vienos iš to paties atlikėjo, kiekviena su bent
   dviem paaiškinimais.

2. **Paieška be paskyros, pagal pavadinimą.** Žmogus, atėjęs su nuoroda, `song_id`
   nežino – jis težino atlikėją ir pavadinimą. Rezultatas tas pats.

   ```bash
   python -m timbre --title "Pateikta daina" --artist "A-1021" --tenant bendras
   ```

   Jei pagal pavadinimą rastos kelios dainos, sistema jų **nepasirenka tyliai**: ji
   išvardija jas ir paprašo nurodyti `--song-id`.

3. **Tie patys duomenys, kiti svoriai – kita eilė.** Balai skaičiuojami užklausos metu,
   niekas nėra paruošta iš anksto.

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --weights vector=0.1,tempo=0.8,key=0.1
   ```

4. **Klaidos ir konfliktai.** Keturi klaidų kodai, visi grąžina išėjimo kodą 1.

   ```bash
   python -m timbre --song-id nera-tokios --tenant bendras
   ```

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --weights vector=1.5
   ```

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --weights vector=0,tempo=0,key=0,loudness=0,mood=0
   ```

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --bpm-min 130 --bpm-max 118
   ```

5. **Dalinis rezultatas.** Per siauras filtras negrąžina tuščio sąrašo tyliai – grąžina, ką
   turi, ir nurodo labiausiai apribojusį filtrą.

   ```bash
   python -m timbre --song-id t-0000 --tenant bendras --bpm-min 121 --bpm-max 123 --instrumental-only
   ```

6. **Paskyrų duomenų atskyrimas.** Daina `t-3000` yra paskyros `t-88` įkelta daina.
   Pirma komanda ją randa, antra ir trečia – ne, nors id tiksliai žinomas.

   ```bash
   python -m timbre --song-id t-3000 --tenant t-88 --limit 3
   ```

   ```bash
   python -m timbre --song-id t-3000 --tenant t-77
   ```

   ```bash
   python -m timbre --song-id t-3000 --tenant t-77 --remove
   ```

   Trečioji komanda yra **keitimo** kelias: svetimos dainos pašalinti nepavyksta. Savo
   įkeltą dainą paskyra pašalinti gali:

   ```bash
   python -m timbre --song-id t-3001 --tenant t-88 --remove
   ```

7. **Bendras katalogas yra tik skaitomas.** Daina `t-0001` matoma visiems, bet jos
   nepašalina niekas – nei paskyra, nei neprisijungęs naudotojas.

   ```bash
   python -m timbre --song-id t-0001 --tenant t-77 --remove
   ```

   ```bash
   python -m timbre --song-id t-0001 --tenant bendras --remove
   ```

8. **Įkelta daina niekada negrįžta atsakyme.** Užklausa iš paskyros įkeltos dainos veikia,
   bet rezultatai ateina tik iš bendro katalogo – net pačiai paskyrai.

   ```bash
   python -m timbre --song-id t-2000 --tenant t-77 --limit 5
   ```

9. **Testai.**

   ```bash
   python -m pytest -q
   ```

> **Jei lietuviškos raidės konsolėje atrodo sujauktos,** išvestis perjungiama į UTF-8 pačios
> programos (`cli.py`), bet senesnė Windows `cmd` konsolė gali jų neparodyti. Tada padeda
> `chcp 65001` prieš paleidimą.

---

## Architektūra

```
cli.py  ->  app/search_service.py  ->  domain/*
                      |
              ports/repository.py  <-  adapters/{json_catalog,in_memory}.py
```

| Katalogas | Atsakomybė |
|---|---|
| `domain/` | grynas skaičiavimas: balai, atranka, paaiškinimai. Jokio I/O, tinklo, failų, `print`, `random` ar laiko |
| `ports/` | abstrakti katalogo sąsaja (`typing.Protocol`) |
| `adapters/` | `json_catalog.py` paleidimui, `in_memory.py` testams |
| `app/` | scenarijaus orkestracija ir priklausomybių injekcija |
| `cli.py` | tik `argparse` ir spausdinimas; **tik čia** žinomos konkrečios realizacijos |

Sluoksnių atskyrimą galima patikrinti komanda, o ne tik patikėti žodžiu:

```bash
grep -rn -e sqlite3 -e argparse -e json -e open src/timbre/domain/
```

### Pritaikytas projektavimo šablonas: Strategy

Kiekvienas iš penkių kriterijų yra atskira klasė su `name` ir `score`
(`domain/scoring.py`), o `DEFAULT_STRATEGIES` yra registras, susidedantis iš pačių strategijų
vardų. Svoriai perduodami **vardais**, ne pozicijomis, todėl šeštas kriterijus reiškia vieną
naują klasę ir vieną įrašą registre – nei bendro balo skaičiavimas, nei CLI, nei svorių
apdorojimas nesikeičia.

## Balų skaičiavimas

Penki kriterijai, visi balai tarp 0 ir 1; bendras balas `(Σ wᵢ·balasᵢ) / Σ wᵢ`.

| Kriterijus | Formulė |
|---|---|
| Vektorius | kosinuso panašumas |
| Tempas | `Δ = min(\|b₁−b₂\|, \|2b₁−b₂\|, \|b₁−2b₂\|)`, balas `exp(−(Δ/6)²)` |
| Tonacija | `max(0, 1 − žingsniai/4) × min(pasitikėjimai)` |
| Garsumas | `exp(−\|Δ LUFS\|/6)` |
| Nuotaika | `1 − vidutinis absoliutus skirtumas` tarp bendrų nuotaikos raktų |

Atranka, būtent šia eilės tvarka: **dublikatai** (kosinusas > 0,98 arba sutampa sunormintas
pavadinimas) → **atlikėjo limitas** (užklausos atlikėjas išmetamas visada) → **įvairovė**
(`0,7·balas − 0,3·didžiausias kosinusas su jau atrinktomis`).

Klaidų kodai: `DAINA_NERASTA`, `NULINIAI_SVORIAI`, `NETINKAMAS_SVORIS`, `NETINKAMAS_FILTRAS`.

---

## Nukrypimai nuo I etapo dokumento ir kodėl

Visi penki yra sąmoningi prototipo supaprastinimai, o ne nespėtas darbas.

1. **JSON failas vietoj PostgreSQL su `pgvector`.** Spartos įrodymai pagal pačią užduotį yra
   III etapo darbas. Tekstinis katalogas matomas savo akimis ir nereikalauja bazės kūrimo
   žingsnio prieš paleidimą. Saugykla yra už `CatalogRepository` sąsajos, tad `pgvector` bus
   dar viena tos pačios sąsajos realizacija, nekeičiant pagrindinio modulio. **Ko neteigiu:**
   kad filtrus vykdo duomenų bazė – juos vykdo adapteris, bet **prieš** balų skaičiavimą, o
   tai ir yra I etapo 2 taisyklės invariantas.
2. **Komandinė eilutė vietoj FastAPI.** Užduotis leidžia „paprastą sąsają, API **arba**
   komandinę eilutę". Pagrindinis modulis tas pats; HTTP sluoksnis yra III etapo darbas.
3. **Sugeneruoti požymiai vietoj Essentia neuroninio tinklo.** Modulis niekada nepriklausė
   nuo tinklo: pagal I etapo 3 skyrių jis gauna paruoštus skaičius ir tik skaičiuoja, o iš kur
   atsiranda vektorius, yra adapterio sprendimas. Tai svarbiausias šio modulio projektavimo
   sprendimas. **Ko neteigiu:** kad panašumo kokybė tokia pati – ji dar neišmatuota.
4. **Klientų atskyrimą vykdo programos kodas, ne duomenų bazės eilučių lygio saugumas (RLS).**
   Be PostgreSQL RLS nėra. Riziką, aprašytą pačiame I etapo dokumente – „užtenka vienoje
   užklausoje užmiršti sąlygą" – mažina trys dalykai: `tenant_id` yra privalomas argumentas be
   numatytosios reikšmės kiekviename repozitorijos metode; matomumo sritys sudaromos **trijose**
   privačiose funkcijose `_readable()`, `_searchable()` ir `_owned()`, kurias kviečia visi
   metodai; ir atskiri izoliacijos testai fiksuoja elgesį. **Ko neteigiu:** kad apsaugos
   lygis toks pat kaip RLS – jis žemesnis.
5. **Atsakymai imami tik iš bendro katalogo.** Patvirtintas I etapo dokumentas leidžia
   klientui ieškoti keliuose kataloguose iš karto (`katalogai: ["t-77", "bendras"]`). Čia
   atsakymai imami **tik** iš bendro: paskyros įkelta daina gali būti tik užklausa, bet
   niekada ne atsakymas. Taip ji nenuteka kitam net netiesiogiai – per panašumo rezultatą.
   **Ko neteigiu:** kad tai atitinka dokumentą pažodžiui – nukrypimas sąmoningas, o
   muzikos bibliotekos scenarijui (ieškoti savo kataloge) reikėtų dokumento varianto.

### Trys vietos, kur patvirtintas dokumentas sau prieštarauja

Visos trys rastos tikrinant ir perskaičiuojant dokumento skaičius, ne spėjant.

1. **`cos(K1,K5) = 0,55` yra geometriškai neįmanoma.** Kai `cos(q,K1) = 0,91` ir
   `cos(q,K5) = 0,88`, trikampio nelygybė leidžia tik intervalą `[0,6039; 0,9977]`. Todėl
   kandidatų tarpusavio panašumai (`pairwise`) į `domain` perduodami **kaip duomenys** ir
   niekada neskaičiuojami iš vektorių. Taip dokumento pavyzdys atkuriamas tiksliai
   (eilė K1 → K5 → K4), o CLI ant tikrų vektorių duoda geometriškai suderintą eilę
   K1 → K4 → K5. Tai ne klaida: pavyzdyje tarpusavio kosinusai pateikti kaip ilustratyvūs
   duomenys, ir būtent todėl modulis juos priima kaip įvestį. Tai ir teisingas projektavimo
   sprendimas savaime – tarpusavio panašumus gali pateikti indeksas, kuris juos jau turi.
2. **„Balai mažėja" negali būti tiesa kartu su 7 taisykle.** Dokumento 1 scenarijus sako, kad
   rezultatų balai mažėja, bet to paties dokumento pavyzdys duoda K1 (0,908) → K5 (0,720) →
   K4 (0,877): įvairovės taisyklė sąmoningai perstato mažesnio balo kandidatą į priekį.
   Įgyvendinta 7 taisyklė, nes ji turi ir formulę, ir pilnai suskaičiuotą pavyzdį. Garantija,
   kuri tikrai laikosi ir yra testuojama: **pirmas rezultatas visada yra didžiausio balo.**
3. **Tonacijos pasitikėjimo pagrindimas sako priešingai, nei daro formulė.** Dokumento
   2 taisyklė teigia, kad netiksliai nustatyta tonacija „beveik neturi įtakos balui". Tikrovėje
   svorinėje sumoje su fiksuotu vardikliu `pasitikėjimas → 0` reiškia `tonacijos balas → 0`, t. y.
   **maksimalią baudą**: iki 0,05 bendro balo, o visas skirtumas tarp K1 (0,908) ir K4 (0,877)
   yra tik 0,031. Taigi mechanizmas, aprašytas kaip apsauga, praktikoje gali nulemti eilę – ir
   baudžia būtent tą iškreiptą gitarinę muziką, kurią turėjo ginti. Formulė įgyvendinta taip,
   kaip dokumente; teisingas sprendimas (vardiklį skaičiuoti tik iš kriterijų, kurie turi
   duomenų) yra III užduoties darbas, nes jis keistų patvirtintą balų skaičiavimą.

## Ko sąmoningai nėra – tai III etapas

HTTP API, Docker, PostgreSQL su `pgvector`, Redis, Essentia ir tikras garso apdorojimas,
prisijungimas ir rolės, kokybės atributų įrodymai, našumo matavimai, 100 000 dainų katalogas.

### Iš kur realiame darbe atsirastų dainos

Prototipas to neatsako, bet klausimas akivaizdus, todėl atsakymas užrašytas čia. Patikrinta
2026-11-16.

Paieška **be savo skaičių neįmanoma**: kosinusui reikia abiejų vektorių, o 600 000 dainų
atsiuntimas ir analizė kiekvienai užklausai reikštų apie 300 GB ir nuo 8 valandų iki
7 dienų **vienai** užklausai. Tačiau pats vektorius ir yra būdas katalogo **nekaupti**:
dainai pakanka ~178 baitų (vektorius, `song_id`, atlikėjas, sunormintas pavadinimas ir
penki skaičiai), tad visos 600 000 dainų sutelpa į ~107 MB – maždaug 2 800 kartų mažiau
nei garsas. Garsas po analizės nesaugomas.

Taip pat patikrinta, ko **negalima** nupirkti. Panašumo API egzistuoja ir yra nemokamos,
bet jos matuoja ne garsą: Jamendo `/tracks/similar` – „mostly based on tags", Last.fm
`track.getSimilar` – „based on listening data", ListenBrainz – klausymo sesijos. Garsu
pagrįstą panašumą prieš didelį svetimą katalogą kaip paslaugą teikia **niekas**, ir nė
viena iš jų negrąžina paaiškinimo, kodėl daina panaši. Būtent tai ir yra šio modulio
vieta. **Ko neteigiu:** kad panašumo matas čia naujas – kosinusas su svoriais yra
standartas; naujas yra atrankos ir paaiškinimų sluoksnis virš jo.

III etapo šaltinis, kuris duoda visus penkis kriterijus be jokio garso apdorojimo ir be
licencijos apribojimų (CC0), yra AcousticBrainz iškrovos. Keistųsi tik
`scripts/seed_catalog.py` ir atsirastų dar vienas `CatalogRepository` adapteris –
`domain/` liktų nepaliestas.

## AI panaudojimas

AI naudotas kaip pagalbinis įrankis rašant kodą (testų juodraščiai, `argparse` karkasas,
katalogo generatorius) ir dokumentaciją. Laukiamos testų reikšmės **nėra** AI išvestis:
visi šeši atraminio testo balai, Camelot žingsniai ir įvairovės reikšmės perskaičiuoti pagal
dokumento formules ir sutampa su patvirtintu dokumentu. Visi trys aukščiau aprašyti dokumento
prieštaravimai rasti būtent tikrinant, o ne priimant skaičius aklai.

**Pats pagrindinis modulis AI nenaudoja** – jis gauna paruoštus skaičius ir tik skaičiuoja.
Vektorių gamyba yra atskiras, iš anksto vykdomas etapas.

## Dokumentai

| Užduotis | Dokumentas | Būsena |
|---|---|---|
| I. Projektavimo dokumentas | [docs/1-etapas-projektavimo-dokumentas.md](docs/1-etapas-projektavimo-dokumentas.md) | Pateikta, patvirtinta |
| II. Veikiantis prototipas | [docs/2-uzduotis-prototipas.md](docs/2-uzduotis-prototipas.md) + šis README + kodas | Pateikta |
| III. Galutinis sprendimas ir architektūros dokumentas | – | Rengiama |
