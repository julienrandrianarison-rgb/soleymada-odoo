# -*- coding: utf-8 -*-
"""
Générateur déterministe de données SOLEY MADA (pur Python, sans dépendance Odoo).
500 clients, commandes de transit import/export 2020-2025, factures, paiements, factures fournisseurs.

Paramètres (variables d'environnement) :
  SEED, START_DATE, END_DATE, N_CLIENTS, SCALE (1.0 = volume normal ; 0.05 = test rapide)
Test à sec :  python3 soleymada_data.py   (écrit des CSV dans ./export)
"""
import os, re, csv, random, unicodedata, datetime as dt
from collections import defaultdict

SEED = int(os.environ.get("SEED", "2020"))
START = dt.date.fromisoformat(os.environ.get("START_DATE", "2020-01-01"))
END = dt.date.fromisoformat(os.environ.get("END_DATE", "2025-12-31"))
N_CLIENTS = int(os.environ.get("N_CLIENTS", "500"))
SCALE = float(os.environ.get("SCALE", "1.0"))

# ---------------------------------------------------------------- macro-économie
INFL = {2020: 1.00, 2021: 1.05, 2022: 1.12, 2023: 1.20, 2024: 1.28, 2025: 1.36, 2026: 1.42}
FX = {2020: 3780, 2021: 3950, 2022: 4200, 2023: 4400, 2024: 4550, 2025: 4650, 2026: 4700}   # Ar / USD
FRT = {2020: 1.0, 2021: 2.2, 2022: 2.5, 2023: 1.3, 2024: 1.6, 2025: 1.4, 2026: 1.3}          # indice fret

def _yf(table, d):
    return table.get(d.year, table[max(table)])

def _r(x):
    return int(round(x, -3))

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())[:22]

# ---------------------------------------------------------------- produits / coûts
PRODUCTS = {  # code: (nom, taxe par défaut)
    "TRANSIT": "Honoraires de transit & dédouanement (DAU)",
    "BSC": "Frais BSC GasyNet & traçabilité",
    "MANUT": "Manutention, acconage & THC port",
    "HANDLING": "Handling & frais aéroport Ivato",
    "TRANSPORT": "Transport routier RN2",
    "SCANNER": "Frais scanner / expertise douane",
    "MAGASIN": "Magasinage sous douane (MAD)",
    "DEBOURS": "Débours - droits & taxes de douane",
    "FRET": "Fret international (maritime / aérien)",
    "X_BOOKING": "Booking & positionnement conteneur",
    "X_CERTIF": "Certificats (phytosanitaire, origine EUR.1/CO)",
    "X_EMPOTAGE": "Empotage, plombage & contrôle conformité",
    "X_TRANSIT": "Honoraires de transit export (EX1)",
    "X_TRANSPORT": "Transport site exportateur vers Port/Aéroport",
}
COSTS = {  # code: (clé fournisseur, ratio coût / prix de vente)
    "BSC": ("GASYNET", .55), "MANUT": ("MICTSL", .72), "HANDLING": ("ADEMA", .70),
    "TRANSPORT": ("TRANSPORT", .78), "SCANNER": ("DOUANE", .90), "MAGASIN": ("DOUANE", .65),
    "DEBOURS": ("DOUANE", 1.0), "FRET": ("CARRIER", .90), "X_BOOKING": ("CARRIER", .60),
    "X_CERTIF": ("CCI", .60), "X_EMPOTAGE": ("TRANSPORT", .55), "X_TRANSPORT": ("TRANSPORT", .78),
}
SUPPLIERS = {
    "DOUANE": "Direction Générale des Douanes (DGD)",
    "GASYNET": "GasyNet S.A. (Guichet unique BSC)",
    "MICTSL": "MICTSL - Terminal à conteneurs de Toamasina",
    "ADEMA": "ADEMA - Aéroport international d'Ivato",
    "TRANSPORT": "Flotte partenaire RN2 (sous-traitance transport)",
    "CCI": "CCI & Services phytosanitaires",
    "MSC": "MSC Madagascar (armateur)",
    "CMA CGM": "CMA CGM Madagascar (armateur)",
    "Maersk": "Maersk Line Madagascar (armateur)",
    "AIRCARGO": "Compagnies aériennes cargo (Ivato)",
}
CARRIERS = ["MSC", "CMA CGM", "Maersk"]
CARRIER_PREFIX = {"MSC": "MSCU", "CMA CGM": "CMAU", "Maersk": "MAEU"}

# ---------------------------------------------------------------- secteurs
def S(key, label, flux, items, usd, duty, nouns, season=None, air=0.03):
    return dict(key=key, label=label, flux=flux, items=items, usd=usd, duty=duty,
                nouns=nouns, season=season, air=air)

