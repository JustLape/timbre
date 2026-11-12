# Timbre – panašiai skambančių dainų paieška

Kursinis darbas. Programų sistemų projektavimas, Vilnius Tech, 2026 m. rudens semestras.

Sistema pagal vieną pateiktą dainą (nuorodą arba įkeltą failą) suranda panašiai **skambančias** dainas – pagal pačios dainos garsą, o ne pagal atlikėjo žanrą ar klausymo statistiką. Rezultatus galima susiaurinti pagal tempą, tonaciją ir instrumentalumą, o kiekvienas pasiūlymas paaiškinamas, kodėl jis pateko į sąrašą.

## Dokumentai

| Etapas | Dokumentas | Būsena |
|---|---|---|
| I. Projektavimo dokumentas | [docs/1-etapas-projektavimo-dokumentas.md](docs/1-etapas-projektavimo-dokumentas.md) | Pateikta |
| II. Veikiantis prototipas | – | Rengiama |
| III. Galutinis sprendimas ir architektūros dokumentas | – | Rengiama |

## Pagrindinis modulis

Panašumo rikiavimo modulis: iš vektorinės paieškos gautus kandidatus įvertina pagal penkis kriterijus (garso panašumą, tempą, tonaciją, garsumą ir nuotaiką), pašalina pasikartojimus, apriboja to paties atlikėjo dainas, užtikrina rezultatų įvairovę ir paaiškina kiekvieną pasiūlymą.

## Planuojamos technologijos

Python, FastAPI, Essentia, PostgreSQL su `pgvector`, Redis, Docker Compose.

## Paleidimas

Bus papildyta II etape – sistema turės pasileisti viena komanda.


## Architektūriniai sprendimai (II etapas)
1. **`dalinis_rezultatas` semantika:** `true`, kai grąžinamų rezultatų mažiau nei prašyta (`limit`). Laukas `labiausiai_ribojes_filtras` užpildomas tik tada, kai kandidatus atmetė pats filtras (ne dublikatų šalinimas ar atlikėjo limitas).
2. **Filtro statistika:** repozitorija grąžina `survivors_per_filter` (kiek dainų atskirai praeina kiekvieną filtrą), o `domain` sluoksnis išrenka labiausiai apribojusį filtrą.
3. **Vardiniai svoriai:** svoriai perduodami per vardinį registrą (`--weights vector=0.7,tempo=0.1`), kad kriterijų skaičius nebūtų įkaltas kode.