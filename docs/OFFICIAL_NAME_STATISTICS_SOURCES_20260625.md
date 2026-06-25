# Official multilingual name-statistics sources collected on 2026-06-25

This file records official or official-derived name statistics that are useful
for surname/given-name role evidence in Project 1. The sources below were
checked for structured role evidence, reproducible download paths, and usable
licensing.

## Used in the current optimization

| Country / source | Useful fields | How it is used | Citation URL |
|---|---|---|---|
| U.S. Census Bureau, 2020 Census first and last names | first-name counts; last-name counts | Adds broad U.S. given/surname evidence independent from SSA/Census 2010 | <https://www.census.gov/topics/population/genealogy/data/2020_names.html> |
| INSEE, France, Fichier des prénoms 2024 | given-name counts by year and sex | Adds French and immigrant given-name evidence | <https://www.insee.fr/fr/statistiques/8595130?sommaire=8595113> |
| INSEE, France, Fichier des noms 1891-2000 | surname counts by decade | Adds French surname evidence | <https://www.insee.fr/fr/statistiques/3536630> |
| Poland Ministry of Digital Affairs / PESEL first names | male/female first-name counts, latest 2026-01-20 records | Adds Polish given-name evidence | <https://dane.gov.pl/en/dataset/1667,lista-imion-wystepujacych-w-rejestrze-pesel-osoby-zyjace> |
| Poland Ministry of Digital Affairs / PESEL surnames | male/female current-surname counts, latest 2026-01-20 records | Adds Polish surname evidence | <https://dane.gov.pl/en/dataset/1681,nazwiska-osob-zyjacych-wystepujace-w-rejestrze-pesel> |
| Statistics Sweden / SCB via Researchdata.se | first names and last names in Sweden by country of birth, 2020 | Adds Nordic and migrant-name evidence; improved every validation set | <https://researchdata.se/en/catalogue/dataset/2021-272-1> |

The committed derived model is documented in
[`../data/OFFICIAL_NAME_STATS_ATTRIBUTION.md`](../data/OFFICIAL_NAME_STATS_ATTRIBUTION.md).

## Downloaded raw files and hashes

| Local cache file | SHA-256 |
|---|---|
| `us_census_2020_first_names_sex.xlsx` | `b763374b9b0ea4a9496f8563721312e8572e5a45136d34244db9ffba666c3326` |
| `us_census_2020_last_names_race_hispanic.xlsx` | `2e773c7edd934bb340b09be46e5d991b74a65cd63f547c94f80b6e233db462b3` |
| `fr_insee_prenoms_2024_nat_csv.zip` | `5a61af8b7a1cbc38147c44765543f825f3fbfedec861d485d3c4d9dfa56a3ea4` |
| `fr_insee_noms2008nat_txt.zip` | `c8693ff69bed32621250f1fc06e71b686e72bba1dbd771055e431d305527cfba` |
| `pl_pesel_given_female_2026_first.csv` | `95dcfa121ef81d2102705e865744cfa433dcecd4a582157881f94cbde339f73a` |
| `pl_pesel_given_male_2026_first.csv` | `6a6e30832a880d5006ac5b884828235599cd5180aa2b4bb92e69adf004ca7853` |
| `pl_pesel_surnames_female_2026.csv` | `e4f1b46641a38f8244d7872f343542f29e83eea394900535b802d4889262ba60` |
| `pl_pesel_surnames_male_2026.csv` | `ce4238feda85e75c73b16a229eb8afc1dfccb8854a7809111ab85fb8672b62f4` |
| `se_scb_names_by_birth_country_2020.zip` | `908602a4ea1e0ccc577c74bb8b71fe2b0d428ef4cb3c2d84c44319d8f8360351` |

Raw files are cached outside the repository under the local
`external_data/official_name_stats_20260625` directory. They are intentionally
not committed.

## Candidate sources for later work

These are useful future targets but were not ingested in this iteration because
the current optimization already improved all validation sets and these sources
need separate API-specific loaders and licensing checks:

- Nordic statistics portals with name tables, especially Norway Statistics
  Norway (SSB) and Statistics Denmark StatBank.
- Spain INE frequent names/surnames statistics.
- Additional Central/Eastern European government name registries, especially
  if they expose both given names and surnames in CSV/API form.
- Official sources that connect non-Latin native scripts to Latin
  transliterations; these are more valuable than native-script-only lists for
  the current Crossref Latin-name ordering problem.
