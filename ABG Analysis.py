#definitions

#defining severity of ards
def ards(fio, pao):
    pf = pao/fio
    if pf < 100:
        rds = "Severe"
    elif pf >= 100 and pf < 200:
        rds = "Moderate"
    elif pf >= 200 and pf < 300:
        rds = "Mild"
    else:
        rds = False
    return rds

#defining respiratory disorder
def respdisorder(pco, exppco):
    if pco > exppco+2:
        respdis = "Respiratory acidosis"
    elif pco < exppco-2:
        respdis = "Respiratory alkalosis"
    else:
        respdis = False
    return respdis

#defining metabolic disorder
def metdisorder(hco, exphco):
    if hco > exphco:
        metdis = "Metabolic alkalosis"
    elif hco < exphco:
        metdis = "Metabolic acidosis"
    else:
        metdis = False
    return metdis

#defining blood disorder
def blooddisorder(ph):
    if ph < 7.4:
        blooddis = "Acidemia"
    elif ph > 7.4:
        blooddis = "Alkalemia"
    else:
        blooddis = False
    return blooddis

#defining anion gap
def aniongap(na, hco, cl):
    ag = na - (cl + hco)
    if ag > 12:
        ag = True
    else:
        ag = False
    return ag

#defining negative value error
def negvalue():
    print("negative value not allowed")

#defining too low or high error
def error(value, lowhi):
    print(f"{value} is too {lowhi}")

#calculating expected pco2
def expco (hco):
    return hco + 15

#calculating expected hco3
def expbicarb(pco, hco, ratio):
    exphco = 24 + ((pco - 40)/10)*ratio
    return exphco

#defining input of Na and Cl and primary disorder and severity
def enternacl():  
    na = 0
    cl = 0  

    #enter Sodium 
    while na < 80 or na > 170:
        na = float(input("Enter Na:"))
        if na < 80:
            error("Na","low")
        elif na > 170:
            error("Na","high")
    #enter Chloride    
    while cl < 70 or cl > 140:
        cl = float(input("Enter Cl:"))
        if cl < 70:
            error("Cl","low")
        elif cl > 140:
            error("Cl","high")
    return na, cl

#defining entering pH, pCO, HCO3, pO2 and FiO2
def enterphpcohcopofio():
    is_abg_valid = False
    po = 0
    fio = 0
    while is_abg_valid == False:
        ph = 0
        pco = 0
        hco = 0
        #pH
        while ph < 6 or ph > 7.7:
            ph = float(input("Enter pH:"))
            if ph < 6:
                error("pH", "low")
            elif ph > 7.7:
                error("pH", "high")

        #pCO2    
        while pco <= 0:
            pco = float(input("Enter pCO2:"))
            if pco < 0:
                negvalue()

        #HCO3
        while hco <= 0:
            hco = float(input("Enter HCO3:"))
            if hco < 0:
                negvalue()
        is_abg_valid = abgisvalid(ph, pco, hco)
        if is_abg_valid == False:
            print("Re-enter values, ABG is not valid!")

    #pO2
    while po <= 0:
        po = float(input("Enter pO2:"))
        if po < 0:
            negvalue()

    #FiO2
    while fio < 0.21 or fio > 1:
        fio = (float(input("Enter FiO2:")))/100
        if fio < 0.21:
            error("FiO2","low")
        elif fio > 1:
            error("FiO2","high")
    return ph, pco, hco, po, fio

#defining taking input of primary disorder and severity if respiratory is primary disorder
def enterprimaryandseverity(value):
    prim = value
    sev = "y"
    while prim != "y" and prim != "n":
        prim = input("Is respiratory primary disorder(y/n):")
    if prim == "y":
        while sev != "a" and sev != "c":
            sev = input("Is respiratory disorder acute or chronic(a/c):")
    return prim, sev

#deciding metabolic acidosis is anion gap or not
def metacidosis(hco):
    nacl = enternacl()
    na = nacl[0]
    cl = nacl[1]
    anion_gap = aniongap(na, cl, hco)
    if anion_gap:
       met_disorder = "Anion gap Metabolic acidosis"
    else:
        met_disorder = "Non gap Metabolic acidosis"
    return met_disorder

#defining printing on analysis
def abganal(primdis, compsec, secdis):
    if not secdis:
        return primdis
    else:
        return primdis + compsec + secdis

#defining validity of ABG
def abgisvalid(ph, pco, hco):
    valhco = 23.9*pco/10**(9-ph)
    if hco < valhco + 0.06*valhco and hco > valhco - 0.06*valhco:
        validity = True
    else:
        validity = False
    return validity