SECTORS = {s["key"]: s for s in [
    S("it_solaire", "Matériel informatique / Solaire", "import", [("Panneaux solaires & onduleurs", "8541.43"), ("Ordinateurs & périphériques", "8471.30"), ("Batteries lithium", "8507.60")], (12000, 70000), .28, ["Solaire", "Tech", "Énergie", "Digital"], air=.12),
    S("btp", "Construction & Génie civil", "import", [("Ciment & fer à béton", "7214.20"), ("Engins de chantier", "8429.51"), ("Carrelage & sanitaires", "6908.90")], (15000, 90000), .30, ["BTP", "Construction", "Matériaux", "Infrastructures"]),
    S("pharma", "Produits pharmaceutiques", "import", [("Médicaments génériques", "3004.90"), ("Consommables médicaux", "9018.90")], (20000, 120000), .20, ["Pharma", "Santé", "Médical"], air=.12),
    S("imprimerie", "Papier & matériel d'imprimerie", "import", [("Papier & carton", "4802.56"), ("Encres & plaques", "3215.11")], (8000, 40000), .28, ["Imprimerie", "Papeterie", "Graphique"]),
    S("auto", "Pièces détachées & véhicules", "import", [("Pièces détachées automobiles", "8708.99"), ("Pneumatiques", "4011.10")], (6000, 50000), .35, ["Auto", "Motors", "Pièces"]),
    S("alim_imp", "Produits alimentaires (riz, farine, huile)", "import", [("Riz", "1006.30"), ("Farine de blé", "1101.00"), ("Huile alimentaire", "1512.19")], (25000, 140000), .22, ["Alimentaire", "Distribution", "Grossiste"]),
    S("electro", "Électroménager & électronique", "import", [("Réfrigérateurs & congélateurs", "8418.10"), ("Téléviseurs", "8528.72")], (10000, 60000), .33, ["Électro", "Ménager", "Store"]),
    S("mines", "Matériel minier & industriel", "import", [("Concasseurs & pompes", "8474.20"), ("Groupes électrogènes", "8502.13")], (30000, 200000), .18, ["Mining", "Industrie", "Équipement"]),
    S("agri_eq", "Équipements & intrants agricoles", "import", [("Engrais NPK", "3105.20"), ("Motoculteurs", "8432.80")], (8000, 45000), .15, ["Agri", "Agro", "Culture"]),
    S("hygiene", "Parapharmacie & hygiène", "import", [("Produits d'hygiène", "3307.90"), ("Savons & détergents", "3401.11")], (9000, 45000), .28, ["Hygiène", "Parapharma", "Soins"], air=.10),
    S("mobilier", "Mobilier & équipement de bureau", "import", [("Mobilier de bureau", "9403.10")], (5000, 30000), .33, ["Mobilier", "Bureau", "Déco"]),
    S("froid", "Froid commercial / Énergie renouvelable", "import", [("Chambres froides modulaires", "8418.50"), ("Compresseurs", "8414.30")], (15000, 80000), .25, ["Froid", "Énergie", "Climat"]),
    S("transport", "Transport & Manutention", "import", [("Camions & remorques", "8704.22"), ("Matériel de manutention", "8427.10")], (20000, 150000), .25, ["Logistique", "Fret", "Transport"]),
    S("divers", "Import divers (négoce)", "import", [("Marchandises diverses (négoce)", "3926.90"), ("Articles ménagers", "3924.90")], (5000, 40000), .30, ["Trading", "Négoce", "Import"]),
    S("textile_in", "Intrants textiles (zone franche)", "import", [("Tissus & fournitures de confection", "5407.52")], (10000, 60000), .12, ["Textile", "Confection", "Tissus"]),
    S("vanille", "Vanille & épices (conditionnement)", "export", [("Vanille Bourbon de Madagascar", "0905.10"), ("Poivre sauvage (Voatsiperifery)", "0904.11"), ("Cannelle", "0906.11")], (20000, 300000), 0, ["Vanille", "Épices", "Aromates"], season={6, 7, 8, 9, 10}),
    S("girofle", "Girofle & clous de girofle", "export", [("Clous de girofle", "0907.10")], (30000, 250000), 0, ["Girofle", "Agro", "Collecte"], season={10, 11, 12, 1}),
    S("huiles", "Huiles essentielles & cosmétiques naturels", "export", [("Huile essentielle d'ylang-ylang", "3301.29"), ("Huile essentielle de niaouli", "3301.29")], (8000, 90000), 0, ["Bio", "Cosmétiques", "Essences"], air=.05),
    S("mer", "Produits halieutiques", "export", [("Crevettes congelées", "0306.17"), ("Poissons congelés", "0303.43")], (30000, 350000), 0, ["Seafoods", "Pêche", "Océan"]),
    S("textile", "Confection & textile (Zone Franche)", "export", [("Vêtements en coton", "6109.10"), ("Pantalons & vestes", "6203.42")], (25000, 400000), 0, ["Textile", "Vêtement", "Confection"]),
    S("cacao", "Cacao, café & litchis", "export", [("Cacao en fèves", "1801.00"), ("Café vert", "0901.11"), ("Litchis frais", "0810.90")], (15000, 150000), 0, ["Cacao", "Café", "Plantation"]),
    S("minerai", "Pierres, graphite & produits miniers", "export", [("Graphite naturel", "2504.10"), ("Pierres fines", "7103.91")], (20000, 500000), 0, ["Minéraux", "Pierres", "Graphite"], air=.05),
    S("bio", "Produits agricoles bio", "export", [("Haricots secs & pois du Cap", "0713.39"), ("Riz bio", "1006.30"), ("Noix de cajou", "0801.32")], (10000, 120000), 0, ["Bio", "Farmland", "Terroir"]),
    S("raphia", "Artisanat & raphia", "export", [("Articles en raphia", "4601.94"), ("Artisanat divers", "4602.19")], (4000, 40000), 0, ["Raphia", "Artisanat", "Créations"]),
]}

