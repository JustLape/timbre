# II užduotis: veikiantis prototipas

Timbre — panašiai skambančių dainų paieška pagal patį dainos garsą.
Kursinis darbas, Programų sistemų projektavimas, Vilnius Tech, 2026 m. rudens semestras.

Šis dokumentas aprašo, **kas padaryta ir kodėl būtent taip**. Kaip paleisti — [README.md](../README.md).
Ką buvo planuota — [I užduoties projektavimo dokumentas](1-etapas-projektavimo-dokumentas.md).

---

## 1. Ką reikėjo padaryti ir kas padaryta

| Reikalavimas | Kas tai įgyvendina |
|---|---|
| Veikianti pagrindinė funkcija su verslo taisyklėmis ir klaidos apdorojimu | `cli.py` → `app/search_service.py` → `domain/*`; penkios taisyklės, keturi klaidų kodai |
| Logika atskirta nuo sąsajos ir infrastruktūros | `domain/` · `ports/` · `adapters/` · `app/` · `cli.py` |
| Bent 3 pagrindinio modulio testai + bent 1 izoliacijos | 70 testų septyniuose failuose, iš jų 5 izoliacijos |
| Bent du klientai, kurių duomenų negalima nei perskaityti, nei pakeisti | `t-77` ir `t-88`; `_visible()` viena vieta |
| Paleidimas ir README | Viena komanda, nulis paleidimo priklausomybių |

**Apimtis sąmoningai maža.** Prototipas rodo pagrindinį modulį nuo įvesties iki rezultato.
Kokybės atributų įrodymai, prisijungimas, rolės ir konteinerizavimas pagal užduotį numatyti
III užduočiai, todėl čia jų nėra.

---

## 2. Pagrindinis modulis: panašumo rikiavimo modulis

**Svarbiausias jo projektavimo sprendimas:** modulis **nieko neparsiunčia pats**. Jis gauna
paruoštus skaičius ir tik skaičiuoja — nesikreipia į internetą, neatidaro garso failų,
nesirašo į duomenų bazę. Dėl to testui pakanka kelių skaičių, sugalvotų ranka, ir jie veikia
per milisekundes.

Tai patikrinama komanda, o ne patikima žodžiu:

```bash
grep -rn -e sqlite3 -e argparse -e json -e open src/timbre/domain/
```

Rezultatas tuščias. `domain/` importuoja tik `math`, `re`, `enum`, `dataclasses`,
`collections.abc` ir `typing`.

### Veikimo eiga

```
1. Svorių patikra                  app/search_service.py
2. Filtrų ir limitų patikra        app/search_service.py
3. Užklausos daina                 ports/repository.py -> adapters/
4. Kandidatai, filtrai PAIEŠKOS METU   adapters/in_memory.py
5. Kandidatų tarpusavio kosinusai  app/search_service.py
6. Balai ir rikiavimas             domain/scoring.py
7. Dublikatai -> atlikėjo limitas -> įvairovė   domain/selection.py
8. Paaiškinimai                    domain/explain.py
9. Rezultatas                      domain/models.py
```

Filtrai taikomi **paieškos metu, ne po jos**. Jei pirma imtume 200 artimiausių, o tik paskui
išmestume netinkamas, liktų vos kelios. Tai I užduoties 2 taisyklės invariantas.

---

## 3. Balų skaičiavimas

Penki kriterijai, visi balai tarp 0 ir 1. Bendras balas — svorinė suma, dalijama iš svorių sumos,
todėl rezultatas visada lieka intervale [0; 1].

| Kriterijus | Formulė | Svoris |
|---|---|---|
| Vektorius | kosinuso panašumas | 0,70 |
| Tempas | `Δ = min(\|b₁−b₂\|, \|2b₁−b₂\|, \|b₁−2b₂\|)`, balas `exp(−(Δ/6)²)` | 0,10 |
| Tonacija | `max(0, 1 − žingsniai/4) × min(pasitikėjimai)` | 0,05 |
| Garsumas | `exp(−\|Δ LUFS\|/6)` | 0,05 |
| Nuotaika | `1 − vidutinis absoliutus skirtumas` tarp **bendrų** raktų | 0,10 |

**Du dalykai, kuriuos lengva supainioti.** Tempo formulė yra kvadratinė, garsumo — ne.
Prie Δ = 2 tempas duoda 0,895, o garsumas 0,717. Abi formos yra iš patvirtinto dokumento.

