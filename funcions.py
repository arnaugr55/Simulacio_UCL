import pandas as pd
import random
import numpy as np
import bisect
import math
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk
import time
import subprocess
import sys

from flask import Flask, render_template_string, request
import threading


def sorteig_fase_lliga(equips, countr_teams_faced, partits):
    '''
    Genera els partits de la Fase Lliga
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :param countr_teams_faced: Diccionari per controlar que un equip no s'enfronti a +2 d'una lliga
    :param partits: Matriu amb els enfrontaments
    :return: matriu partits amb els 144 partits (o no)
    '''
    # Itera cada POT
    for pot_num in range(4):
        # Seleccionem un ordre aleatori del pot
        min_num_pot = pot_num * 9
        max_num_pot = min_num_pot + 9
        pot_randomized = random.sample(range(min_num_pot, max_num_pot), 9)
        # Iterem els diferents equips del pot
        for ind in pot_randomized:
            equip = equips.iloc[ind]
            equip_league = equip['League']

            # Iterem fins que aquell equip ja tingui 8 rivals
            while sum(partits[ind]) != 8:
                # Generem una llista aleatòria dels 36 possibles equips rivals
                random_36teams = random.sample(range(0, 9), 9) + random.sample(range(9, 18), 9) + random.sample(
                    range(18, 27), 9) + random.sample(range(27, 36), 9)
                cont = 0  # Contador de quants possibles rivals portem iterats
                # Iterem els diferents possibles rivals de la llista random_36teams
                while sum(partits[ind]) != 8:
                    random_team_num = random_36teams[cont]
                    league_valid = True
                    equip2 = equips.iloc[random_team_num]  # equip2 és el possible rival
                    equip2_league = equip2['League']

                    # Revisem el número de rivals ja seleccionats que té en aquell pot, tant el equip com el equip2
                    min_index = (equip2['POT']-1)*9
                    max_index = equip['POT']*9
                    num_equips2_pot = sum(partits[ind, min_index:max_index])
                    num_equips_pot = sum(partits[min_index:max_index, random_team_num])

                    # Si algún dels indicadors >= 2, aquell enfrontament no s'afegirà (ja que ja tindrà 2 rivals d'aquell pot)
                    if num_equips2_pot < 2 and num_equips_pot < 2:
                        try:
                            # Si de la lliga de l'equip2 ja té 2 equips, aquell enfrontament no s'afegirà
                            if countr_teams_faced[ind][equip2_league] == 2:
                                league_valid = False
                        except:
                            pass
                        try:
                            # Si de la lliga de l'equip ja té 2 equips, aquell enfrontament no s'afegirà
                            if countr_teams_faced[random_team_num][equip_league] == 2:
                                league_valid = False
                        except:
                            pass
                        # En cas de que hagi passat les "resticcions" anteriors, afegiex l'enfrontament a partits i actualitza countr_teams_faced
                        if league_valid:
                            if partits[ind, random_team_num] == 0:
                                try:
                                    countr_teams_faced[ind][equip2_league] += 1
                                except:
                                    countr_teams_faced[ind][equip2_league] = 1
                                try:
                                    countr_teams_faced[random_team_num][equip_league] += 1
                                except:
                                    countr_teams_faced[random_team_num][equip_league] = 1

                            partits[ind, random_team_num] = 1
                            partits[random_team_num, ind] = 1

                        else:
                            # Descartat mateixa lliga
                            pass
                    else:
                        # Descartat pot complet
                        pass

                    # Ja fem iterat tots els possibles rivals i no hem aconseguit que agafi els 8
                        # De ser així es retorna ja "partits"
                    cont += 1
                    if cont == 36 and sum(partits[ind]) != 8:
                        return partits
    # Es retorna partits ja complet
    return partits


def validem_sorteig_fase_lliga(equips):
    '''
    Crida a sorteig_fase_lliga() fins que li retorni una Fase Lliga (partits) completa
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :return: matriu partits amb els 144 partits
    '''
    countr_teams_faced = {}   # Diccionari per controlar que un equip no s'enfronti a +2 d'una lliga
    num_partits = 0  # Número de partits a la matriu "partits"
    for i in range(36):
        countr_teams_faced[i] = {}
        countr_teams_faced[i][equips.iloc[i]['League']] = 2

    while num_partits != 288:  # A la matriu un partit es definiex 2 vegades (ex: PSV,PSG i PSG,PSV) per això aquest 288 (144*2)
        # Dins d'aquest while, cridem a sorteig_fase_lliga() fins que trobi una Fase Lliga vàlida, amb els 144 partits
        countr_teams_faced = {}
        partits = np.zeros(shape=(36, 36))
        for i in range(36):
            countr_teams_faced[i] = {}
            countr_teams_faced[i][equips.iloc[i]['League']] = 2
        partits = sorteig_fase_lliga(equips, countr_teams_faced, partits)
        num_partits = np.count_nonzero(partits == 1)
        if num_partits != 288:
            # Es repeteix la cerca d'una Fase Lliga compatible
            pass
    return partits


def trobar_i_intercanviar(df_matches, team_a, home_count, away_count, mode):
    '''
    Funció secundària de definim_local_visitant()
    Troba un partit que es pugui reassignar i ajusta els comptadors
    :param df_matches: Dataset amb els 144 enfrontaments. La seva estructura és Equip 1, Equip 2, PENDENT (si serà local o visitant)
    :param team_a: Equip que se li treurà un partit
    :param home_count: Núm_partits a casa de l'Equip 1
    :param away_count: Núm_partits fora de casa de l'Equip 2
    :param mode: HOME o AWAY
    :return: Variables d'entrada (df_matches, home_count, away_count) actualitzades
    '''
    # Elimina un partit del team_a, perque te el comptador (home_count o away_count al maxim (4)) i el seu espai l'ocupi un altre
    for i in range(len(df_matches)):
        random_eliminar = random.randint(0, 143)
        match_susp = df_matches.iloc[random_eliminar]
        if match_susp['PENDENT'] != 'PENDENT':
            equip1, equip2 = match_susp['Equip 1'], match_susp['Equip 2']
            if ((equip1 == team_a and match_susp['PENDENT'] == mode) or
                (equip2 == team_a and match_susp['PENDENT'] == ('AWAY' if mode == 'HOME' else 'HOME'))):
                # Alliberar l'assignació a df_matches
                df_matches.loc[random_eliminar, 'PENDENT'] = 'PENDENT'
                # Si el partit era HOME del team_a, en baixem el home_count i l'away_count de l'altre equip
                if home_count[team_a] == 4:
                    home_count[team_a] -= 1
                    away_count[equip2 if equip1 == team_a else equip1] -= 1
                # Si el partit era AWAY del team_a, en baixem l'away_count i el home_count de l'altre equip
                else:
                    home_count[equip2 if equip1 == team_a else equip1] -= 1
                    away_count[team_a] -= 1
                return df_matches, home_count, away_count, True
    return df_matches, home_count, away_count, False