# ---------------------------------------------------------------- clients "ancres" (fournis dans le cahier des charges)
def A(name, sector, city, street, label=None, rep=None, nif=None, stat=None, rcs=None):
    return dict(name=name, sector=sector, city=city, street=street, label=label, rep=rep, nif=nif, stat=stat, rcs=rcs)

ANCHORS = {
    1: A("MadaTech Solutions SARLU", "it_solaire", "Antananarivo", "Zone Océan, Immeuble B, Ankorondrano", "Importation et distribution de matériel informatique et panneaux solaires", ("Rija", "RANDRIANARISOA", "Gérant", "M"), "3004589211", "46511 11 2021 0 10245", "2021 B 00452"),
    2: A("SAVA Aromates & Vanille S.A.", "vanille", "Sambava", "Boulevard Joffre", "Conditionnement et exportation d'épices d'exception", ("Sarah", "BENOÎT", "Directrice des Opérations Export", "F"), "4001258744", "01130 31 2018 0 00584", "2018 B 00118"),
    3: A("Électricité & Froid du Grand Sud", "froid", "Toliara", "Avenue de l'Indépendance", "Froid commercial et énergie renouvelable", ("Jean-Luc", "ANDRIANINA", "Directeur Général", "M"), "5008962310", "43210 11 2023 0 04112", "2023 B 00210"),
    4: A("Madagascar BTP & Infrastructures", "btp", "Antananarivo", "Lot II M Ivandry"),
    5: A("Tropic Bio Cosmétiques", "huiles", "Toamasina", "Zone Portuaire Ambodimanga"),
    6: A("Alpha Agro Trading", "girofle", "Mananara", "Rue Principale", "Collecte de Girofle & Poivre"),
    7: A("Delta Pharma Madagascar", "pharma", "Antananarivo", "Zone Andraharo"),
    8: A("Nosy Be Seafoods Export", "mer", "Nosy Be", "Port d'Hell-Ville"),
    9: A("Imprimerie Moderne Iarivo", "imprimerie", "Antananarivo", "Rue Rainandriamampandry, Isoraka"),
    10: A("Sud Énergie Renouvelable", "it_solaire", "Fianarantsoa", "Avenue de la Libération", "Équipements Solaires"),
    100: A("Horizon Textile Madagascar", "textile", "Antsirabe", "Zone Industrielle Antsirabe"),
    200: A("Mahajanga Logistique & Fret", "transport", "Mahajanga", "Zone Portuaire Mahajanga"),
    300: A("Antsiranana Trading Co.", "divers", "Antsiranana", "Rue Colbert", "Import Divers"),
    400: A("Tamatave Bulk & Logistics", "transport", "Toamasina", "Zone Portuaire Ambodimanga", "Consignation & Acconage"),
    496: A("Socota Vêtement Export", "textile", "Antananarivo", "Zone Industrielle Forello Tanjombato"),
    497: A("Cap Est Vanille & Épices", "vanille", "Maroantsetra", "Rue Principale", "Conditionnement Vanille"),
    498: A("Madagascar Mining & Logistics", "mines", "Toamasina", "Zone Portuaire Ambodimanga"),
    499: A("Bio Farmland Mada", "bio", "Fianarantsoa", "Avenue de la Libération"),
    500: A("Vahona Logistique & Services", "hygiene", "Antananarivo", "Lot IVG Ambanidia", None, ("Lalatiana", "RAKOTOARISOA", "Gérante", "F"), "1009874523", "46412 11 2025 0 00892", "2025 A 00150"),
}

CITY_WEIGHTS = [("Antananarivo", 60), ("Toamasina", 15), ("Mahajanga", 10), ("Antsiranana", 6), ("Nosy Be", 4),
                ("Antsirabe", 1), ("Fianarantsoa", 1), ("Toliara", 1), ("Sambava", 1), ("Morondava", 0.5), ("Taolagnaro", 0.5)]
