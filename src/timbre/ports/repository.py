"""Katalogo sąsaja. Specifikacijos 5 skyrius.

Čia yra priklausomybių krypties sukeitimo taškas: `domain` ir `app` žino tik
šią abstrakčią sąsają, o konkretūs adapteriai (`adapters/json_catalog.py`,
`adapters/in_memory.py`) ją įgyvendina. Todėl testams pakanka atminties
katalogo — nei failų, nei duomenų bazės.

Naudojamas `typing.Protocol`, o ne `abc.ABC`: adapteriui nereikia nieko
paveldėti, pakanka turėti tinkamus metodus.

`tenant_id` yra **privalomas pirmas argumentas kiekviename metode** ir neturi
numatytosios reikšmės. Tai sąmoninga apsauga: kliento atskyrimo negalima
pamiršti, nes be jo kvietimas tiesiog nesuveikia.

Matomumas nėra vienas dalykas, o trys atskiri klausimai, ir adapteris juos
atsako skirtingai:

    UŽKLAUSAI   bendras katalogas + paties kliento įkeltos dainos
    ATSAKYMUI   tik bendras katalogas
    KEITIMUI    tik paties kliento įkeltos dainos

Iš to seka pagrindinė sistemos savybė: kliento įkelta daina gali būti tik
klausimas, bet niekada ne atsakymas, todėl per rezultatus ji nenuteka niekam.
Neprisijungęs naudotojas paduoda `bendras` kaip savo `tenant_id` — jam
„savų dainų" rinkinys tiesiog tuščias, ir jokio atskiro atvejo nereikia.
"""

from typing import Protocol

from ..domain.models import CandidatePool, FilterSpec, Track


class CatalogRepository(Protocol):
    def get_track(self, tenant_id: str, song_id: str) -> Track | None:
        """Grąžina dainą arba None, jei klientui ji nematoma.

        Matoma yra bendro katalogo daina ir paties kliento įkelta daina.
        """

    def find_by_title_artist(self, tenant_id: str, title: str,
                             artist: str | None = None) -> list[Track]:
        """Randa dainas pagal pavadinimą ir, jei nurodytas, atlikėją.

        Grąžinamas sąrašas, nes pavadinimas NĖRA unikalus raktas: patikrinta,
        kad „Billie Jean" su Michael Jackson MusicBrainz duomenyse atitinka
        152 įrašus. Pasirinkimą tarp jų daro kviečiantysis, o ne adapteris.
        """

    def fetch_candidates(self, tenant_id: str, query: Track,
                         filters: FilterSpec, pool_size: int) -> CandidatePool:
        """Grąžina iki pool_size kandidatų, artimiausių query vektoriui.

        Filtrai taikomi PAIEŠKOS METU, ne po jos. Užklausos daina į kandidatus
        neįtraukiama. survivors_per_filter užpildomas kiekvienam filtrui atskirai –
        kiek dainų praeitų tą vieną filtrą, kitų netaikant.
        """

    def remove_track(self, tenant_id: str, song_id: str) -> bool:
        """Pašalina kliento dainą; grąžina False, jei jos tame kataloge nėra.

        Rašymo kelias yra būtinas II etapo 4 reikalavimui: reikia parodyti, kad
        kito kliento duomenų negalima ne tik perskaityti, bet ir PAKEISTI.

        Svetimo kliento daina čia nėra atskiras klaidos atvejis – ji tiesiog
        neegzistuoja, tad grąžinama False lygiai taip pat, kaip ir visai
        nesančiai dainai. Taip sąmoningai neatskleidžiama, kad tas song_id
        kataloge egzistuoja.

        Bendro katalogo daina irgi grąžina False, nors ji ir matoma: bendras
        katalogas yra tik skaitomas. Matyti ir keisti yra du skirtingi dalykai.
        """
