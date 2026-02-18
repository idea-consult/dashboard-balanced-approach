def get_hinder_punten(
    gehinderde_personen_zonder_isolatie, gehinderde_personen_met_isolatie, z
):
    match z:
        case "A":
            return (
                gehinderde_personen_zonder_isolatie * 32
                + gehinderde_personen_met_isolatie * 24
            )
        case "B":
            return (
                gehinderde_personen_zonder_isolatie * 16
                + gehinderde_personen_met_isolatie * 12
            )
        case "C":
            return (
                gehinderde_personen_zonder_isolatie * 8
                + gehinderde_personen_met_isolatie * 6
            )
        case "D":
            return (
                gehinderde_personen_zonder_isolatie * 4
                + gehinderde_personen_met_isolatie * 3
            )
        case "E":
            return 0


def get_hinder_punten_zonder_isolatie(gehinderde_personen_zonder_isolatie, z):
    match z:
        case "A":
            return gehinderde_personen_zonder_isolatie * 32
        case "B":
            return gehinderde_personen_zonder_isolatie * 16
        case "C":
            return gehinderde_personen_zonder_isolatie * 8
        case "D":
            return gehinderde_personen_zonder_isolatie * 4
        case "E":
            return 0


def get_hinder_punten_met_isolatie(
    gehinderde_personen_met_isolatie, z
):
    match z:
        case "A":
            return gehinderde_personen_met_isolatie * 24
        case "B":
            return gehinderde_personen_met_isolatie * 12
        case "C":
            return gehinderde_personen_met_isolatie * 6
        case "D":
            return gehinderde_personen_met_isolatie * 3
        case "E":
            return 0