ZIP = {"Antananarivo": "101", "Toamasina": "501", "Mahajanga": "401", "Antsiranana": "201", "Nosy Be": "207", "Antsirabe": "110",
       "Fianarantsoa": "301", "Toliara": "601", "Sambava": "208", "Morondava": "619", "Taolagnaro": "614", "Maroantsetra": "512", "Mananara": "515"}
STREETS = {
    "Antananarivo": ["Zone Océan, Ankorondrano", "Lot II M Ivandry", "Zone Andraharo", "Route de l'Aéroport, Ivato", "Rue Rainandriamampandry, Isoraka", "Avenue de l'Indépendance, Analakely", "Lot IVG Ambanidia", "Zone Forello, Tanjombato", "Route Digue, Behoririka", "Zone Logistique Andranomena"],
    "Toamasina": ["Boulevard Joffre", "Avenue de l'Indépendance", "Zone Portuaire Ambodimanga", "Rue Ratsimilaho", "Bazary Be Sud"],
}
DIST = {"Antananarivo": 1.0, "Toamasina": .25, "Antsirabe": 1.3, "Fianarantsoa": 1.9, "Mahajanga": 1.9, "Toliara": 2.9, "Antsiranana": 3.1,
        "Nosy Be": 3.4, "Sambava": 3.6, "Morondava": 2.8, "Taolagnaro": 3.8, "Maroantsetra": 3.5, "Mananara": 3.3}
FIRST_M = ["Rija", "Hery", "Tiana", "Mamy", "Faly", "Njaka", "Haja", "Jean-Luc", "Toky", "Nirina", "Lova", "Andry", "Santatra", "Tahina", "Fenitra", "Mickaël", "Eric", "Patrick", "Dina", "Tsiry"]
FIRST_F = ["Lalatiana", "Volatiana", "Sarah", "Mialy", "Fanja", "Hasina", "Voahirana", "Miora", "Nirina", "Aina", "Soa", "Tsiky", "Navalona", "Holy"]
LAST = ["RAKOTOARISOA", "RANDRIANARISOA", "ANDRIANINA", "RASOANAIVO", "RABEMANANJARA", "RATSIMBAZAFY", "RAZAFINDRAKOTO", "RAKOTOMALALA", "ANDRIAMAMPIANINA",
        "RAVELOMANANA", "RAJAONARISON", "RANDRIAMANANTENA", "RASOLOFO", "RAHARISON", "RAKOTONIRINA", "ANDRIANJAFY", "RAMANANTSOA", "RASOLONJATOVO", "RAZANAMAHEFA", "RAVOAHANGY"]
PREFIX = ["Mada", "Tana", "Iarivo", "Vahiny", "Ravinala", "Antsa", "Fanilo", "Tsiry", "Haingo", "Soa", "Mahasoa", "Vato", "Rano", "Tolotra", "Fiainana", "Aina", "Nosy",
          "Ankaratra", "Betsimisaraka", "Sakalava", "Tsimihety", "Zafy", "Hasina", "Mirary", "Mandroso", "Rivo", "Harena", "Voary", "Sambatra", "Tafita", "Alpha", "Delta", "Omega",
          "Horizon", "Tropic", "Indigo", "Océan Indien", "Baobab", "Zébu", "Lémur", "Orchidée", "Cap", "Sud", "Nord", "Est", "Ouest", "Grand", "Royal", "Union", "Pacific"]
SUFFIX = ["SARL", "SA", "SARLU", "Madagascar", "Group", "& Fils", "Trading", "International"]
IMPORT_ORIGINS = ["Shanghai (CN)", "Ningbo (CN)", "Guangzhou (CN)", "Durban (ZA)", "Mumbai (IN)", "Singapour (SG)", "Jebel Ali (AE)", "Port Louis (MU)", "Le Havre (FR)", "Marseille (FR)", "Port Klang (MY)", "Mombasa (KE)"]
AIR_ORIGINS = ["Paris CDG (FR)", "Dubaï (AE)", "Nairobi (KE)", "Johannesburg (ZA)", "Bangkok (TH)", "Canton (CN)"]
EXPORT_DEST = ["Le Havre (FR)", "Marseille (FR)", "Rotterdam (NL)", "Hambourg (DE)", "New York (US)", "Jebel Ali (AE)", "Mumbai (IN)", "Shanghai (CN)", "Singapour (SG)", "Port Louis (MU)"]
AIR_DEST = ["Paris CDG (FR)", "Dubaï (AE)", "Nairobi (KE)"]
VESSEL_NAMES = ["Anjara", "Mahavelona", "Ivoloina", "Tsingy", "Ravinala", "Baobab", "Zafimaniry", "Ranomafana", "Isalo", "Masoala", "Andringitra", "Betsiboka"]

FREQ = [(7, .01), (14, .05), (30, .24), (60, .35), (91, .35)]
FREQ_LABEL = {7: "Hebdomadaire", 14: "Bimensuel", 30: "Mensuel", 60: "Bimestriel", 91: "Trimestriel"}
PAYER = [("good", .70), ("slow", .22), ("bad", .08)]