#defintion of ruling out causes and printing probable causes
def causes(disorder1, disorder2, compsec):
    provisional = []
    if disorder1 != False:
        if compsec == secon:
            cause = disorder1.union(disorder2)
        else:
            cause = disorder1
        i = 1
        j = 1
        reselect = "y"
        while reselect == "y":
            
            #going through all the causes for the disorders
            for items in cause:
                userinput = "a"
                while userinput != "y" and userinput != "n":
                    userinput = input(f"{j}) Is {items} a probable reason(yes/no):")
                if userinput =="y":
                    provisional.append(items)
                j+=1
            print("")
            length = len(provisional)
            
            #printing of the causes selected
            if length > 1:
                print(f"The following {length} are the probable causes that you have selected:")
                for item in provisional:
                    print(f"{i}) {item}")
                    i+=1
                    reselect = "n"
            elif length == 1:
                print(f"The following is the probable cause that you have selected:")
                for item in provisional:
                    print(f"{i}) {item}")
                    i+=1
                    reselect = "n"
                    
            #if none of the causes are selected
            else:
                resel = "a"
                print("You did not select any probable causes from the list!")
                while resel != "y" and resel != "n":
                    resel = input("Do you want to go through list again(y/n):")
                reselect = resel


#defining cause1 and cause2
def differentials(disorder):
    if disorder == "Acute Respiratory alkalosis" or disorder == "Chronic Respiratory alkalosis" or disorder == "Respiratory alkalosis":
        return respalkalosis
    elif disorder == "Acute Respiratory acidosis" or disorder == "Chronic Respiratory acidosis" or disorder == "Respiratory acidosis":
        return respacidosis
    elif disorder == "Metabolic alkalosis":
        return metabolicalkalosis
    elif disorder == "Anion gap Metabolic acidosis":
        return highaniongapmetabolicacidosis
    elif disorder == "Non gap Metabolic acidosis":
        return nonaniongapmetabolicacidosis

#defining causes of disorders
respalkalosis = {"Pain","Anxiety","Fever","CVA","Meningitis/Encephalitis","Tumor","Trauma","High altitude","Pneumonia","Pulmonary edema","Aspiration","Severe anemia","Pregnancy","Salicylates","Cardiac failure","Progesterone","Hemothorax","Flail chest","Pulmonary embolism","Sepsis","Hepatic failure","Mechanical hyperventilation","Heat exposure"}
respacidosis = {"Anesthetics","Morphine","Sedatives","Stroke","Infection","Airway obstruction","Asthma","COPD","Pneumoconiosis","ARDS","Barotrauma","Poliomyelitis","Kyphoscoliosis","Myasthenia","Muscular dystrophies","Obesity","Hypoventilation","Permissive hypercapnia"}
metabolicalkalosis = {"Acute alkali administration","Milk-alkali syndrome","Vomiting","Aspiration","Congenital chloridorrhea","Villous adenoma","Diuretics","Posthypercapnic state","Hypercalcemia/Hypoparathyroidism","Penicillin/cabenicillin","Hypomagnesemia","Hypokalemia","Bartter's syndrome","Gitelman's syndrome","Renal artery stenosis","Accelerated hypertension","Renin secreting tumor","Estrogen","Primary aldosteronism","Adrenal enzyme deficiency","Cushing's syndrome","Licorice","Carbenoxolone","Chewer's tobacco","Liddle's syndrome"}
nonaniongapmetabolicacidosis = {"Diarrhea","External pancreatic or small bowel drainage","Ureterosigmoidostomy, jejunal/ileal loop","CaCl","MgSO4","Cholestyramine","Renal Acidosis","K+ sparing diuretics","Trimethoprim","Pentamidine","ACE-I/ARBs","NSAIDs","Calcineurin inhibitors","Acid loads","Loss of potential bicarbonate","Rapid saline administration","Cation exchange raisins","Hippurate"}
highaniongapmetabolicacidosis = {"Lactic acidosis","DKA","Alcoholic ketoacidosis","Starvation ketoacidosis","Ethylene glycol","Methanol","Salicylates","Propylene glycol","Pyroglutamic acid","Sepsis","Uremia","Paraldehyde","Isoniazid","Seizures"}


