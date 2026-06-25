# Official national name statistics role model

`official_name_stats_role_counts.json` is a derived token-role table used by
the Crossref name-order fallback. It contains only normalized Latin tokens and
source-normalized surname/given pseudo-counts. The raw downloaded files are not
stored in the repository.

## Sources

| Source | Role evidence | URL | License / terms | SHA-256 |
|---|---|---|---|---|
| U.S. Census Bureau, 2020 Census first names by sex | given names | <https://www2.census.gov/topics/genealogy/2020surnames/Names2020_FirstNames_Sex.xlsx> | U.S. government public data | `b763374b9b0ea4a9496f8563721312e8572e5a45136d34244db9ffba666c3326` |
| U.S. Census Bureau, 2020 Census last names by race/Hispanic origin | surnames | <https://www2.census.gov/topics/genealogy/2020surnames/Names2020_LastNames_RaceHispanic.xlsx> | U.S. government public data | `2e773c7edd934bb340b09be46e5d991b74a65cd63f547c94f80b6e233db462b3` |
| INSEE, France, `prenoms-2024-nat_csv.zip` | given names | <https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2024-nat_csv.zip> | INSEE open data terms | `5a61af8b7a1cbc38147c44765543f825f3fbfedec861d485d3c4d9dfa56a3ea4` |
| INSEE, France, `noms2008nat_txt.zip` | surnames | <https://www.insee.fr/fr/statistiques/fichier/3536630/noms2008nat_txt.zip> | INSEE open data terms | `c8693ff69bed32621250f1fc06e71b686e72bba1dbd771055e431d305527cfba` |
| Poland PESEL, female first names, 2026-01-20 | given names | <https://api.dane.gov.pl/resources/1159670,lista-imion-zenskich-w-rejestrze-pesel-stan-na-20012026-imie-pierwsze/csv> | CC0 1.0 | `95dcfa121ef81d2102705e865744cfa433dcecd4a582157881f94cbde339f73a` |
| Poland PESEL, male first names, 2026-01-20 | given names | <https://api.dane.gov.pl/resources/1159669,lista-imion-meskich-w-rejestrze-pesel-stan-na-20012026-imie-pierwsze/csv> | CC0 1.0 | `6a6e30832a880d5006ac5b884828235599cd5180aa2b4bb92e69adf004ca7853` |
| Poland PESEL, female surnames, 2026-01-20 | surnames | <https://api.dane.gov.pl/resources/1148811,nazwiska-zenskie-stan-na-2026-01-20/csv> | CC0 1.0 | `e4f1b46641a38f8244d7872f343542f29e83eea394900535b802d4889262ba60` |
| Poland PESEL, male surnames, 2026-01-20 | surnames | <https://api.dane.gov.pl/resources/1148808,nazwiska-meskie-stan-na-2026-01-20/csv> | CC0 1.0 | `ce4238feda85e75c73b16a229eb8afc1dfccb8854a7809111ab85fb8672b62f4` |
| Statistics Sweden / SCB, names by country of birth, 2020 | given names and surnames | <https://researchdata.se/en/catalogue/dataset/2021-272-1> | CC BY 4.0 | `908602a4ea1e0ccc577c74bb8b71fe2b0d428ef4cb3c2d84c44319d8f8360351` |

## Rebuild

```powershell
$base = "path\to\official_name_stats_20260625"

python experiments/build_official_name_stats_role_model.py `
  --us-census-first "$base\us_census_2020_first_names_sex.xlsx" `
  --us-census-last "$base\us_census_2020_last_names_race_hispanic.xlsx" `
  --fr-insee-prenoms "$base\fr_insee_prenoms_2024_nat_csv.zip" `
  --fr-insee-noms "$base\fr_insee_noms2008nat_txt.zip" `
  --pl-given-female "$base\pl_pesel_given_female_2026_first.csv" `
  --pl-given-male "$base\pl_pesel_given_male_2026_first.csv" `
  --pl-surnames-female "$base\pl_pesel_surnames_female_2026.csv" `
  --pl-surnames-male "$base\pl_pesel_surnames_male_2026.csv" `
  --se-scb-zip "$base\se_scb_names_by_birth_country_2020.zip" `
  --output data/official_name_stats_role_counts.json
```

Expected derived model SHA-256:

`f203d44234eea568802b6868aeb500640169d529950c77155fcb0887f18579ca`
