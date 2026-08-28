import pandas as pd


def construire_resume_courbe(courbe_bam):
    """
    Résumé de la courbe des taux par date et segment.
    """

    resume = (
        courbe_bam
        .groupby(["Date_reference", "Segment"])["Taux"]
        .mean()
        .reset_index()
    )

    resume = resume.pivot(
        index="Date_reference",
        columns="Segment",
        values="Taux"
    )

    resume = resume.rename(columns={
        "Court Terme": "CT",
        "Moyen Terme": "MT",
        "Long Terme": "LT"
    })

    resume = resume.reset_index()

    # ==========================================
# Indicateurs de la courbe
# ==========================================

    resume["Spread_LT_CT"] = (
        resume["LT"] - resume["CT"]
    )

    resume["Spread_MT_CT"] = (
        resume["MT"] - resume["CT"]
    )

    resume["Spread_LT_MT"] = (
        resume["LT"] - resume["MT"]
    )

    resume["Volatilite_Courbe"] = (
        resume[
            ["CT", "MT", "LT"]
        ].std(axis=1)
    )
    
    return resume
def indicateurs_courbe(resume):

    return {
        "Spread moyen LT-CT":
            resume["Spread_LT_CT"].mean(),

        "Spread maximum LT-CT":
            resume["Spread_LT_CT"].max(),

        "Spread minimum LT-CT":
            resume["Spread_LT_CT"].min(),

        "Volatilité moyenne de la courbe":
            resume["Volatilite_Courbe"].mean(),
    }