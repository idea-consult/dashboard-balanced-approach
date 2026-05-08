def _zone_factor(zone: str, base: float) -> float:
    """Halve factor per zone-stap (A -> B -> C ...)."""
    zone_idx = max(ord(str(zone).upper()) - ord("A"), 0)
    return base / (2 ** zone_idx)


def get_hinder_punten(
    gehinderde_personen_zonder_isolatie: float, gehinderde_personen_met_isolatie: float, z
):
    return (
        gehinderde_personen_zonder_isolatie * _zone_factor(z, 32)
        + gehinderde_personen_met_isolatie * _zone_factor(z, 24)
    )
        

def get_hinder_punten_zonder_isolatie(gehinderde_personen_zonder_isolatie, z):
    return gehinderde_personen_zonder_isolatie * _zone_factor(z, 32)


def get_hinder_punten_met_isolatie(
    gehinderde_personen_met_isolatie, z
):
    return gehinderde_personen_met_isolatie * _zone_factor(z, 24)
