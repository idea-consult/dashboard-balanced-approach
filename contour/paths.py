from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INTERMEDIATE_DIR = ROOT / "output" / "intermediate"
INPUT_DIR = ROOT / "input"

CONTOUR_VLAANDEREN = DATA_DIR / "contour_vlaanderen_stocks.xlsx"
INWONERS_BRUSSEL = DATA_DIR / "inwoners_brussel_sector_contour_2024.xlsx"
POPULATION_SECTOR = DATA_DIR / "population 2024 par bout de secteur stat.xlsx"
POPULATION_SECTOR_SHEETS = {
    "lden": "intersection ss Lden - surface",
    "lnight": "intersection ss Lnight - surfac",
}
VERGUNNINGEN_OMGEVINGSLOKET = DATA_DIR / "vergunningen_omgevingsloket_2026_lang.csv"
VERGUNNINGEN_KWETSBAAR = DATA_DIR / "vergunningen_kwetsbare_functies_2026_lang.csv"
VERGUNNINGEN_VERKAVELING = DATA_DIR / "vergunningen_verkaveling_2026_lang.csv"
TRANSACTIES_DIR = DATA_DIR / "transacties_vastgoed"
CAPAKEY_CONTOUR_LDEN = DATA_DIR / "capakey_contour_lden.csv"

FLOW_RULES_FILE = INPUT_DIR / "flow_rules.csv"
LDEN_CONTOUR_FILE = INPUT_DIR / "lden_contour.csv"
LNIGHT_CONTOUR_FILE = INPUT_DIR / "lnight_contour.csv"
LDEN_CONTOUR_REGIONAL_FILE = INPUT_DIR / "lden_contour_regional.csv"
LNIGHT_CONTOUR_REGIONAL_FILE = INPUT_DIR / "lnight_contour_regional.csv"