**Tempo dvigubinimas.** Tempą nustatantys algoritmai dažnai klysta lygiai dvigubai, todėl
skirtumas skaičiuojamas trimis būdais ir imamas mažiausias. 124 ir 62 BPM gauna balą 1,0.

**Camelot žingsniai:** `min(|n₁−n₂|, 12−|n₁−n₂|) + (1 jei raidės skiriasi)`.
Patikrinta: 8A↔8A = 0, 8A↔9A = 1, 8A↔3B = 6. Nežinoma tonacija duoda balą 0.

**Svoriai.** Kiekvienas nuo 0 iki 1 imtinai; už ribų — `NETINKAMAS_SVORIS`. Jei suma lygi
nuliui — `NULINIAI_SVORIAI`, nes visų dainų balas būtų 0 ir eilė taptų atsitiktinė.

---

## 4. Atranka

Eilės tvarka yra verslo taisyklė, ne įgyvendinimo detalė:

1. **Dublikatai** — kandidatas atmetamas, jei su jau atrinkta daina sutampa sunormintas
   pavadinimas **arba** tarpusavio kosinusas **> 0,98** (riba griežta).
2. **Atlikėjo limitas** — užklausos atlikėjas išmetamas visada; iš kitų ne daugiau nei limitas.
3. **Įvairovė (MMR)** — `0,7·balas − 0,3·didžiausias kosinusas su jau atrinktomis`.

**Dalinis rezultatas.** Jei rezultatų mažiau nei prašyta, tuščias sąrašas negrąžinamas tyliai:
grąžinama, kas yra, pažymima `dalinis_rezultatas` ir nurodomas labiausiai apribojęs filtras.
Tas laukas užpildomas **tik tada, kai atmetė pats filtras** — ne dublikatai ar atlikėjo limitas.

---

## 5. Architektūra

```
cli.py  ->  app/search_service.py  ->  domain/*
                      |
              ports/repository.py  <-  adapters/{json_catalog,in_memory}.py
```

| Sluoksnis | Atsakomybė |
|---|---|
| `domain/` | grynas skaičiavimas; jokio I/O |
| `ports/` | abstrakti katalogo sąsaja (`typing.Protocol`) |
| `adapters/` | `json_catalog.py` paleidimui, `in_memory.py` testams |
| `app/` | scenarijaus orkestracija, priklausomybių injekcija |
| `cli.py` | tik `argparse` ir spausdinimas; **tik čia** žinomos konkrečios realizacijos |

`JsonCatalogRepository` užklausų logikos nedubliuoja — jis naudoja `InMemoryCatalog` vidumi,
o pats atsako tik už failą. Taip ta pati logika egzistuoja vienoje vietoje.

### Pritaikytas projektavimo šablonas: Strategy

Kiekvienas iš penkių kriterijų yra atskira klasė su `name` ir `score` (`domain/scoring.py`),
o `DEFAULT_STRATEGIES` yra registras, susidedantis **iš pačių strategijų vardų**. Svoriai
perduodami vardais, ne pozicijomis.

**Kodėl tai nėra prilipintas šablonas.** Šeštas kriterijus reiškia vieną naują klasę ir vieną
įrašą registre — nei bendro balo skaičiavimas, nei svorių apdorojimas, nei CLI nesikeičia.
Pozicinis `--weights 0.7,0.1,0.05,0.05,0.1` būtų įkalęs „kriterijų yra lygiai penki".

---

## 6. Klientų duomenų atskyrimas

Du klientai: `t-77` (59 dainos) ir `t-88` (21 daina). Kataloge jie sąmoningai turi **tuos pačius
`song_id`**, o `t-88` turi dainų, kurių `t-77` neturi (kataloge `t-0100`, testuose `s-999`) — tai natūraliausias
pažeidimo kelias, kai svetimas id yra žinomas.

Atskyrimą užtikrina trys dalykai:

1. **`tenant_id` yra privalomas argumentas be numatytosios reikšmės** kiekviename repozitorijos
   metode. Jo pamiršti neįmanoma — be jo kvietimas tiesiog nesuveikia.
2. **Matomumo sąlyga sudaroma vienoje privačioje funkcijoje** `_visible()`
   (`adapters/in_memory.py`), kurią kviečia visi metodai. „Užmiršti sąlygą vienoje užklausoje"
   nebėra kur.
