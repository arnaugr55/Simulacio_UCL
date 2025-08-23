from funcions import *
import random
import string
import numpy as np
import pandas as pd
import os


'''
try:
    iters = int(input("Quantes iteracions vols fer de la Champions?\n--> Si esculls 1 podràs "
                      "veure com va la Champions ronda a ronda. \n--> Si esculls un número major, no, "
                      "però se't generarà un csv amb els resultats de cada equip en les x iteracions. "
                      "\n----> També cal tenir en compte que per cada iteració tarda mig segon, per lo que, "
                      "per exemple, si fessis 100 iteracions, el codi tardaria uns 8 minuts.\n"))
except Exception as e:
    raise ValueError(f"Has d'introduir un número enter.")

if iters == 1:
    try:
        conv_respostes = {'S': True, 'N': False}

        pas_a_pas_ = input("S --> Mostra de forma visual de la Fase Lliga a la Final\n"
                           "N --> Mostra de forma visual de la Taula Final de la Fase Lliga a la Final\n")
        pas_a_pas = conv_respostes[pas_a_pas_]
        tot_proces_ = input("La definció d'una fase lliga compatible tarda bastant.\n"
                            "S --> Genera de zero una frase lliga\n"
                           "N --> N'agafa aleatòriament una de les ja generades\n")
        tot_proces = conv_respostes[tot_proces_]
    except Exception as e:
        raise ValueError(f"Has d'introduir el valor S o N. En majúscules")
'''

iters = 1
pas_a_pas = True
tot_proces = False

# Inicialitzem resultats. On posem els resultats de cada equip en cada iteració
resultats = pd.read_csv('equips/UCLTeams_202526.csv')
resultats = resultats.drop(columns=["Points", "POT"])
resultats["Winner"] = 0
resultats["Final"] = 0
resultats["Semis"] = 0
resultats["Quarts"] = 0
resultats["Vuitens"] = 0
resultats["Playoffs"] = 0
resultats["FaseLliga"] = 0

# Funció principal que va cridant a les funcions de funcions.py
def champions(tot_proces, equips):
    if tot_proces:
        random_code = ''.join(random.choices(string.ascii_letters + string.digits, k=10))  # Generem un codi random de 10 caracters

        # Definim els 144 partits de la fase lliga en una matriu
        partits = sorteig_fase_lliga(equips)
        print(partits)
        partits_matriu_nom = "equips/fase_lliga/202526/enfrontaments_matriu_" + random_code + ".csv"
        np.savetxt(partits_matriu_nom, partits, delimiter=",", fmt="%d")  # Saves as CSV
        #partits = np.loadtxt("equips/fase_lliga/202526/enfrontaments_matriu_XMEODcsxA5.csv", delimiter=",")

        # Decidim els partits de local o visitant
        # En aquest cas cridem la funció en un while, ja que hi ha cops que es queda "encallada" i l'hem de tonar a cridar
        partitsLV = "None"
        while isinstance(partitsLV, str):
            partitsLV = definim_local_visitant(equips, partits)
        partitsLV_nom = "equips/fase_lliga/202526/enfrontamentsLV_" + random_code + ".csv"
        partitsLV.to_csv(partitsLV_nom, index=False)

        # Assignem jornades als diferents partits
        jornades = "None"
        while isinstance(jornades, str):
            jornades = assignar_jornades(partitsLV, equips)
        jornades_nom = "equips/fase_lliga/202526/jornades_" + random_code + ".csv"
        jornades.to_csv(jornades_nom, index=False)

    else:
        # Aleatòriament, seleccionem una fase lliga de les ja generades
        carpeta = r"C:\Users\usuari\Documents\SimulacióFut\equips\fase_lliga\202526"
        fitxers = [f for f in os.listdir(carpeta) if
                   f.startswith("jornades_") and os.path.isfile(os.path.join(carpeta, f))]
        # Selecciona un fitxer aleatori
        fitxer_aleatori = random.choice(fitxers)
        ruta_completa = os.path.join(carpeta, fitxer_aleatori)
        jornades = pd.read_csv(ruta_completa)
        print(jornades)

        # Si hem deciidit "pas_a_pas", mostrarem primer els endrentaments de cada equip a la fase lliga
        if pas_a_pas == True:
            fase_lliga_imatge(jornades[['Equip 1', 'Equip 2']], equips)

    # Diccionari on guardem, quins equips s'han quedat a FaseLliga, quins als playoffs, quins a Vuitens...
    arribat = {'FaseLliga': [], 'Playoffs': [], 'Vuitens': [], 'Quarts': [], 'Semis': [], 'Final': [], 'Winner': []}

    # Partits fase lliga. Ens retorna la taula final
    leaguephase_table = fase_lliga(jornades, equips, arribat, pas_a_pas, iters)

    # Després de la fase lliga, els equips amb:
        # >= 18 punts, se'ls hi pujarà 1 punt "de poder" perquè tinguin més probabolitats als partits de les ronde eliminatòries
        # >= 20 punts, se'ls hi pujarà 2 punts "de poder" perquè tinguin més probabolitats als partits de les ronde eliminatòries
        # >= 22 punts, se'ls hi pujarà 3 punts "de poder" perquè tinguin més probabolitats als partits de les ronde eliminatòries
    equips2 = equips.copy()
    # Afegim la columna Punts a partir del df1
    equips2 = equips2.merge(leaguephase_table[['Club', 'Punts']], on='Club', how='left')
    equips2['Points'] += (equips2['Punts'] >= 18).astype(int) + \
                         (equips2['Punts'] >= 20).astype(int) + \
                         (equips2['Punts'] >= 22).astype(int)
    # Eliminar la columna Punts per tornar al format original
    equips2 = equips2.drop(columns=['Punts'])

    # Rondes eliminatòries i final. S'actualitza el diccionari "arribat"
    bracket_phase(leaguephase_table, arribat, equips2, iters)

    # Afegim els resultats d'aquesta UCL a resultats (resultats generals)
    for fase, equips in arribat.items():
        for equip in equips:
            resultats.loc[resultats["Club"] == equip, fase] += 1


if __name__ == '__main__':
    # VARIABLES A PARAMETRITZAR PER L'USUARI
    # Carreguem els equips que hi participen
    equips = pd.read_csv('equips/UCLTeams_202526.csv')
    for i in range(iters):
        champions(tot_proces, equips)

    # Si hi ha més d'una UCL, crearem un csv amb el resultats de totes
    if iters > 1:
        name = "outputs/Equips_resultats_"+str(iters)+"x.csv"
        resultats.to_csv(name, index=False)
