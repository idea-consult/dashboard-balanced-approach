import pandas as pd


def calculate_leefbaarheidspunten_for_contour(
    contour_df: pd.DataFrame,
    punten_niet_geisoleerd: float,
    punten_geisoleerd: float,
) -> tuple[float, float, float]:
    """Bereken leefbaarheidspunten voor alle contourcellen in één zone."""
    if contour_df.empty:
        return 0.0, 0.0, 0.0

    inwoners_per_huis = contour_df["gemiddeld_aantal_inwoners_per_huis"]
    inwoners_zonder = float(
        (contour_df["bewoonde_niet_geïsoleerde_woning"] * inwoners_per_huis).sum()
    )
    inwoners_met = float(
        (contour_df["bewoonde_geïsoleerde_woning"] * inwoners_per_huis).sum()
    )
    leefbaarheidspunten_zonder = inwoners_zonder * punten_niet_geisoleerd
    leefbaarheidspunten_met = inwoners_met * punten_geisoleerd
    return leefbaarheidspunten_zonder, leefbaarheidspunten_met, leefbaarheidspunten_zonder + leefbaarheidspunten_met


def _zone_factor(zone: str, base: float) -> float:
    """Halve factor per zone-stap (A -> B -> C ...)."""
    zone_idx = max(ord(str(zone).upper()) - ord("A"), 0)
    return base / (2 ** zone_idx)


def get_aantal_ernstig_gehinderden(
    gehinderde_personen_zonder_isolatie: float, gehinderde_personen_met_isolatie: float, z
):
    return (
        get_aantal_ernstig_gehinderden_zonder_isolatie(
            gehinderde_personen_zonder_isolatie, z
        )
        + get_aantal_ernstig_gehinderden_met_isolatie(gehinderde_personen_met_isolatie, z)
    )


def get_aantal_ernstig_gehinderden_zonder_isolatie(
    gehinderde_personen_zonder_isolatie, z
):
    return gehinderde_personen_zonder_isolatie * _zone_factor(z, 32)


def get_aantal_ernstig_gehinderden_met_isolatie(gehinderde_personen_met_isolatie, z):
    return gehinderde_personen_met_isolatie * _zone_factor(z, 24)