def wchoice(rng, pairs):
    r = rng.random() * sum(w for _, w in pairs)
    for v, w in pairs:
        r -= w
        if r <= 0:
            return v
    return pairs[-1][0]


# ---------------------------------------------------------------- clients
def generate_clients(rng):
    n_imp = round(N_CLIENTS * 0.6)
    anchors = {k: v for k, v in ANCHORS.items() if k <= N_CLIENTS}
    imp_left = n_imp - sum(1 for a in anchors.values() if SECTORS[a["sector"]]["flux"] == "import")
    n_free = N_CLIENTS - len(anchors)
    pool = ["import"] * imp_left + ["export"] * (n_free - imp_left)
    rng.shuffle(pool)
    sect_by_flux = {f: [s for s in SECTORS.values() if s["flux"] == f] for f in ("import", "export")}
    used, clients = set(), []
    total_days = (END - START).days
    for i in range(1, N_CLIENTS + 1):
        a = anchors.get(i)
        flux = SECTORS[a["sector"]]["flux"] if a else pool.pop()
        sec = SECTORS[a["sector"]] if a else rng.choice(sect_by_flux[flux])
        city = a["city"] if a else wchoice(rng, CITY_WEIGHTS)
        street = a["street"] if a else rng.choice(STREETS.get(city, ["Rue Principale", "Avenue de la Libération", "Zone Industrielle"]))
        if a:
            name = a["name"]
        else:
            for _ in range(30):
                name = f"{rng.choice(PREFIX)} {rng.choice(sec['nouns'])} {rng.choice(SUFFIX)}"
                if name not in used:
                    break
            else:
                name = f"{name} {i}"
        used.add(name)
        # date de début : les IDs bas sont les plus anciens clients
        frac = ((i - 1) / max(N_CLIENTS - 1, 1)) ** 2.4
        start = START if i == 1 else START + dt.timedelta(days=int(frac * (total_days - 90)) + rng.randint(0, 20))
        if a and a["stat"]:
            reg_year = int(a["stat"].split()[2])
            start = max(start, dt.date(reg_year, 6, 1)) if reg_year > START.year else start
            if start > END - dt.timedelta(days=60):
                start = END - dt.timedelta(days=60)
        else:
            reg_year = max(2005, start.year - rng.randint(0, 12))
        stop = None
        if i > 1 and rng.random() < .08:
            s = start + dt.timedelta(days=rng.randint(400, 1200))
            stop = s if s < END else None
        if a and a["rep"]:
            rep = a["rep"]
        else:
            g = rng.choice("MF")
            rep = (rng.choice(FIRST_M if g == "M" else FIRST_F), rng.choice(LAST),
                   rng.choice(["Gérant", "Directeur Général", "Responsable Logistique", "Directeur des Opérations"]) if g == "M"
                   else rng.choice(["Gérante", "Directrice Générale", "Responsable Logistique", "Directrice des Opérations"]), g)
        interval = wchoice(rng, FREQ)
        sp = 2 if city not in ("Antananarivo",) else rng.randint(0, 1)
        clients.append(dict(
            id=f"CUST-{i:03d}", idx=i, name=name, flux=flux, sector=sec["key"], sector_label=(a and a["label"]) or sec["label"],
            city=city, street=street, zip=ZIP.get(city, "101"),
            rep_first=rep[0], rep_last=rep[1], rep_title=rep[2], rep_gender=rep[3],
            nif=(a and a["nif"]) or str(rng.randint(1000000000, 5999999999)),
            stat=(a and a["stat"]) or f"{rng.randint(10000, 69999)} 11 {reg_year} 0 {rng.randint(0, 99999):05d}",
            rcs=(a and a["rcs"]) or f"{reg_year} B {rng.randint(1, 999):05d}",
            email=f"contact@{slug(name)}.mg",
            phone=f"+261 {rng.choice(['32', '33', '34', '38'])} {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(10, 99)}",
            start=start, stop=stop, interval=interval, freq_label=FREQ_LABEL[interval],
            payer=wchoice(rng, PAYER), salesperson=sp,
        ))
    return clients


# ---------------------------------------------------------------- commandes
def _line(code, desc, price, tax, qty=1):
    return dict(code=code, desc=desc, price=price, tax=tax, qty=qty)