#display and analysis
print("ABG Analysis")
print("------------")
print("")
cont = "y"
while cont == "y":

    #defining variables
    compen = " with compensated "
    secon = " with secondary "

    #taking inputs
    abginputs = enterphpcohcopofio()
    ph = abginputs[0]
    pco = abginputs[1]
    hco = abginputs[2]
    po = abginputs[3]
    fio = abginputs[4]

    #preliminary calulations for blood disorders
    blood_disorder = blooddisorder(ph)
    resp_disorder = respdisorder(pco, 40)
    met_disorder = metdisorder(hco, 24)

    #analysis of abg

    #if ABG is normal
    if not blood_disorder and not resp_disorder and not met_disorder:
        cause1 = False
        cause2 = False
        abg_analysis ="Normal ABG"

    #if blood pH is normal, but pCO2 and HCO3 are abnormal    
    if not blood_disorder and (resp_disorder != False or met_disorder != False):

        #if resp acidosis present
        if resp_disorder == "Respiratory acidosis":
            primdisorder_severity = enterprimaryandseverity("a")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y": 
                if sev == "a":
                    severity = "Acute"
                    ratio = 1
                elif sev == "c":
                    severity = "Chronic"
                    ration = 3
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)

                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)

                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            #if primarily metabolic disorder
            else:
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)
                
                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon
                    
                primary_disorder = met_disorder
                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)
                
                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

        #if respiratory alkalosis present
        else:
            primdisorder_severity = enterprimaryandseverity("a")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y":
                if sev == "a":
                    severity = "Acute"
                    ratio = 2
                elif sev =="c":
                    severity = "Chronic"
                    ratio = 5
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)
            
            # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)
                
                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            
            #if primarily metabolic disorder
            else:
                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)

                primary_disorder = met_disorder
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)

                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon

                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)
        
    #if Acidemic blood
    if blood_disorder == "Acidemia":

        #if respiratory acidosis present
        if resp_disorder == "Respiratory acidosis":
            primdisorder_severity = enterprimaryandseverity("y")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y": 
                if sev == "a":
                    severity = "Acute"
                    ratio = 1
                elif sev == "c":
                    severity = "Chronic"
                    ratio = 3
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)

                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)

                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            #if primarily metabolic disorder
            else:
                primary_disorder = met_disorder
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)

                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon

                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

        #if respiratory alkalosis present
        else:
            primdisorder_severity = enterprimaryandseverity("n")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y":
                if sev == "a":
                    severity = "Acute"
                    ratio = 2
                elif sev =="c":
                    severity = "Chronic"
                    ratio = 5
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)
            
            # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)
                
                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            
            #if primarily metabolic disorder
            else:
                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)

                primary_disorder = met_disorder
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)

                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon

                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

    #if Alkalemic blood
    if blood_disorder == "Alkalemia":

        #if respiratory alkalosis present
        if resp_disorder == "Respiratory alkalosis":
            primdisorder_severity = enterprimaryandseverity("y")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y": 
                if sev == "a":
                    severity = "Acute"
                    ratio = 2
                elif sev == "c":
                    severity = "Chronic"
                    ratio = 5
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)

                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)
                
                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            #if primarily metabolic disorder
            else:
                primary_disorder = met_disorder
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)

                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon

                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

        #if respiratory acidosis present
        else:
            primdisorder_severity = enterprimaryandseverity("n")
            prim = primdisorder_severity[0]
            sev = primdisorder_severity[1]

            #if primarily respiratory disorder
            if prim == "y":
                if sev == "a":
                    severity = "Acute"
                    ratio = 2
                elif sev =="c":
                    severity = "Chronic"
                    ratio = 5
                exp_hco = expbicarb(pco, hco, ratio)
                met_disorder = metdisorder(hco, exp_hco)
            
            # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)
                
                if not met_disorder:
                    met_disorder = metdisorder(hco, 24)
                    compsec = compen
                else:
                    compsec = secon

                primary_disorder = severity +" " +resp_disorder
                secondary_disorder = met_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)

                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

            
            #if primarily metabolic disorder
            else:
                # special case in case of metabolic acidosis to know if Anion gap present or not
                if met_disorder == "Metabolic acidosis":
                    met_disorder = metacidosis(hco)

                primary_disorder = met_disorder
                exp_co = expco(hco)
                resp_disorder = respdisorder(pco, exp_co)

                if not resp_disorder:
                    resp_disorder = respdisorder(pco, 40)
                    compsec = compen
                else:
                    compsec = secon

                secondary_disorder = resp_disorder
                cause1 = differentials(primary_disorder)
                cause2 = differentials(secondary_disorder)
                
                abg_analysis = abganal(primary_disorder, compsec, secondary_disorder)

    #analyzing respiratory distress
    arespdis = ards(fio,po)
    if not arespdis:
        arespdis = "No"
    abg_analysis_ards = abg_analysis + " with " + arespdis + " ARDS"

    #printing ABG analysis
    print("")
    print("Analysis:")
    print(abg_analysis_ards)
    print("")
    
    #know causes
    userinput = "a"
    if cause1 != False:
        while userinput != "y" and userinput != "n":
            userinput = input("Do you want to go through the possible causes(y/n):")
        if userinput == "y":
            causes(cause1, cause2, compsec)

    cont = "a"
    while cont != "y" and cont != "n":
        cont = input("Do you want to analyze another ABG (y/n)? ")

print("")
print("ABG Analysis designed by Dr. Shoubhik Banerjee")
print("Thank you!")
input("press enter to continue")