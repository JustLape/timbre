"""Visos sistemos konstantos vienoje vietoje.

Specifikacijos 1 skyrius. Šis modulis nieko neimportuoja, todėl juo gali
naudotis visi sluoksniai nesukeliant ciklinio importo.

Dėmesio dviem skirtingoms formų rūšims: tempo balas yra KVADRATINIS
exp(-(d/TEMPO_SIGMA)^2), o garsumo — NE kvadratinis exp(-|d|/LOUDNESS_SCALE).
Prie d = 6 abu duoda 0,368, bet prie d = 2 tempas duoda 0,895, o garsumas
0,717. Abi formos yra iš patvirtinto I etapo dokumento 3 skyriaus.
"""

POOL_SIZE = 200                  # kandidatų, imamų iš katalogo
DEFAULT_LIMIT = 10               # grąžinamų rezultatų
DEFAULT_ARTIST_LIMIT = 1         # dainų iš to paties atlikėjo
VECTOR_DIM = 256                 # vektoriaus ilgis
DUPLICATE_COSINE = 0.98          # virš šios reikšmės – dublikatas
MMR_RELEVANCE = 0.7              # įvairovės formulės balo dalis
MMR_PENALTY = 0.3                # įvairovės formulės baudos dalis
TEMPO_SIGMA = 6.0                # exp(-(d/sigma)^2)
LOUDNESS_SCALE = 6.0             # exp(-|d|/s)
KEY_MAX_STEPS = 4.0              # max(0, 1 - žingsniai/KEY_MAX_STEPS)
INSTRUMENTAL_THRESHOLD = 0.5     # nuo kada daina laikoma instrumentine
MIN_EXPLANATIONS = 2             # paaiškinimų vienam rezultatui
MOOD_INSTRUMENTAL = "instrumentinė"   # nuotaikos rakto pavadinimas
MOOD_DARK = "tamsi"

# Bendro katalogo žyma. Patvirtinto I etapo dokumento 4 skyrius pažodžiui:
# „Žyma `bendras` pažymi viešąjį katalogą, kurį mato visi."
#
# Tai ne eilinė konstanta, o viso matomumo ašis:
#   - `bendras` dainas mato VISI, ir tik jos gali atsidurti ATSAKYME;
#   - kliento įkeltas dainas mato TIK jis, ir jos gali būti tik UŽKLAUSA.
#
# Neprisijungęs žmogus paduoda patį `bendras` kaip savo tenant_id, todėl
# atskiro „be kliento" atvejo kode nereikia, o tenant_id lieka privalomas
# be numatytosios reikšmės.
SHARED_CATALOG = "bendras"

DEFAULT_WEIGHTS = {"vector": 0.70, "tempo": 0.10, "key": 0.05,
                   "loudness": 0.05, "mood": 0.10}