def _weekday(d):
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def build_order(c, d, rng):
    sec = SECTORS[c["sector"]]
    imp = sec["flux"] == "import"
    yf, fx, frt = _yf(INFL, d), _yf(FX, d), _yf(FRT, d)
    air = rng.random() < sec["air"]
    carrier = "AIRCARGO" if air else rng.choice(CARRIERS)
    ctype = "AIR" if air else wchoice(rng, [("20DV", .38), ("40DV", .17), ("40HC", .35), ("LCL", .10)])
    size = {"20DV": .6, "40DV": 1.0, "40HC": 1.1, "LCL": .25, "AIR": .2}[ctype]
    cif = max(sec["usd"][0] * .2, rng.uniform(*sec["usd"]) * size * rng.uniform(.6, 1.2) * (yf ** .5))
    cif = int(round(cif, -2))
    weight = int({"20DV": rng.uniform(8e3, 24e3), "40DV": rng.uniform(12e3, 27e3), "40HC": rng.uniform(12e3, 27e3),
                  "LCL": rng.uniform(1e3, 8e3), "AIR": rng.uniform(100, 2500)}[ctype])
    marchandise, hs = rng.choice(sec["items"])
    regime = wchoice(rng, [("IM4", .85), ("IM7", .10), ("IM5", .05)]) if imp else "EX1"
    canal = wchoice(rng, [("vert", .55), ("jaune", .25), ("rouge", .20)] if imp else [("vert", .70), ("jaune", .25), ("rouge", .05)])
    pref = CARRIER_PREFIX.get(carrier, "")
    o = dict(client=c["id"], flux=sec["flux"], ot_date=d, regime=regime, canal=canal, mode="aerien" if air else "maritime",
             container_type=ctype, carrier=("Fret aérien" if air else carrier), marchandise=marchandise, hs=hs, cif=cif, weight=weight,
             supplier_carrier=carrier,
             container_no="" if air or ctype == "LCL" else f"{pref} {rng.randint(100000, 999999)}-{rng.randint(0, 9)}",
             vessel="" if air else f"{carrier} {rng.choice(VESSEL_NAMES)}", voyage="" if air else f"{rng.randint(100, 999)}{rng.choice('ABEW')}",
             bl_no=(f"LTA 176-{rng.randint(1000000, 9999999)}" if air else f"{pref[:3]}{rng.randint(10000000, 99999999)}"),
             bsc_no=f"BSC{d.year}{rng.randint(100000, 999999)}", dau_no="")
    dest_city = c["city"]
    o["dest_city"] = dest_city
    # --- jalons
    bsc = d + dt.timedelta(days=rng.randint(0, 1))
    if imp:
        arrival = d + dt.timedelta(days=rng.randint(1, 5) if air else rng.randint(4, 24))
        dau = arrival + dt.timedelta(days=rng.randint(1, 4))
        o["port_origin"] = rng.choice(AIR_ORIGINS if air else IMPORT_ORIGINS)
        o["port_dest"] = "Ivato (TNR)" if air else "Toamasina"
    else:
        arrival = bsc + dt.timedelta(days=rng.randint(4, 12))       # empotage / préparation
        dau = arrival + dt.timedelta(days=rng.randint(1, 2))
        o["port_origin"] = "Ivato (TNR)" if air else "Toamasina"
        o["port_dest"] = rng.choice(AIR_DEST if air else EXPORT_DEST)
    rel = dau + dt.timedelta(days=rng.randint(*{"vert": (0, 1), "jaune": (2, 4), "rouge": (4, 9)}[canal]) if imp else rng.randint(*{"vert": (0, 1), "jaune": (1, 3), "rouge": (2, 5)}[canal]))
    if imp:
        far = DIST.get(dest_city, 2)
        final = rel + dt.timedelta(days=rng.randint(0, 1) if (air and dest_city == "Antananarivo") else rng.randint(1, 3) + int(far * 1.5))
    else:
        final = rel + dt.timedelta(days=rng.randint(2, 9))
    o.update(bsc=bsc, arrival=arrival, dau=dau, release=rel, final=final)
    o["dau_no"] = f"DAU-{dau.year}-{regime}-{rng.randint(1, 99999):06d}"
    # --- lignes
    L = []
    val = cif * fx
    dist = DIST.get(dest_city, 2)
    if imp:
        L.append(_line("TRANSIT", f"Honoraires de transit & dédouanement {regime} - {marchandise}", _r(min(max(val * rng.uniform(.006, .011), 250e3 * yf), 6e6 * yf)), "tva"))
        L.append(_line("BSC", f"Frais BSC GasyNet n° {o['bsc_no']}", _r(rng.uniform(110e3, 170e3) * yf), "tva"))
        if air:
            L.append(_line("HANDLING", f"Handling aéroport Ivato - {o['bl_no']}", _r(max(120e3, weight * rng.uniform(250, 420)) * yf), "tva"))
        else:
            L.append(_line("MANUT", f"Manutention, acconage & THC - {ctype} {o['container_no']}".strip(), _r({"20DV": 380e3, "40DV": 560e3, "40HC": 580e3, "LCL": 250e3}[ctype] * yf * rng.uniform(.95, 1.1)), "tva"))
        base_tr = {"20DV": 1.6e6, "40DV": 2.3e6, "40HC": 2.4e6, "LCL": .9e6, "AIR": .35e6}[ctype]
        L.append(_line("TRANSPORT", f"Transport routier {'Toamasina' if not air else 'Ivato'} -> {dest_city} (RN2)", _r(base_tr * dist * yf * rng.uniform(.9, 1.15)), "tva"))
        if canal == "rouge":
            L.append(_line("SCANNER", "Frais scanner / visite physique douane", _r(rng.uniform(180e3, 400e3) * yf), "tva"))
        elif canal == "jaune" and rng.random() < .5:
            L.append(_line("SCANNER", "Frais d'expertise documentaire douane", _r(rng.uniform(80e3, 160e3) * yf), "tva"))
        if regime == "IM7" or rng.random() < .12:
            days = rng.randint(4, 18)
            L.append(_line("MAGASIN", f"Magasinage sous douane (MAD) - {days} jours", _r(38e3 * yf), "tva", days))
        L.append(_line("DEBOURS", f"Débours droits & taxes (DD + TVA) - DAU {o['dau_no']}", _r(val * sec["duty"] * rng.uniform(.85, 1.1)), "exo"))
        if rng.random() < .35:
            usd = weight * 4.5 if air else {"20DV": 1800, "40DV": 3200, "40HC": 3400, "LCL": 900}[ctype]
            L.append(_line("FRET", f"Fret international {o['port_origin']} -> {o['port_dest']}", _r(usd * fx * frt * rng.uniform(.85, 1.2)), "exo"))
    else:
        L.append(_line("X_TRANSIT", f"Honoraires de transit export EX1 - {marchandise}", _r(min(max(val * rng.uniform(.004, .008), 300e3 * yf), 3e6 * yf)), "exo"))
        L.append(_line("BSC", f"Frais BSC GasyNet n° {o['bsc_no']}", _r(rng.uniform(110e3, 170e3) * yf), "exo"))
        L.append(_line("X_BOOKING", f"Booking {o['carrier']} & positionnement - {ctype}", _r(rng.uniform(250e3, 450e3) * yf), "exo"))
        L.append(_line("X_CERTIF", "Certificats phytosanitaire / origine EUR.1", _r(rng.uniform(150e3, 350e3) * yf), "exo"))
        if air:
            L.append(_line("HANDLING", "Handling & fret aérien export Ivato", _r(max(150e3, weight * rng.uniform(250, 420)) * yf), "exo"))
        else:
            L.append(_line("X_EMPOTAGE", f"Empotage, plombage & contrôle - {ctype}", _r(rng.uniform(220e3, 480e3) * yf), "exo"))
            L.append(_line("MANUT", f"Manutention & THC export Toamasina - {ctype}", _r({"20DV": 380e3, "40DV": 560e3, "40HC": 580e3, "LCL": 250e3}[ctype] * yf), "exo"))
        L.append(_line("X_TRANSPORT", f"Transport {dest_city} -> {'Ivato' if air else 'Port de Toamasina'}", _r(1.6e6 * dist * yf * rng.uniform(.9, 1.15)), "exo"))
        if canal == "rouge":
            L.append(_line("SCANNER", "Frais scanner / visite physique douane", _r(rng.uniform(180e3, 400e3) * yf), "exo"))
        if rng.random() < .5:
            usd = weight * 4.0 if air else {"20DV": 2500, "40DV": 4500, "40HC": 4700, "LCL": 1200}[ctype]
            L.append(_line("FRET", f"Fret international {o['port_origin']} -> {o['port_dest']}", _r(usd * fx * frt * rng.uniform(.85, 1.2)), "exo"))
    o["lines"] = L
    o["total_ht"] = sum(l["price"] * l["qty"] for l in L)
    return o


