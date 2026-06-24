# SSA given-name and US Census surname role data

`ssa_census_role_counts.json` is a derived, normalized count table. It contains
no individual-level records.

Sources:

- US Social Security Administration, **National data**, downloaded from
  <https://www.ssa.gov/oact/babynames/names.zip>. The official documentation is
  <https://www.ssa.gov/oact/babynames/limits.html> and the data qualifications
  are at <https://www.ssa.gov/oact/babynames/background.html>.
- US Census Bureau, **Frequently Occurring Surnames from the 2010 Census**,
  downloaded from
  <https://www2.census.gov/topics/genealogy/2010surnames/names.zip>. The landing
  page is <https://www.census.gov/topics/population/genealogy/data/2010_surnames.html>.

Input integrity:

- SSA `names.zip` SHA-256:
  `CD78E975ED7BB358E018DD62FBE14CED89295E9581C49172CA4EEDCB011B3724`
- Census `names.zip` SHA-256:
  `117C41CB4668727B7627B2845B6DF3F83EB2A22A1813F42C0FF4BDCAB86DE135`
- Extracted Census `Names_2010Census.csv` SHA-256 is recorded inside the
  generated JSON metadata.

Important qualifications:

- SSA counts are US Social Security card applications for births after 1879;
  the archive suppresses names with fewer than five occurrences in a year.
- Census counts cover surnames occurring at least 100 times in the 2010 Census.
- These US distributions are used only as a conservative fallback. They are not
  treated as globally representative of all cultures or languages.

Rebuild:

```powershell
python experiments/build_ssa_census_role_model.py `
  --ssa-zip path/to/names.zip `
  --census-zip path/to/census-names.zip `
  --census-csv path/to/Names_2010Census.csv `
  --output data/ssa_census_role_counts.json
```