def definim_local_visitant(equips, partits):
    '''

    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :param partits: Matriu de la Fase Lliga
    :return: Dataset amb els 144 enfrontaments. La seva estructura és Equip 1, Equip 2, PENDENT (si serà local o visitant)
    '''
    # Passem de la matriu de 144/288 partits a un dataset amb 144 registres (els partits)
    teams = equips['Club'].tolist()
    matches = [] # Crear una llista de partits (parelles d'equips)
    num_teams = 36
    for i in range(num_teams):
        for j in range(i, num_teams):  # Evitem duplicats (només agafem la part superior de la matriu)
            if partits[i, j] == 1:
                if (i + j) % 2 == 1:
                    matches.append((teams[i], teams[j], "PENDENT"))
                elif (i + j) % 2 == 0:
                    matches.append((teams[j], teams[i], "PENDENT"))
    # Barrejar els partits aleatòriament per distribuir millor locals i visitants
    np.random.shuffle(matches)
    df_matches = pd.DataFrame(matches, columns=["Equip 1", "Equip 2", "PENDENT"])

    home_count = {team: 0 for team in teams}  # Comptador de partits a casa per cada equip
    away_count = {team: 0 for team in teams}  # Comptador de partits a domicili per cada equip

    # Assignar local/visitant amb 4 partits locals i 4 partits visitants per equip

    # Si supera les 1000 iteracions vol dir que s'ha quedat encallat en alguna combinació, per tant, tornariem a començar.

    iteracions = 0

    # Aquest bucle s'iterarà fins que tots els equips tinguin 4 partits com a locals (aka tots els partits estiguin ja assignats si son de local o visitant)
    while any(value != 4 for value in home_count.values()):
        iteracions += 1
        # Seleccionem un partit random dels 144
        random_partit = random.randint(0, 143)
        partit = df_matches.iloc[random_partit]
        # Si encara no està assignat
        if partit['PENDENT'] == 'PENDENT':
            team1 = partit['Equip 1']
            team2 = partit['Equip 2']
            # Mirem si el podem posar amb team1 com a local i team2 com a away.
            if home_count[team1] < 4 and away_count[team2] < 4:
                home_count[team1] += 1
                away_count[team2] += 1
                df_matches.iloc[random_partit]['PENDENT'] = 'HOME'
            # Si no, al revés, posem el team1 com a away i el team2 com a local
            elif home_count[team2] < 4 and away_count[team1] < 4:
                home_count[team2] += 1
                away_count[team1] += 1
                df_matches.iloc[random_partit]['PENDENT'] = 'AWAY'
            # Sino compleix cap de les 4, esborrem un partit ja guardat i afegim el partit que estem iterant actualment
            else:
                hc_t1 = home_count[team1]
                ac_t1 = away_count[team1]
                hc_t2 = home_count[team2]
                ac_t2 = away_count[team2]
                # Si t1 té més partits assignats que t2
                if hc_t1 + ac_t1 > hc_t2 + ac_t2:
                    # Si t1 ja te els 4 partits de home
                    if hc_t1 == 4:
                        # treure-li un partit de home al t2, perque t1, pugui fer ple
                        df_matches,home_count,away_count,boolean_deleted = trobar_i_intercanviar(df_matches, team2, team1, home_count, away_count, 'HOME')
                        if boolean_deleted:
                            df_matches.loc[random_partit, 'PENDENT'] = 'AWAY'
                            home_count[team2] += 1
                            away_count[team1] += 1
                    # Si t1 ja te els 4 partits d'away
                    if ac_t1 == 4:
                        # treureli un partit de away al t2, perque t1, pugui fer ple
                        df_matches,home_count,away_count,boolean_deleted = trobar_i_intercanviar(df_matches, team2, home_count, away_count, 'AWAY')
                        if boolean_deleted:
                            df_matches.iloc[random_partit]['PENDENT'] = 'HOME'
                            home_count[team1] += 1
                            away_count[team2] += 1
                # Si t1 té més partits assignats que t2
                else:
                    # Si t2 ja te els 4 partits de home
                    if hc_t2 == 4:
                        # treureli un partit de home al t1, perque t2, pugui fer ple
                        df_matches,home_count,away_count,boolean_deleted = trobar_i_intercanviar(df_matches, team1, home_count, away_count, 'HOME')
                        if boolean_deleted:
                            df_matches.iloc[random_partit]['PENDENT'] = 'HOME'
                            home_count[team1] += 1
                            away_count[team2] += 1
                    # Si t2 ja te els 4 partits d'away
                    if ac_t2 == 4:
                        # treureli un partit de away al t1, perque t2, pugui fer ple
                        df_matches, home_count, away_count, boolean_deleted = trobar_i_intercanviar(df_matches, team1, home_count, away_count, 'AWAY')
                        if boolean_deleted:
                            df_matches.iloc[random_partit]['PENDENT'] = 'AWAY'
                            home_count[team2] += 1
                            away_count[team1] += 1

        # Si arribem a les 10000 iteracions, és que la cosa s'ha complicat molt, per lo que sortim de la funció perque es torni a cridar i l'assignació de local/vistant començi de nou
        if iteracions == 10000:
            print("Repetim :(")
            return "None"

    # Els MATCHES en AWAY els hi canviem l'ordre de Equip1, Equip2 i els passem a HOME
    mask = df_matches["PENDENT"] == "AWAY"
    df_matches.loc[mask, ["Equip 1", "Equip 2"]] = df_matches.loc[mask, ["Equip 2", "Equip 1"]].values
    fase_lliga_imatge(df_matches[['Equip 1', 'Equip 2']], equips)  # Funció que ens mostra el resultat del sorteig de forma visual
    return df_matches[['Equip 1', 'Equip 2']]


def mides_escut(escut, mida_eix):
    '''
    Funció que rep l'escut en imatge i retorna les mides que ha de tenir
    :param escut: escut en imatge
    :return: mides que ha de tenir (amplada, alçada)
    '''
    amplada, alçada = escut.size
    # Si els escuts tenen la mateixa alçada que amplada
    if abs(amplada - alçada) / max(amplada, alçada) < 0.05:
        mides = (mida_eix, mida_eix)  # Definim que ha de tenir la mateixa alçada que amplada
    # Si no, apliquem una fórmula per calcular les mides que ha de tenir sense que l'escut es quedi "xafat" ni que sobresurti
    else:
        valor_ = amplada / alçada
        x = math.sqrt(mida_eix**2 / valor_)
        mides = (round(valor_ * x), round(x))
        if valor_ < 0.65:  # escuts especial com els del Tottenham, que desborden
            mides = (round(valor_ * x * (valor_ + 0.3)), round(x * (valor_ + 0.3)))
    return mides