3. **Atskiri testai** fiksuoja ir skaitymo, ir keitimo kelius.

Keitimo kelias yra `--remove`: svetimos dainos pašalinti nepavyksta. Svetimas id grąžina tą patį
`DAINA_NERASTA`, kaip ir visai nesanti daina — taip sąmoningai neatskleidžiama, kad tas id
kataloge egzistuoja.

**Ko neteigiu:** kad apsaugos lygis toks pat kaip duomenų bazės eilučių lygio saugumo (RLS).
Jis žemesnis. RLS numatytas III užduočiai.

---

## 7. Testai

70 testų, visi atmintyje. Jokio tinklo, failų sistemos ar duomenų bazės — todėl jie veikia per
0,3 s ir demonstracijos duomenų nepaveikia.

| Failas | Ką tikrina |
|---|---|
| `test_scoring.py` | penki kriterijai, svorių validacija, **dokumento pavyzdys** |
| `test_selection.py` | dublikatai, atlikėjo limitas, įvairovė |
| `test_search_service.py` | visas scenarijus, dalinis rezultatas, klaidų keliai |
| `test_tenant_isolation.py` | skaitymo ir keitimo atskyrimas |
| `test_explain.py` | paaiškinimų garantija |
| `test_models.py` | požymių patikros |
| `test_cli.py` | argumentų apdorojimas |

**Atraminis testas** `test_dokumento_pavyzdys_atkuria_visus_sesis_balus` atkuria patvirtinto
dokumento 3 skyriaus pavyzdį — visus šešis balus (0,908 · 0,900 · 0,883 · 0,877 · 0,720 · 0,945)
su tolerancija 0,001. Laukiamos reikšmės paimtos iš dokumento, ne iš kodo išvesties.

### Testai patikrinti mutacijomis

Žalia testų suite dar nereiškia, kad testai ką nors tikrina. Todėl kodas buvo sąmoningai
laužomas po vieną vietą ir tikrinama, ar testai tai pagauna.

**Pirmas bandymas: 15 iš 18 sulaužymų testai praleido.** Pavyzdžiai:

- bendro balo dalyba iš svorių sumos — nepagauta, nes visuose testuose svorių suma buvo
  lygiai 1,0, tad dalyba neturėjo jokio efekto;
- `camelot_steps` be raidės baudos ir be rato apsisukimo;
- dublikatų riba `>=` vietoj `>`;
- `NETINKAMAS_FILTRAS` — vienas iš keturių klaidų kodų — neturėjo nė vieno testo.

Po spragų užpildymo tos pačios mutacijos **pagaunamos visos**. Testų skaičius išaugo nuo 37
iki 70. Tai buvo vertingiausias darbas visame prototipe: be jo testai būtų atrodę geri, bet
nieko neįrodinėję.

---

## 8. Nukrypimai nuo I užduoties ir kodėl

