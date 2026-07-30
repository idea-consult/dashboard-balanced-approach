# Balanced Approach — dashboard luchthaven

Dit project is een **Streamlit-dashboard** voor de Balanced Approach rond Brussels Airport. Het simuleert beleidsmaatregelen in Lden-geluidszones **A–F** (mutueel exclusief) en optioneel in de overlappende contouren **Lnight45** en **NA70**. Per scenario zie je de impact op woning- en perceelstocks, ernstig gehinderden en kosten (overheid / privé).

---

## Opstarten

**Vereisten:** Python ≥ 3.14 en [uv](https://github.com/astral-sh/uv).

```powershell
uv sync
uv run streamlit run app.py
```

De app vraagt een wachtwoord (zie `.streamlit/secrets.toml`).

### Data-analyse (pipeline)

De Lden-intersecties en flow rates bouw je opnieuw op met:

```powershell
uv run streamlit run contour_analyse_1.py --server.port 8502
uv run streamlit run contour_analyse_2.py --server.port 8502
```

### Tests

```powershell
uv run pytest
```

---

## Documentatie

| Pagina | Inhoud |
|--------|--------|
| [Data-structuur](docs/data-structuur.md) | Van brondata tot `input/`/`output/`: waar wat berekend wordt |
| [Dashboard-berekeningen](docs/dashboard-berekeningen.md) | Simulatie per jaar, flows, KPI’s, overlay-rates |
| [Terminologie](docs/terminologie.md) | Glossarium (contour, zone, stock, flow, …) |
| [Architectuur](docs/architectuur.md) | Codekaart: modules en verantwoordelijkheden |
| [Maatregelen toevoegen](docs/maatregelen-toevoegen.md) | Checklist om een nieuwe maatregel te configureren |
| [Scenario’s](docs/scenarios.md) | Sidebar-presets via `input/scenarios.csv` |
| [Maatregelen en stocks](docs/maatregelen-en-stocks.md) | Volledige referentie van alle maatregelen en simulatiestocks |
| [Overlays Lnight45 / NA70](docs/overlays-lnight45-na70.md) | Overlappende zones: UI, shares en visualisaties |
