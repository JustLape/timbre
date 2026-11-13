"""Visos sistemos konstantos vienoje vietoje.

Specifikacijos 1 skyrius. Sis modulis nieko neimportuoja, todel juo gali
naudotis visi sluoksniai nesukeliant ciklinio importo.

Demesio dviem skirtingoms formu rusims: tempo balas yra KVADRATINIS
exp(-(d/TEMPO_SIGMA)^2), o garsumo - NE kvadratinis exp(-|d|/LOUDNESS_SCALE).
Prie d = 6 abu duoda 0,368, bet prie d = 2 tempas duoda 0,895, o garsumas 0,717.
Abi formos yra is patvirtinto I etapo dokumento 3 skyriaus.
"""

POOL_SIZE = 200                  # kandidatu, imamu is katalogo
DEFAULT_LIMIT = 10               # grazinamu rezultatu
DEFAULT_ARTIST_LIMIT = 1         # dainu is to paties atlikejo
VECTOR_DIM = 256                 # vektoriaus ilgis
DUPLICATE_COSINE = 0.98          # virs sios reiksmes - dublikatas
MMR_RELEVANCE = 0.7              # ivairoves formules balo dalis
MMR_PENALTY = 0.3                # ivairoves formules baudos dalis
TEMPO_SIGMA = 6.0                # exp(-(d/sigma)^2)
LOUDNESS_SCALE = 6.0             # exp(-|d|/s)
KEY_MAX_STEPS = 4.0              # max(0, 1 - zingsniai/KEY_MAX_STEPS)
INSTRUMENTAL_THRESHOLD = 0.5     # nuo kada daina laikoma instrumentine
MIN_EXPLANATIONS = 2             # paaiskinimu vienam rezultatui
MOOD_INSTRUMENTAL = "instrumentinė"   # nuotaikos rakto pavadinimas
MOOD_DARK = "tamsi"

DEFAULT_WEIGHTS = {"vector": 0.70, "tempo": 0.10, "key": 0.05,
                   "loudness": 0.05, "mood": 0.10}
