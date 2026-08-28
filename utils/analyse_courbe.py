import numpy as np


def analyser_pente(courbe):

    ct = courbe[courbe["Maturite_annees"] <= 2]["Taux"].mean()

    lt = courbe[courbe["Maturite_annees"] >= 10]["Taux"].mean()

    pente = lt - ct

    if pente > 1:
        regime = "Très pentue"

    elif pente > 0.30:
        regime = "Normale"

    elif pente > -0.20:
        regime = "Plate"

    else:
        regime = "Inversée"

    return {
        "Court Terme": round(ct, 2),
        "Long Terme": round(lt, 2),
        "Pente": round(pente, 2),
        "Regime": regime,
    }