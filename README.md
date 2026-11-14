# Pelitarjous

Suomenkielinen pelitarjoussivu, joka päivittyy itsestään. GitHub Actions hakee hinnat neljä kertaa päivässä, tallentaa hintahistorian ja julkaisee sivun GitHub Pagesiin.

## Rakenne

| Polku | Tehtävä |
|---|---|
| `scripts/fetch.py` | Hakee Steamin tarjoukset (Suomen hinnat), muiden kauppojen hinnat IsThereAnyDealista ja Epicin ilmaispelit |
| `scripts/build.py` | Rakentaa sivuston `dist/`-kansioon: etusivu, oma sivu jokaiselle pelille, sitemap |
| `site/template.html` | Etusivun rakenne ja logiikka |
| `site/game.html` | Pelisivun pohja |
| `site/style.css` | Yhteiset tyylit |
| `data/deals.json` | Tämänhetkiset tarjoukset |
| `data/history.csv` | Hintahistoria, uusi rivi aina kun hinta muuttuu |
| `.github/workflows/update.yml` | Ajastus, datan tallennus ja julkaisu |

## Käyttöönotto

1. Luo GitHubissa uusi **julkinen** repo (esim. `pelitarjous`) ja lataa tämän kansion sisältö sinne.
2. Tarkista, että tiedosto `.github/workflows/update.yml` on repossa. Jos piilokansio ei tullut mukaan, luo se: **Add file -> Create new file**, nimeksi `.github/workflows/update.yml`, ja liitä tiedoston sisältö.
3. **Settings -> Pages -> Source:** valitse **GitHub Actions**.
4. **Settings -> Actions -> General -> Workflow permissions:** valitse **Read and write permissions**.
5. **Settings -> Secrets and variables -> Actions -> New repository secret:**
   - `ITAD_API_KEY` = IsThereAnyDeal-avaimesi (muiden kauppojen hinnat)
   - `DISCORD_WEBHOOK` = Discord-webhookin osoite (valinnainen, virheilmoituksia varten)
6. **Actions -> Paivita hinnat ja julkaise -> Run workflow.**

Sivu löytyy sen jälkeen osoitteesta `https://<käyttäjänimi>.github.io/<repon-nimi>/`.

## Ajo omalla koneella

```
python scripts/fetch.py
python scripts/build.py
```

Avaa sitten `dist/index.html` selaimessa. Lisäpaketteja ei tarvita.

## Huomioita

- Älä koskaan tallenna API-avaimia tiedostoihin. Ne kuuluvat vain GitHubin Secrets-kohtaan.
- Tilausten hinnat (Game Pass, PS Plus, Switch Online) ovat käsin ylläpidettyjä `site/template.html`-tiedostossa. Tarkista ne säännöllisesti.