def stage_at(o, ref):
    if o["status"] == "cancel":
        return "cancel"
    if o["flux"] == "import":
        if o["final"] <= ref: return "livre"
        if o["release"] <= ref: return "transport"
        if o["dau"] <= ref: return "controle"
        if o["arrival"] <= ref: return "port"
        if o["bsc"] <= ref: return "bsc"
        return "ot"
    if o["final"] <= ref: return "embarque"
    if o["release"] <= ref: return "mainlevee"
    if o["dau"] <= ref: return "dau"
    if o["arrival"] <= ref: return "empotage"
    if o["bsc"] <= ref: return "booking"
    return "ot"


def generate_orders(clients, rng):
    orders = []
    covid = (dt.date(2020, 3, 20), dt.date(2020, 6, 30))
    for c in clients:
        sec = SECTORS[c["sector"]]
        d = c["start"]
        while d <= END:
            if c["stop"] and d > c["stop"]:
                break
            skip = (covid[0] <= d <= covid[1] and rng.random() < .5) or \
                   (sec["season"] and d.month not in sec["season"] and rng.random() < .7)
            if not skip:
                orders.append(build_order(c, _weekday(d), rng))
            d += dt.timedelta(days=max(1, int(c["interval"] * rng.uniform(.75, 1.25) / SCALE)))
    orders = [o for o in orders if o["ot_date"] <= END]
    orders.sort(key=lambda o: (o["ot_date"], o["client"]))
    cl = {c["id"]: c for c in clients}
    cnt = defaultdict(int)
    for o in orders:
        key = (o["ot_date"].year, o["flux"])
        cnt[key] += 1
        o["ot_ref"] = f"OT-{o['ot_date'].year}-{'IMP' if o['flux'] == 'import' else 'EXP'}-{cnt[key]:04d}"
        o["status"] = "cancel" if rng.random() < .02 else ("done" if o["final"] <= END else "progress")
        o["stage"] = stage_at(o, END)
        o["invoice_date"] = o["pay_date"] = o["due_date"] = None
        if o["status"] == "done":
            inv = o["final"] + dt.timedelta(days=rng.randint(1, 5))
            if inv <= END:
                o["invoice_date"] = inv
                o["due_date"] = inv + dt.timedelta(days=30)
                p = cl[o["client"]]["payer"]
                delay = {"good": rng.randint(5, 35), "slow": rng.randint(40, 90), "bad": rng.randint(90, 200)}[p]
                if p == "bad" and rng.random() < .25:
                    delay = 10 ** 5   # ne paie jamais
                pay = inv + dt.timedelta(days=delay)
                o["pay_date"] = pay if pay <= END else None
            else:
                o["status"] = "progress"
    return orders