def fase_lliga_imatge(df_matches, equips):
    '''
    En aquesta funció es mostren 4 imatges. Cada una d'elles conté els 9 equips d'un POT i els seus 8 rivals
    :param df_matches: Dataset generat a definim_local_visitant
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    '''
    # Carreguem una plantilla d'imatge
    image_path = "inputs/League phase.jpeg"
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\GOTHICB.ttf", 20)

    # Per a cada 1 dels 36 equips de la UCL
    for idx, row in equips.iterrows():
        # -- Primerament tractarem l'escut de l'equip en qüestió --
        equip_omplir = row["Club"]
        escut_path = equip_omplir + ".png"
        escut = Image.open("static/escuts/" + escut_path).convert("RGBA")
        # Calculem les mides que ha de tenir l'escut
        mides = mides_escut(escut, 50)
        # Actualitzem el tamany de l'escut segons les mides calculades
        escut = escut.resize(mides, Image.ANTIALIAS)
        # Definim en quina posició de la imatge hi posarem l'escut
        pos_x = 69 - mides[0] // 2
        pos_y = (208 + (idx % 9) * 69) - mides[1] // 2
        img.paste(escut, (pos_x, pos_y), escut)  # Enganxem l'escut a la plantilla

        # -- Al costat d'aquest equip hi posarem l'escut dels 8 rivals --
        rivals = [False] * 8  # Llista de 8 booleans. Representen les posicions on hi posarem els escuts
        for idx2, row2 in df_matches.iterrows():
            # Iterem els 144 matches fins trobar-ne un on el nostre equip_omplir hi jugui
            if (equip_omplir in row2["Equip 1"]) or (equip_omplir in row2["Equip 2"]):
                equip_1 = row2["Equip 1"]
                equip_2 = row2["Equip 2"]
                # Seleccionem el contrincant
                contricant = equip_2 if equip_1 == equip_omplir else equip_1 if equip_2 == equip_omplir else equip_1
                # Seleccionem el POT del contrincant
                pot_contrincant = equips.loc[equips['Club'] == contricant, 'POT'].values[0]
                # Cada POT té 2 posicions on posarhi el escut. Si la 1a posició ja està agafada, el posarem a la 2a
                if rivals[(pot_contrincant*2)-2] == False:
                    rivals[(pot_contrincant * 2) - 2] = True
                    pos_escut_contricant = (pot_contrincant*2)-2
                else:
                    pos_escut_contricant = (pot_contrincant * 2) - 1
                escut2_path = contricant + ".png"
                escut2 = Image.open("static/escuts/" + escut2_path).convert("RGBA")  # Assegurar RGBA
                mides2 = mides_escut(escut2, 50)
                # Actualitzem el tamany de l'escut segons les mides calculades
                escut2 = escut2.resize(mides2, Image.ANTIALIAS)
                # Definim en quina posició de la imatge hi posarem l'escut
                pos_x = (146 + pos_escut_contricant * 74) - mides2[0] // 2
                pos_y = (208 + (idx % 9) * 69) - mides2[1] // 2
                img.paste(escut2, (pos_x, pos_y), escut2)  # Enganxem l'escut a la plantilla

        # Per a cada 9 equips (i els seus 8 rivals) mostrem la imatge
        if (idx%9) == 8:
            # Afegim text amb el POT del qual estem veient els equips
            pot = "POT"+str((idx // 9)+1)
            draw.text((45, 146), pot, fill="black", font=font)
            # Obrim una finestra amb la imatge
            finestra = tk.Tk()
            finestra.title(f"Oponents del {pot} - Fes clic per continuar")
            nova_mida = (int(img.width * 0.90), int(img.height * 0.90))
            img = img.resize(nova_mida, Image.LANCZOS)
            imatge_tk = ImageTk.PhotoImage(img)
            label = tk.Label(finestra, image=imatge_tk)
            label.pack()
            # Aturem el codi fins que l'usuari faci click. Aleshores mostarà la següent foto
            def clic(event):
                finestra.destroy()

            finestra.bind("<Button-1>", clic)
            finestra.mainloop()

            # "Buidem" la imatge per omplir-la amb els escuts del següent POT
            image_path = "inputs/League phase.jpeg"
            img = Image.open(image_path)
            # 📌 Crear un objecte per dibuixar sobre la imatge
            draw = ImageDraw.Draw(img)
    return


def assignar_jornades(df_matches, equips):
    '''
    Tenim ja els 144 enfrentaments i quins són local i visitant. En aquesta funció assignem a cada partit la jornada en la que es jugarà
    :param df_matches: Dataset generat a definim_local_visitant
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :return: df_matches actualitzat en el que s'ha afegit la jornada
    '''
    # Creem una nova columna on hi guardarem el núm de jornada d'aquell partit (del 1 al 8)
    # De primeres tots els partits tenen assignada una jornada 0, que posteriorment es canviarà
    df_matches["Jornada"] = 0

    # Diccionari on guardem, per a cada jornada, els equips que hi disputen partit.
        # L'hem d'emplenar de manera que hi hagi els 36 equips a cada jornada, sense que estiguin repetits
    equips_jornada = {}

    # Anem jornada a jornada omplint-la de partits
    for num_jornada in range(1, 9):
        iteracions = 0
        # Seleccionem aquells partits no assignats (jornada = 0)
        df_matches_mini = df_matches[df_matches['Jornada'] == 0]
        equips_jornada[num_jornada] = []
        count = 0
        while len(equips_jornada[num_jornada]) != 36:
            # Ordenem de manera aleatòria els partits
            df_matches_mini = df_matches_mini.sample(frac=1, random_state=None).reset_index(drop=True)
            # Anem iterant partit a partit
            for num in range(len(df_matches_mini)):
                match = df_matches_mini.iloc[num]
                # Si cap dels equips ja està a la jornada, hi afegim el partit
                if (match['Equip 1'] not in equips_jornada[num_jornada]) and (match['Equip 2'] not in equips_jornada[num_jornada]):
                    equips_jornada[num_jornada].append(match['Equip 1'])
                    equips_jornada[num_jornada].append(match['Equip 2'])
                    df_matches_mini.loc[num, 'Jornada'] = num_jornada
                # Si no, passem al següent
                else:
                    pass
                count += 1

            # Un cop hem acabat d'iterar tots els partits
            ## Si hem aconseguit posar-hi els 36 equips, passarem a la següent jornada
            if len(equips_jornada[num_jornada]) == 36:
                df_matches.set_index(['Equip 1', 'Equip 2'], inplace=True)
                df_matches_mini.set_index(['Equip 1', 'Equip 2'], inplace=True)
                df_matches.update(df_matches_mini)  # Actualitza només les coincidències
                # Reset index per recuperar el format original
                df_matches.reset_index(inplace=True)
                print(df_matches)

                df_matches.to_csv("partits_per_jornada_2.csv", index=False)

            ## Si no, buidem els equips que haviem definit d'aquesta jornada i
            ## buidem també la llista de equips_jornada de la jornada en qüestió
            else:
                df_matches_mini.loc[df_matches_mini["Jornada"] == num_jornada, "Jornada"] = 0
                equips_jornada[num_jornada] = []
                iteracions += 1
                print("Cont", iteracions)
                # La jornada 7 és la que ha de fer més iteracions, ja que, al tenir molts pocs partits disponibles, les combinacions correctes són molt poques
                if iteracions == 200:
                    if num_jornada != 7:
                        return "None"
                    return "None"
                if iteracions == 2000:
                    return "None"
    return df_matches


def partit(equip_local, equip_visitant, jornada, taula, equips):
    '''
    Funció que simula un partit
    No dona gols, sino que simplement dona Victoria, Derrota o Empat de l'equip local
    :param equip_local: Equip local del partit. El resultat retornat serà sobre aquest-
    :param equip_visitant: Equip visitant del partit
    :param jornada: Número de jornada o ronda eliminatòria (1,2,3,4,5,6,7,8,"0F1","0F2","VF1","VF2","QF1","QF2","SF1","SF2","FF0")
    :param taula: Taula de la Fase Lliga
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :return: 0 (Victòria), 1 (Derrota) o 2 (Empat) de l'Equi Local
    '''
    # Per simular un partit es tenen en compte els "punts de poder" d'un equip. Com més en tingui millor
    print(equip_local, equip_visitant)

    # -- Primer de tot definim i modifiquem el punts de poder i l'elevat, que són variables que intervenen a l'hora de calcular el resultat d'un partit --
    elevat = 15
    # Al equip local se li suma +2 als punts de poder
    puntspoder_equip_local = int(equips[equips["Club"] == equip_local]['Points']) + 2
    # Al equip visitant se li resta -1 als punts de poder
    puntspoder_equip_visitant = int(equips[equips["Club"] == equip_visitant]['Points']) - 1
    # A l'última jornada de la Fase Lliga canviem les probabilitats d'alguns equips
    if jornada == 8:
        punts_pos8 = taula.iloc[8]["Punts"]
        punts_pos24 = taula.iloc[23]["Punts"]
        for num, tim in enumerate([equip_local, equip_visitant]):
            # si els equips grans es jugen la classificació, a l'última jornada es posen les piles
            if int(equips[equips["Club"] == tim]['Points']) >= 82:
                if int(taula[taula["Club"] == tim]['Punts']) <= punts_pos24:
                    elevat = 20  # passem d'un elevat de 15 a 20, amb lo cual l'equip amb més punts és encara més favorit
            # quan un equip està matemàticament calssificat, jugarà amb suplents l'última jornada
            if int(taula[taula["Club"] == tim]['Punts']) - 3 > punts_pos8:
                # Li restem 10 punts de poder
                if num == 0:
                    puntspoder_equip_local -= 10
                elif num == 1:
                    puntspoder_equip_visitant -= 10
    # Si és una ronda eliminatòria
    if len(str(jornada)) > 1:
        # si és una tornada (bracket phase), el local té +1 el favorit és encara més favorit
        if jornada[2] == '2':
            puntspoder_equip_local += 1
        # si és la final, es desfà l'aventatge de local i viistant donat al començament de tot
        elif jornada == 'FF0':
            puntspoder_equip_local -= 2
            puntspoder_equip_visitant += 1
            elevat = 20
        # El Real Madrid a les rondes eliminatòries està més Chetat. Se li suma +1
        if equip_local == 'Real Madrid':
            puntspoder_equip_local += 1
        elif equip_visitant == 'Real Madrid':
            puntspoder_equip_visitant += 1
    # Fase Lliga
    else:
        # El Real Madrid a la Fase Lliga té mal rendiment
        if equip_local == 'Real Madrid':
            puntspoder_equip_local -= 1
        elif equip_visitant == 'Real Madrid':
            puntspoder_equip_visitant -= 1

    # -- Definició de la fórmula --
    # Amb aquestes línies afegim la probabilitat de que la victòria sigui per un equip o per l'altre
    total = puntspoder_equip_local ** elevat + puntspoder_equip_visitant ** elevat
    perctgs = [puntspoder_equip_local ** elevat / total, puntspoder_equip_visitant ** elevat / total]
    # Amb les de baix, afegim un percentatge d'empat. Com més igualada estigui l'eliminatòria més percentatge d'empat hi haurà
    if perctgs[0] < 0.05 or perctgs[1] < 0.05:
        empat = 0.02
    elif perctgs[0] < 0.1 or perctgs[1] < 0.1:
        empat = 0.04
    elif perctgs[0] < 0.2 or perctgs[1] < 0.2:
        empat = 0.08
    elif perctgs[0] < 0.30 or perctgs[1] < 0.30:
        empat = 0.14
    elif perctgs[0] < 0.35 or perctgs[1] < 0.35:
        empat = 0.18
    elif perctgs[0] < 0.4 or perctgs[1] < 0.4:
        empat = 0.20
    elif perctgs[0] < 0.45 or perctgs[1] < 0.45:
        empat = 0.25
    elif perctgs[0] <= 0.5 or perctgs[1] <= 0.5:
        empat = 0.28

    # a la final no hi pot haver empat
    if jornada == 'FF0':
        empat = 0

    # Redefinim els percantatges, afegint-hi la probabilitat d'empat
    perctgs_amb_empat = [perctgs[0] * (1 - empat), perctgs[0] * (1 - empat) + perctgs[1] * (1 - empat)]
    print(perctgs_amb_empat, puntspoder_equip_local, puntspoder_equip_visitant)

    num = random.random()  # Genera un número entre 0 i 1

    posicio_bisect = bisect.bisect(perctgs_amb_empat, num)  # Retorna la posició on s'hauria d'inserir (0, 1 o 2)
    # Si posicio_bisect 0 --> Victòria Local, 1 --> Victòria Visitant, 2 --> Empat)
    print(posicio_bisect)
    return posicio_bisect


def desempat(equips_empatats):
    '''
    Com que a la classificació no hi ha Diferència de Gols, molts equips queden empatats a punts després de la J8.
    També s'utilitza per quan a una ronda eliminatòria, 2 equips empaten a "resultats"
    Amb aquesta funció com bé diu el nom, ho desmpatem, tenint en compte que el que té més punts de poder, té més probabilitat
    :param equips: Llista dels equips empatats
    :return: equips_ordenat: Llista d'equips ordenada després del "desempat"
    '''
    # Inicialitzem variables i llistes
    longitud_equips = len(equips_empatats)
    equips_nom_list = []
    equips_ordenat = []  # Llista final a retornar
    elevat = 10
    probabilities = []
    for eq in equips_empatats:
        # Omplim equips_nom_list amb els noms dels equips a desempatar
        equips_nom_list.append(eq['Club'])
        # Omplim probabilities amb eq['Points']**10
        probabilities.append(eq['Points'] ** elevat)

    while longitud_equips != len(equips_ordenat):
        total = sum(probabilities)
        probabilities_final = []
        compt_prob = 0
        # Convertim la llista de probabilities a un rang de 0 a 1 i la guardem a probabilities_final
        for prb in probabilities:
            compt_prob = compt_prob + prb / total
            probabilities_final.append(compt_prob)
        print(probabilities_final)

        num = random.random()  # Genera un número entre 0 i 1

        print(num)
        posicio_bisect = bisect.bisect(probabilities_final, num)  # Retorna la posició on s'hauria d'inserir

        # Afegim l'equip de la posicio_bisect a equips_ordenat
        equips_ordenat.append(equips_nom_list[posicio_bisect])
        # Eliminem aquest equip de equips_nom_listi probabilities
        equips_nom_list.pop(posicio_bisect)
        probabilities.pop(posicio_bisect)
    return equips_ordenat


# FUNCIONS I VARIABLES NECESSÀRIES PER GENERAR I MOSTRAR HTMLS AMB FLASK

html_complet = ""
html_table = ""  # també global per comoditat
jornada = 0
evento = threading.Event()
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    '''
    Si rep un POST atura el servidor Flask
    :return: La pàgina HTML
    '''
    if request.method == "POST":
        print("POST rebut. Alliberant event...")
        evento.set()

        # 🔻 Tanquem el servidor Flask
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()

    return render_template_string(html_complet, html_table=html_table, jornada=jornada)

def espera_click():
    '''
    Funció que controla quan rep un click per continuar el codi
    '''
    print("Esperant clic del botó al navegador...")
    evento.wait()
    print("Clic rebut! Continuant el codi...")


def html_results_fase_lliga(resultats_jornada, jornada, clica_aqui):
    '''
    Genera l'HTML amb els resultats de cada jornada (8 jornades de FaseLliga + Playoff)
    :param resultats_jornada: Llista amb els resultats. Format [equip1, 'E/W/L', equip2, 'E/W/L']
    :param jornada: Jornada de Fase Lliga o Play-offs
    :param clica_aqui: Missatge que es mostrarà en el "clica aquí" (següent jornada o veure bracket)
    '''
    global html_complet, evento

    html_output = []
    def resultat_class(g1, g2):
        '''
        Transforma les "W", "L" i "E" a "win", "loss" i "draw"
        :param g1: Resultat equip local
        :param g2: Resultat equip visitant
        :return: resultat del partit "win", "loss" i "draw" en (resultat_local, resultat_visitant)
        '''
        if g1 > g2:
            return "win", "loss"
        elif g1 < g2:
            return "loss", "win"
        else:
            return "draw", "draw"

    # Per a cada partit, mostrarà:
        # els escuts i noms dels equips enfrontats
        # El seu resultat ("W", "L" o "E")
        # L'escut rodejat per un quadrat verd, en cas de victòria, vermell en cas de derrota i groc en cas d'empat
    for equip1, g1, equip2, g2 in resultats_jornada:
        class1, class2 = resultat_class(g1, g2)
        bloc = f"""
        <div class="card">
          <div class="teams">
            <img src="static/escuts/{equip1}.png" alt="{equip1}" class="team-logo {class1}">
            <div class="score">{g1} - {g2}</div>
            <img src="static/escuts/{equip2}.png" alt="{equip2}" class="team-logo {class2}">
          </div>
          <div class="team-names"><strong>{equip1} vs {equip2}</strong></div>
        </div>
        """
        html_output.append(bloc.strip())

    # Ara afegim el codi HTML complet
    html_complet = f"""
    <!DOCTYPE html>
    <html lang="ca">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultats {jornada}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f4f4f4;
      margin: 0;
      padding: 20px;
    }}
    
    .boton {{
        display: block;
        margin: 0 auto 30px auto;
        padding: 10px 20px;
        background-color: #051080;
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 16px;
        cursor: pointer;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }}

    .card {{
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        padding: 15px;
        text-align: center;
    }}

    .teams {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }}

    .team-logo {{
      width: 60px;
      height: 60px;
      object-fit: contain;
      padding: 5px;
      border-radius: 20%;
      border: 5px solid transparent;
    }}

    .win {{
      border-color: green;
      background-color: #d4edda;
    }}

    .loss {{
      border-color: red;
      background-color: #f8d7da;
    }}

    .draw {{
      border-color: orange;
      background-color: #fff3cd;
    }}

    .score {{
      font-size: 1.5em;
      font-weight: bold;
    }}

    .team-names {{
      font-size: 0.9em;
      color: #555;
    }}

    @media (max-width: 768px) {{
      .grid {{
        grid-template-columns: repeat(1, 1fr);
      }}
    }}

    @media (min-width: 769px) and (max-width: 1024px) {{
      .grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}
  </style>
</head>
<body>
        <form method="POST">
            <button class="boton" type="submit">{clica_aqui}</button>
        </form>
        <h1>Resultats {jornada}</h1>
        <div class="grid">
            {"".join(html_output)}
        </div>

    </body>
    </html>
    """

    # Guardem el html en local
    with open("outputs//resultats_jornada.html", "w", encoding="utf-8") as f:
        f.write(html_complet)

    # Fem que es mostri el html al Chrome, a la ruta "http://127.0.0.1:5000"
    evento.clear()
    threading.Thread(target=lambda: app.run(debug=False, use_reloader=False)).start()
    time.sleep(1)  # Espera que Flask arrenqui
    chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    local_path = "http://127.0.0.1:5000"
    subprocess.Popen([chrome_path, local_path])

    espera_click()  # 🔴 Aquí es para el codi fins que es fa clic
    return


def html_table_fase_lliga(league_table_, league_table_anterior, jornada):
    '''
    Genera l'HTML amb la classificació després de cada jornada
    :param league_table_: Classificació actual
    :param league_table_anterior: Classificació en la jornada anterior
    :param jornada: Número de jornada
    '''
    global html_complet, html_table, evento

    def assign_color(row):
        '''
        Assignan color a les files de colors segons si queden a la zona de classificats, playoffs o eliminats
        :param row: Fila a assignar-hi el color
        :return: Color en haxadecimal
        '''
        if row['Posició'] <= 8:
            return '#d2f8d2'
        elif row['Posició'] <= 24:
            return '#f8e79d'
        else:
            return '#f8d7da'

    # Aplicar la funció per crear una nova columna 'Color'
    league_table_['Color'] = league_table_.apply(assign_color, axis=1)

    # Per a aquestes jornades es farà el següent procediment
    if jornada in [2, 3, 4, 5, 6, 7]:
        # Agafem les posicions de la league_table_anterior
        tab2_posicions = league_table_anterior[['Club', 'Posició']].rename(columns={'Posició': 'Posició_tab2'})
        # Fem el merge amb tab1 segons el Club
        tab1_merged = league_table_.merge(tab2_posicions, on='Club', how='left')
        # Calculem la diferència de posició (tab1 - tab2)
        tab1_merged['DIFF JOR. ANTERIOR'] = tab1_merged['Posició_tab2'] - tab1_merged['Posició']
        # Afegim la DIFF JOR. ANTERIOR a la league_table_ (taula original)
        league_table_['DIFF JOR. ANTERIOR'] = tab1_merged['DIFF JOR. ANTERIOR']
        league_table_['DIFF JOR. ANTERIOR'] = league_table_['DIFF JOR. ANTERIOR'].apply(
            lambda x: f"+{x}" if isinstance(x, int) and x > 0 else str(x))
        columnes_filtrar = ['Posició', 'Club', 'Punts', "DIFF JOR. ANTERIOR", "Color"]
    # Per a les jorandes 1 i 8 simplement agafem les columnes a filtrar (on no hi ha la "DIFF JOR. ANTERIOR")
    elif jornada in [1,8]:
        columnes_filtrar = ['Posició', 'Club', 'Punts', "Color"]

    # Filtrem la league_table_ per quedar-nos amb els camps agafats
    filtered_table = league_table_[columnes_filtrar]
    # Genere'm una HTML table a partir de la filtered_table, pero havent-li tret el camp Color
    columnes_filtrar.remove("Color")
    html_table = filtered_table[columnes_filtrar].to_html(index=False,classes="classificacio",border=0, escape=False)

    # Substituim cada fila amb l'atribut style que inclou el color del fons, basat en la columna "Color"
    for index, row in filtered_table.iterrows():
        color = row['Color']
        html_table = html_table.replace(f'<tr>', f'<tr style="background-color: {color};">', 1)


    # Ara afegim el codi HTML complet
    html_complet = f"""
    <!DOCTYPE html>
    <html lang="ca">
    <head>
        <meta charset="UTF-8">
        <title>Classificació Jornada {jornada}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f7f7f7;
                padding: 20px;
            }}
            .boton {{
                display: block;
                margin: 0 auto 30px auto;
                padding: 10px 20px;
                background-color: #051080;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }}
            .boton:hover {{
                background-color: #303fc2;
            }}
            table.classificacio {{
                width: 50%;
                margin: auto;
                border-collapse: collapse;
                box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: center;
            }}
            th {{
                background-color: #051080;
                color: white;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            caption {{
                font-size: 24px;
                margin-bottom: 10px;
                font-weight: bold;
            }}
            .color {{
                background-color: html_table['color'];
            }}
        </style>
    </head>
    <body>
        <form method="POST">
            <button class="boton" type="submit">Clica aquí per a la següent jornada</button>
        </form>
    
        <table class="classificacio">
            <caption>Classificació Jornada {jornada}</caption>
            <tbody>
                {html_table}
            </tbody>
        </table>
    
    </body>
    </html>
    """

    # Guardem el html en local
    with open("outputs\classificacio.html", "w", encoding="utf-8") as f:
        f.write(html_complet)

    # Fem que es mostri el html al Chrome, a la ruta "http://127.0.0.1:5000"
    evento.clear()
    threading.Thread(target=lambda: app.run(debug=False, use_reloader=False)).start()
    time.sleep(1)  # Espera que Flask arrenqui
    chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    local_path = "http://127.0.0.1:5000"
    subprocess.Popen([chrome_path, local_path])
    espera_click()  # 🔴 Aquí es para el codi fins que es fa clic

    print("Ara pots generar la següent jornada.")
    return


def fase_lliga(partits_per_jornada, equips, arribat, pas_a_pas, iters):
    '''
    Funció que simula la Fase Lliga
    :param partits_per_jornada: Pandas dataset amb els 144 partits i la seva jornada
    :param equips: Dataset d'entrada amb els 36 equips i els seus punts de poder, lliga i POT
    :param arribat: Diccionari on guardem, quins equips s'han quedat a FaseLliga, quins als playoffs, quins a Vuitens...
    :param pas_a_pas: Booleà que decideix si mostrar la fase lliga jornada a jornada o només el final (jornada 8)
    :param iters: Número d'iteracions. Si és > 1, no mostrarà la taula final de la FaseLliga
    :return: league_table_ --> Taula final després de les 8 jornades
    '''
    # Definim el camp Jornada de partits_per_jornada com a Integer
    partits_per_jornada.Jornada = partits_per_jornada.Jornada.astype(int)
    # Ordenem partits_per_jornada per jornada
    partits_per_jornada = partits_per_jornada.sort_values(by="Jornada", ascending=True)

    # Creem league_table que serà la classifcació
    league_table = equips.copy()
    league_table["Punts"] = 0
    # Inicialitzem 2 altres league_tables
    league_table_ = ''
    league_table_anterior = ''
    # Llista on hi posarem els resultats de cada jornada
    resultats_jornada = []

    # Iterem partit a partit
    for i in range(144):
        # Guardem el partit, els equips i el núm de jornada en variables
        match = partits_per_jornada.iloc[i]
        equip1 = match['Equip 1']
        equip2 = match['Equip 2']
        jornada = match['Jornada']

        # Simulem el partit cridant a la funció partit()
        resultat = partit(equip1, equip2, jornada, league_table_, equips)
        # Afegim els 3 punts o 1 punt als equips pertinents
        # Guardem el resultat a resultat_partit amb el format [equip1, 'E/W/L', equip2, 'E/W/L']
        if resultat == 0:
            league_table.loc[league_table['Club'] == equip1, 'Punts'] += 3
            resultat_partit = [equip1, 'W', equip2, 'L']
        elif resultat == 1:
            league_table.loc[league_table['Club'] == equip2, 'Punts'] += 3
            resultat_partit = [equip1, 'L', equip2, 'W']
        elif resultat == 2:
            league_table.loc[league_table['Club'] == equip1, 'Punts'] += 1
            league_table.loc[league_table['Club'] == equip2, 'Punts'] += 1
            resultat_partit = [equip1, 'E', equip2, 'E']
        resultats_jornada.append(resultat_partit)

        # Si ja han passat 18 partits (és a dir, s'ha acabat una jornada)
        if i % 18 == 17:
            # Ordenem la classicificació per punts
            league_table = league_table.sort_values(by="Punts", ascending=False)
            league_table_ = league_table.reset_index()
            print(resultats_jornada)
            # Si hem habilitat pas_a_pas
            if pas_a_pas:
                # Afegim la columna posició a la classificació
                league_table_['Posició'] = range(1, len(league_table_) + 1)
                # Cridem a html_results_fase_lliga() perque mostri els resultats
                html_results_fase_lliga(resultats_jornada, "Jornada "+str((i // 18) + 1), "Clica aquí per veure la classificació")
                # Per a les jornades 1 fins la 7
                if (i // 18) <= 6:
                    # Cridem a html_table_fase_lliga() perque mostri la classificació
                    html_table_fase_lliga(league_table_, league_table_anterior, (i // 18)+1)
                    # Fem una còpia de l'estat de la classificació en aquesta jornada
                    league_table_anterior = league_table_.copy(deep=True)
            resultats_jornada = []

    # Agrupem els equips per punts
    grouped = league_table_.groupby('Punts').apply(lambda x: x.to_dict(orient='records')).to_dict()

    # Iterem els grups
    for punts, registros in grouped.items():
        if len(registros) > 1:
            # Si en aquell grup hi ha +1 equip (hi ha hagut empat), cridem a la funció desmpat() que ens dóna un nou ordre
            nou_ordre = desempat(registros)
            # Amb el nou ordre, actualitzem la classificació
            df_reordered = pd.concat([league_table_[league_table_["Club"] == club] for club in nou_ordre])
            df_reordered = pd.concat([df_reordered, league_table_[~league_table_["Club"].isin(nou_ordre)]])
            df_reordered.reset_index(drop=True, inplace=True)
            league_table_ = df_reordered

    league_table_ = league_table_.drop(columns=["index"]) # Eliminem la columna index
    league_table_ = league_table_.reset_index()

    # Rordenem la classificació ja fets tots els desempats
    league_table_ = league_table_.sort_values(by=["Punts", "index"], ascending=[False, True])
    league_table_ = league_table_.drop(columns=["index"])
    league_table_ = league_table_.reset_index().drop(columns=["index"])

    # Cridem a update_results, perque afegeixi els equips eliminats a la fase lliga, al diccionari "arribats"
    for index, row in league_table_.loc[24:].iterrows():
        update_results(arribat, 'FaseLliga', row['Club'])

    # Guardem la classificació final en un csv. Mostrant 3 columnes POS - CLUB - PTS
    league_table_.to_csv('outputs/fase_lliga.csv', index=False)
    with open('outputs/fase_lliga.txt', 'w', encoding='utf-8') as f:
        f.write("POS - CLUB - PTS\n")
        for i, row in enumerate(league_table_.itertuples(), start=1):
            f.write(f"{i} - {row.Club} - {row.Punts}\n")

    # Afegim la posició a la classificació
    league_table_['Posició'] = range(1, len(league_table_) + 1)
    # Cridem a html_table_fase_lliga() perque ens mostri els resultats finals de la Fase Lliga
    if iters == True:
        html_table_fase_lliga(league_table_.reset_index(), league_table_anterior, 8)
    return league_table_


# Bracket phase
def determinar_classificat(equip_local, equip_visitant, codi_anada, codi_tornada, equips):
    '''
    Simula els partits de les rondes eliminatòries i dóna un classificat.
    :param equip_local: equip que té la tornada a casa
    :param equip_visitant: equip que té l'anada a casa
    :param codi_anada: PF1, VF1, QF1 i SF1
    :param codi_tornada: PF2, VF2, QF2 i SF2
    :param equips: Dataset amb els 36 equips i els seus punts de poder, lliga i POT. Punts de poder actualitzats segons el rendiment en fase lliga
    :return: nom de l'equip que passa de ronda
    '''
    # Simula els 2 partits (anada i tornada)
    resultat_anada = partit(equip_visitant, equip_local, codi_anada, "", equips)
    resultat_tornada = partit(equip_local, equip_visitant, codi_tornada, "", equips)
    print(resultat_anada, resultat_tornada)

    # En cas de que l'eliminatòria quedi igualada, crida a desempat() per trobar un guanyador
    if resultat_anada == resultat_tornada:
        # Empat. Cridar a desempat()
        equips_empat = [
            {'Club': eq, 'Points': int(equips[equips["Club"] == eq]['Points'])}
            for eq in [equip_local, equip_visitant]
        ]
        return desempat(equips_empat)[0]
    elif resultat_anada == 0 or resultat_tornada == 1:
        return equip_visitant  # Guanya el visitant
    elif resultat_tornada == 0 or resultat_anada == 1:
        return equip_local  # Guanya el local


def update_results(arribat, fase, eliminat):
    '''
    Funció que afegeix els equips eliminats al diccionari "arribat"
    :param arribat: Diccionari que s'actualitza
    :param fase: Ronda a la que han arribat
    :param eliminat: Equip eliminat
    :return:
    '''
    arribat[fase].append(eliminat)


# Per les rondes eliminatòries mostrarem els escuts a una plantilla. Aquesta llista conté les posicions on s'aniran posant els escuts
escut_posicio_bracet = [[
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0),
                (0, 0), (0, 0)
                ], # playoffs, no s'afegeixen al bracket
                [  # vuitens
                    (72, 95), (72, 174),  # Costat esquerre
                    (72, 312), (72, 391),
                    (72, 529), (72, 608),
                    (72, 746), (72, 825),
                    (1360, 95), (1360, 174),  # Costat dret
                    (1360, 312), (1360, 391),
                    (1360, 529), (1360, 608),
                    (1360, 746), (1360, 825)
                ],
                [  # quarts
                    (426, 195), (426, 291),  # Costat esquerre
                    (426, 629), (426, 727),
                    (1174, 195), (1174, 291),  # Costat dret
                    (1174, 629), (1174, 727)
                ],
                [  # semis
                    (605, 411), (605, 508),  # Costat esquerre
                    (997, 411), (997, 508),  # Costat dret
                ],
                [  # final
                    (799, 244),  # Costat esquerre
                    (799, 672)  # Costat dret
                ],
                [ # guanyador
                    (0,0),
                ]]

def genera_imatge_brackets_final(brackets, escut_posicio_bracet):
    '''
    Aquesta funció mostra la imatge del barcket, que la va "omplint" segons van passant les eliminatòries.
    :param brackets: els brackets però en format llista de llistes
    :param escut_posicio_bracet: Llista amb les posicions d'on van els escuts a l'imatge
    '''
    # Carreguem una plantilla d'imatge
    image_path = "inputs/plantilla_UCL1.jpeg"
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 20)  # Canvia la mida segons necessitis

    iteracions = 0  # Contador d'eliminatòries

    # Per a cada ronda (playoffs, vuitens...)
    for num in range(len(brackets)):
        bracket = brackets[num]
        positions = escut_posicio_bracet[num]

        # 📌 Afegir el text i les imatges a la imatge principal
        for (pos, equip) in zip(positions, bracket):
            # 📷 Afegir la imatge (escut de l'equip)
            # Carreguem una plantilla dels brackets i fem 3 coses:
            # 1. Afegim els escuts (vuitens fins final - iteracions: 15 a 45). La mida de l'escut varia segons la ronda
            if 15 < iteracions < 46:
                if 15 < iteracions < 32:  # vuitens
                    mida_eix = 40
                elif 32 <= iteracions < 44:  # quarts i semis
                    mida_eix = 55
                elif iteracions in (44, 45):  # final
                    mida_eix = 75
                try:
                    escut_path = equip + ".png"
                    escut = Image.open("static/escuts/" + escut_path).convert("RGBA")  # Assegurar RGBA
                    mides_escut_bracket = mides_escut(escut, mida_eix)
                    # Actualitzem el tamany de l'escut segons les mides calculades
                    escut = escut.resize(mides_escut_bracket, Image.ANTIALIAS)
                    # Definim en quina posició de la imatge hi posarem l'escut
                    pos_x = pos[0] - mides_escut_bracket[0] // 2
                    pos_y = pos[1] - mides_escut_bracket[1] // 2
                    img.paste(escut, (pos_x, pos_y), escut)  # Passa la imatge com a màscara

                except Exception as e:
                    print(f"⚠️ No s'ha pogut carregar {escut_path}: {e}")

            # 2. Afegim els noms dels equips (només als vuitens - iteracions: 15 a 31)
            if 15 < iteracions < 32:
                # Mostrem el text
                if equip == "Union Saint-Gilloise": # Cas especial perque el nom és massa llarg
                    equip = "Union SG"
                elif equip == "Glimt": # Cas especial perque el nom és massa llarg
                    equip = "Bodø/Glimt"
                # Segons la llargada del nom, calculem en quina posició estarà per que quedi centrat al quadre
                bbox = draw.textbbox((0, 0), equip, font=font)
                ample = bbox[2] - bbox[0]
                alt = bbox[3] - bbox[1]
                pos_x_text = (pos[0] + 100) - ample // 2
                pos_y_text = (pos[1] - 1) - alt // 2
                # Enganxemel nom de l'equip al bracket
                draw.text((pos_x_text, pos_y_text), equip, fill="black", font=font)

            # Cas especial: Per al guanyador només es mostra "Guanyador" al costat del seu escut (iteració 46)
            if iteracions == 46:
                # Depèn de si ha guanyat el local o vistitant, posarem "Guanyador!" a dalt o a baix
                if brackets[4][0] == brackets[5][0]:
                    mides = (735, 164)
                elif brackets[4][1] == brackets[5][0]:
                    mides = (735, 725)
                font = ImageFont.truetype("arial.ttf", 25)
                # Enganxem el text
                draw.text(mides, "Guanyador!", fill="white", font=font)

            # 3. Mostrem la imatge per pantalla (quarts fins final - iteracions: 32 a 45)
            if iteracions >= 31:
                # Per cada ietarció, carreguem la imatge generada en la anterior iteració
                output_path = "outputs/bracket_UCL_final.png" # 1600 x 1148
                img.save(output_path)

                # Obrim una finestra amb la imatge
                finestra = tk.Tk()
                finestra.title(f"Bracket Phase")
                finestra.attributes("-fullscreen", True)

                # Ajustem la mida
                nova_mida = (int(img.width * 0.8), int(img.height * 0.8))
                img = img.resize(nova_mida, Image.LANCZOS)
                imatge_tk = ImageTk.PhotoImage(img)

                finestra.lift()
                finestra.attributes("-topmost", True)  # Posa la finestra al davant de tot (de forma temporal)
                finestra.after(10, lambda: finestra.attributes("-topmost", False))

                label = tk.Label(finestra, image=imatge_tk)
                label.pack()

                # Aturem el codi fins que l'usuari faci click. Aleshores mostarà la següent foto
                def clic(event):
                    finestra.destroy()

                finestra.bind("<Button-1>", clic)
                finestra.mainloop()

                # Mostrem els brackets
                image_path = "outputs/bracket_UCL_final.png"
                img = Image.open(image_path)
                draw = ImageDraw.Draw(img)

            iteracions += 1
    return


def bracket_phase(leaguephase_table, arribat, equips, iters):
    '''
    Simula i orquestra la fase eliminatòria
    :param leaguephase_table: Classificació final de la Fase de Lliga
    :param arribat: Diccionari on guardem quins equips s'han quedat a FaseLliga, quins als playoffs, quins a Vuitens...
    :param equips: Dataset amb els 36 equips i els seus punts de poder, lliga i POT. Punts de poder actualitzats segons el rendiment en fase lliga
    :param iters: Número d'iteracions. Si és > 1, no mostrarà els playoffs i el bracket
    '''
    def determine_and_assign(equip1, equip2, fase, position, bracket, equips):
        '''
        Afegim el classificat al bracket.
        :param equip1: equip que té la tornada a casa
        :param equip2: equip que té l'anada a casa
        :param fase: Ronda (playoffs, vuitens...)
        :param position: Posició a la Fase Lliga
        :param bracket: rondes eliminatòries (brackets) en format llista de llistes
        :param equips: Dataset amb els 36 equips i els seus punts de poder, lliga i POT. Punts de poder actualitzats segons el rendiment en fase lliga
        :return: equip classificat
        '''
        # Cridem a determinar_classificat() que ens retorna el classificat entre els 2 equips
        classificat = determinar_classificat(equip1, equip2, fase + "1", fase + "2", equips)
        bracket[position] = classificat
        return classificat

    # -- Playoffs (setzens) --
    # Numpy array on hi guardarem el bracket_8s (és a dir, el equips que s'enfrontaran a vuitens)
    bracket_8s = np.empty(16, dtype='U20')
    matchups_list = []     # Llista d'enfrentaments
    resultats_playoffs = []  # Resultats dels playoffs en format [[Equip1, W/L, Equip2, W/L], [Equip3, W/L, Equip4, W/L]...]
    # 9o10 vs 24o23 --> Gunaydaor anirà a les posicions 1 o 6 del bracket (VS els que han quedat 7è i 8è de la FaseLliga)
    # 11o12 vs 22o21 --> Gunaydaor anirà a les posicions 2 o 5 del bracket (VS els que han quedat 5è i 6è de la FaseLliga)
    # 13014 vs 20o19 --> Gunaydaor anirà a les posicions 4 o 3 del bracket (VS els que han quedat 3r i 4t de la FaseLliga)
    # 15o16 vs 18o17 --> Gunaydaor anirà a les posicions 0 o 7 del bracket (VS els que han quedat 1è i 2n de la FaseLliga)
    for i, j, position in zip([8, 10, 12, 14], [23, 21, 19, 17], [[1, 6], [2, 5], [4, 3], [0, 7]]):
        # equips del playoff amb tornada a casa
        equip1, equip2 = leaguephase_table.iloc[i]['Club'], leaguephase_table.iloc[i + 1]['Club']
        # equips del playoff amb anada a casa
        equip3, equip4 = leaguephase_table.iloc[j - 1]['Club'], leaguephase_table.iloc[j]['Club']

        # Sorteig eliminatòries - Cada equip té 2 possibles rivals
        # A cada iteració fem 2 matchups. Amb un total de 4 iteracions
        matchups = [(equip4, equip1), (equip3, equip2)] if random.choice([True, False]) else [(equip3, equip1), (equip4, equip2)]
        matchups_list.append(matchups[0])
        matchups_list.append(matchups[1])

        # Simulem cada els 2 matchups
        for i, (equip_a, equip_b) in enumerate(matchups):
            # Equip classificat. També actualitza bracket_8s posant-hi l'equip classificat
            classificat = determine_and_assign(equip_a, equip_b, "0F", position[i] * 2, bracket_8s, equips)
            # Actualitzem el diccionari "arribat" afegint-hi l'equip eliminat
            eliminat_a_playoffs = equip_a if classificat != equip_a else equip_b
            update_results(arribat, 'Playoffs', eliminat_a_playoffs)
            # Afegim el resultat del matchup a resultats_playoffs
            resultat = ['W', 'L'] if classificat == equip_a else ['L', 'W']
            resultats_playoffs.append([equip_a, resultat[0], equip_b, resultat[1]])

    # Creem i omplim el brakcet_playoffs amb els 8 matchups dels 16 equips que juguen el playoff
    bracket_playoffs = []
    for t1_num in range(0, 16, 2):
        t1 = bracket_8s[t1_num]
        for match in matchups_list:
            if t1 in match:
                bracket_playoffs.append(match[0])
                bracket_playoffs.append(match[1])

    # Afegim a bracket_8s els quips classificats directament de la FaseLliga
    for a, b, position in zip([0, 2, 4, 6], [1, 3, 5, 7], [[0, 7], [1, 6], [2, 5], [3, 4]]):
        # Agafem 4 parelles d'equips (1,2), (3,4), (5,6) i (7,8)
        classificat_top8_1 = leaguephase_table.iloc[a]['Club']
        classificat_top8_2 = leaguephase_table.iloc[b]['Club']
        # Aleatòriament afegim un a una banda del quadre i l'altra, a l'altra banda
        if random.choice([True, False]):
            bracket_8s[position[0] * 2 + 1] = classificat_top8_1
            bracket_8s[position[1] * 2 + 1] = classificat_top8_2
        else:
            bracket_8s[position[0] * 2 + 1] = classificat_top8_2
            bracket_8s[position[1] * 2 + 1] = classificat_top8_1

    # -- Vuitens --
    print("Vuitens", bracket_8s)

    # Numpy array on hi guardarem el bracket_4s (és a dir, el equips que s'enfrontaran a quarts)
    bracket_4s = np.empty(8, dtype='U20')
    for i in range(0, 16, 2):
        # Agafem el primer vs segon equip del bracket_8s, el tercer vs quart...
        equip1, equip2 = bracket_8s[i], bracket_8s[i + 1]
        # Cridem a determine_and_assign() per simular el macthup, treient-ne un guanyador i actualitzant el bracket_8s
        bracket_4s[int(i / 2)] = determine_and_assign(equip1, equip2, "VF", int(i / 2), bracket_4s, equips)
        # Actualitzem el diccionari "arribat" afegint-hi l'equip eliminat
        eliminat_a_vuitens = equip2 if equip1 == bracket_4s[int(i / 2)] else equip1
        update_results(arribat, 'Vuitens', eliminat_a_vuitens)


    # -- Quarts --
    print("Quarts", bracket_4s)

    # Numpy array on hi guardarem el equips que s'enfrontaran a semis
    bracket_semis = np.empty(4, dtype='U20')
    for i in range(0, 8, 2):
        # Agafem el primer vs segon equip del bracket_4s, el tercer vs quart...
        equip1, equip2 = bracket_4s[i], bracket_4s[i + 1]
        # Cridem a determine_and_assign() per simular el macthup, treient-ne un guanyador i actualitzant el bracket_4s
        classificat_x_semis = determine_and_assign(equip1, equip2, "QF", int(i / 2), bracket_semis, equips)
        # Actualitzem el diccionari "arribat" afegint-hi l'equip eliminat
        eliminat_a_quarts = equip2 if equip1 == classificat_x_semis else equip1
        update_results(arribat, 'Quarts', eliminat_a_quarts)


    # -- Semis --
    print("Semis", bracket_semis)

    # Numpy array on hi guardarem el equips que s'enfrontaran a la final
    bracket_final = np.empty(2, dtype='U20')
    for i in range(0, 4, 2):
        # Agafem el primer vs segon equip del bracket_semis i el tercer vs quart
        equip1, equip2 = bracket_semis[i], bracket_semis[i + 1]
        # Cridem a determine_and_assign() per simular el macthup, treient-ne un guanyador i actualitzant el bracket_semis
        classificat_x_final = determine_and_assign(equip1, equip2, "SF", int(i / 2), bracket_final, equips)
        # Actualitzem el diccionari "arribat" afegint-hi l'equip eliminat
        eliminat_a_semis = equip2 if equip1 == classificat_x_final else equip1
        update_results(arribat, 'Semis', eliminat_a_semis)


    # -- Final --
    print("Final", bracket_final)

    # Seleccionem els equips finalistes
    equip1, equip2 = bracket_final[0], bracket_final[1]
    # Cridem a partit per simular-lo. Al ser una final no hi ha probabilitat d'empat. Extreiem el guanyador
    guanyador = [equip1, equip2][partit(equip1, equip2, "FF0", "", equips)]
    # Actualitzem el diccionari "arribat" afegint-hi l'equip Guanaydor i el que s'ha quedat a les portes!
    update_results(arribat, 'Winner', guanyador)
    eliminat_a_final = equip2 if equip1 == guanyador else equip1
    update_results(arribat, 'Final', eliminat_a_final)

    print("Guanyador de la UCL:", guanyador)

    # En cas que iters = 1
    if iters == 1:
        # Cridem a html_results_fase_lliga() per mostrar de forma visual els resultats dels playoffs
        html_results_fase_lliga(resultats_playoffs, 'Play-offs', "Clica aquí per veure el bracket")
        # Cridem a genera_imatge_brackets_final() per mostrar de forma visual i iterativa el bracket (no es mostra els playoffs)
        genera_imatge_brackets_final([bracket_playoffs, bracket_8s, bracket_4s, bracket_semis, bracket_final, [guanyador]], escut_posicio_bracet)
    return