Visi keturi yra sąmoningi prototipo supaprastinimai, leidžiami užduoties („visų I etape
išvardytų funkcijų šiame etape nereikia").

| # | Nukrypimas | Pagrindimas |
|---|---|---|
| 1 | JSON failas vietoj PostgreSQL su `pgvector` | Spartos įrodymai — III užduotis. Tekstinis katalogas matomas savo akimis. Saugykla už `CatalogRepository` sąsajos, tad `pgvector` bus kita tos pačios sąsajos realizacija |
| 2 | Komandinė eilutė vietoj FastAPI | Užduotis leidžia „paprastą sąsają, API **arba** komandinę eilutę" |
| 3 | Sugeneruoti požymiai vietoj Essentia tinklo | Modulis niekada nepriklausė nuo tinklo: jis gauna paruoštus skaičius. Iš kur vektorius — adapterio sprendimas |
| 4 | Klientų atskyrimą vykdo kodas, ne RLS | Be PostgreSQL RLS nėra. Riziką mažina privalomas argumentas, viena matomumo funkcija ir testai |

**Ko neteigiu:** kad filtrus vykdo duomenų bazė — juos vykdo adapteris, bet **prieš** balų
skaičiavimą. Kad panašumo kokybė tokia pati kaip su tikru tinklu — ji dar neišmatuota.
Kad apsauga tokio pat lygio kaip RLS — ji žemesnė.

---

## 9. Ką pakeitė pats prototipas

Rašant kodą paaiškėjo dalykų, kurių projektuojant nebuvo matyti. Tai ir yra prototipo vertė.

1. **`Features` laukai pakeisti.** Buvo `valence`, `energy`, `instrumental: bool`. Su jais
   dokumento pavyzdžio atkurti neįmanoma, nes dokumento įvestis yra vardinės nuotaikų
   tikimybės. Pakeista į `moods: dict[str, float]`, o `instrumental_only` filtras dabar skaito
   `moods`, todėl instrumentalumas turi vieną tiesos šaltinį, ne du.

2. **`pairwise` perduodami kaip duomenys.** Dokumente `cos(K1,K5) = 0,55` yra geometriškai
   neįmanoma: kai `cos(q,K1) = 0,91` ir `cos(q,K5) = 0,88`, trikampio nelygybė leidžia tik
   intervalą [0,6039; 0,9977]. Todėl kandidatų tarpusavio panašumai į `domain` **priimami
   argumentu** ir niekada neskaičiuojami iš vektorių. Taip dokumento pavyzdys atkuriamas
   tiksliai, o CLI ant tikrų vektorių duoda geometriškai suderintą eilę. Tai ir teisingas
   sprendimas savaime: tarpusavio panašumus gali pateikti indeksas, kuris juos jau turi.

3. **Kiekvienai dainai reikia savos statmenos ašies.** Pirmas katalogo generatoriaus variantas
   visiems vektoriams naudojo tą pačią statmeną ašį. Tada visos dainos gulėjo vienoje
   plokštumoje, jų tarpusavio kosinusai buvo apie 0,997, ir dublikatų taisyklė išmesdavo
   **visus** kandidatus — paieška grąžindavo tuščią sąrašą. Dabar `c_i = cos_i·q + sin_i·e_i`
   su skirtingomis `e_i`, todėl `cos(c_i, c_j) = cos_i · cos_j`.

4. **„Labiausiai ribojusiam filtrui" reikia nefiltruotų kandidatų kiekio.** Pirmas variantas jį
   spėjo kaip didžiausią `survivors_per_filter` reikšmę. Kai visi filtrai aktyvūs ir atmeta tą
   patį rinkinį, visos reikšmės lygios, ir sistema rašydavo „filtrai nieko neatmetė", nors
   atmesdavo. Todėl `CandidatePool` gavo privalomą lauką `visible_count`.

---

## 10. Trys vietos, kur patvirtintas dokumentas sau prieštarauja

Visos rastos perskaičiuojant dokumento skaičius.

1. **`cos(K1,K5) = 0,55` neįmanoma** — žr. 9 skyriaus 2 punktą.
2. **„Balai mažėja" ir 7 taisyklė vienu metu neįmanomi.** 1 scenarijus sako, kad rezultatų
   balai mažėja, bet to paties dokumento pavyzdys duoda K1 (0,908) → K5 (0,720) → K4 (0,877):
   įvairovės taisyklė sąmoningai perstato mažesnio balo kandidatą į priekį. Įgyvendinta
   7 taisyklė. Garantija, kuri tikrai laikosi ir yra testuojama: **pirmas rezultatas visada
   yra didžiausio balo.**
3. **Tonacijos pasitikėjimo pagrindimas sako priešingai, nei daro formulė.** 2 taisyklė teigia,
   kad netiksliai nustatyta tonacija „beveik neturi įtakos balui". Tikrovėje svorinėje sumoje su
   fiksuotu vardikliu `pasitikėjimas → 0` reiškia `tonacijos balas → 0`, t. y. **maksimalią
   baudą** — iki 0,05 bendro balo, kai visas skirtumas tarp K1 ir K4 yra 0,031. Formulė
   įgyvendinta taip, kaip dokumente; vardiklio skaičiavimas tik iš kriterijų, turinčių duomenų,
   yra III užduoties darbas.

---

## 11. Kas lieka III užduočiai

HTTP API, konteinerizavimas, PostgreSQL su `pgvector`, tikras garso apdorojimas, prisijungimas
ir rolės, kokybės atributų įrodymai, našumo matavimai.

Papildomai, kas paaiškėjo per šią užduotį: panašumo modelio konstantos (svoriai ir MMR santykis)
niekada nebuvo išmatuotos, todėl III užduotyje jas reikia parinkti iš matavimo, o ne iš
intuicijos. Kokybės vertinimui būtina išmesti to paties atlikėjo dainas — kitaip matuojama,
ar sistema atpažįsta atlikėją, o ne ar randa panašią muziką.
