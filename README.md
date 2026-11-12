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