def generate_bills(orders, rng):
    """Factures fournisseurs mensuelles agrégées (coûts réels du transitaire)."""
    agg = defaultdict(float)
    for o in orders:
        if not o["invoice_date"]:
            continue
        m = (o["final"].year, o["final"].month)
        for l in o["lines"]:
            if l["code"] in COSTS:
                sup, ratio = COSTS[l["code"]]
                if sup == "CARRIER":
                    sup = o["supplier_carrier"]
                agg[(m, sup, l["tax"] == "tva")] += l["price"] * l["qty"] * ratio * rng.uniform(.97, 1.03)
    bills = []
    for (m, sup, vat), amt in sorted(agg.items()):
        nxt = dt.date(m[0] + (m[1] == 12), m[1] % 12 + 1, 1)
        d = nxt - dt.timedelta(days=1)
        if d > END:
            continue
        pay = d + dt.timedelta(days=rng.randint(20, 45))
        bills.append(dict(supplier=sup, date=d, amount=_r(amt), vat=vat, pay_date=pay if pay <= END else None, ref=f"{slug(sup).upper()}-{m[0]}{m[1]:02d}"))
    bills.sort(key=lambda b: b["date"])
    return bills


def generate():
    rng = random.Random(SEED)
    clients = generate_clients(rng)
    orders = generate_orders(clients, rng)
    bills = generate_bills(orders, rng)
    return dict(clients=clients, orders=orders, bills=bills)


def stats(ds):
    o = ds["orders"]
    inv = [x for x in o if x["invoice_date"]]
    print(f"clients={len(ds['clients'])} (import={sum(c['flux']=='import' for c in ds['clients'])}, export={sum(c['flux']=='export' for c in ds['clients'])})")
    print(f"commandes={len(o)} facturées={len(inv)} payées={sum(1 for x in inv if x['pay_date'])} annulées={sum(x['status']=='cancel' for x in o)} en cours={sum(x['status']=='progress' for x in o)}")
    print(f"factures fournisseurs={len(ds['bills'])}")
    for y in range(START.year, END.year + 1):
        ys = [x for x in inv if x["invoice_date"].year == y]
        print(f"  {y}: {len(ys):5d} factures | CA HT = {sum(x['total_ht'] for x in ys)/1e9:7.2f} Md Ar")
    act = {x["client"] for x in o}
    print(f"clients ayant commandé: {len(act)}/{len(ds['clients'])}")


if __name__ == "__main__":
    ds = generate()
    stats(ds)
    os.makedirs("export", exist_ok=True)
    with open("export/clients.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Société", "Secteur", "Flux", "Ville", "Adresse", "Représentant", "Fonction", "NIF", "STAT", "RCS", "Email", "Téléphone", "Fréquence", "Début", "Fin"])
        for c in ds["clients"]:
            w.writerow([c["id"], c["name"], c["sector_label"], c["flux"], c["city"], c["street"], f"{c['rep_first']} {c['rep_last']}", c["rep_title"], c["nif"], c["stat"], c["rcs"], c["email"], c["phone"], c["freq_label"], c["start"], c["stop"] or ""])
    with open("export/commandes.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Réf OT", "Client", "Flux", "Date OT", "Régime", "Canal", "Marchandise", "Conteneur", "CIF USD", "Étape", "Statut", "Date facture", "Total HT Ar", "Date paiement"])
        for o in ds["orders"]:
            w.writerow([o["ot_ref"], o["client"], o["flux"], o["ot_date"], o["regime"], o["canal"], o["marchandise"], o["container_type"], o["cif"], o["stage"], o["status"], o["invoice_date"] or "", o["total_ht"], o["pay_date"] or ""])
    print("CSV écrits dans ./export")
