# -*- coding: utf-8 -*-
"""
Chargement de la base SOLEY MADA dans Odoo (société, utilisateurs, 500 clients, produits,
commandes -> factures -> paiements 2020-2025, factures fournisseurs).

Exécution (depuis la racine du projet) :
    docker compose run --rm -T odoo odoo shell -d soleymada --no-http < scripts/seed_odoo.py

- Reprenable : relancer le script saute les commandes déjà créées (clé = n° OT dans client_order_ref).
- Paramètres via .env : SCALE (0.05 = test rapide, 1.0 = volume complet), START_DATE, END_DATE, SEED...
"""
import os, sys, time, datetime as dt
from collections import defaultdict

sys.path.insert(0, os.environ.get("SCRIPTS_DIR", "/mnt/scripts"))
import soleymada_data as D   # noqa: E402

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Soley@Admin#2026")
COMMIT_EVERY = 100

env = env(context=dict(env.context, lang="fr_FR", tz="Indian/Antananarivo", tracking_disable=True, mail_notrack=True,
                       mail_create_nolog=True, mail_auto_subscribe_no_notify=True, no_reset_password=True,
                       disable_cancel_warning=True))


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def has_field(model, name):
    return name in env[model]._fields


# ------------------------------------------------------------------ société
def setup_company():
    mg, mga = env.ref("base.mg"), env.ref("base.MGA")
    mga.active = True
    try:
        mga.rounding = 1.0
    except Exception as e:   # noqa
        log("rounding MGA ignoré:", e)
    co = env.company
    co.write({
        "name": "SOLEY MADA TRANSPORT & LOGISTICS SARL", "street": "Zone Océan, Boulevard Kamoro", "city": "Antananarivo",
        "zip": "101", "country_id": mg.id, "email": "contact@soleymada-logistics.mg", "phone": "+261 20 22 000 00",
        "website": "https://soleymada-logistics.mg", "vat": "5001239874", "company_registry": "2019 B 00987",
    })
    try:
        co.currency_id = mga.id
    except Exception as e:   # noqa
        log("!! devise société non modifiée:", e)
    env["product.pricelist"].with_context(active_test=False).search([]).write({"currency_id": mga.id})
    env.cr.commit()
    log("société configurée, devise:", env.company.currency_id.name)


# ------------------------------------------------------------------ utilisateurs
USERS = [  # login, nom, mot de passe, rôle, groupes
    ("dg@soleymada-logistics.mg", "Hery RAKOTOMALALA (Directeur Général)", "Soley@DG#2026", ["sale_manager", "account_manager", "purchase_manager", "fleet_manager"]),
    ("ops@soleymada-logistics.mg", "Mialy RANDRIANARISOA (Directrice Opérations)", "Soley@Ops#2026", ["sale_manager", "purchase_user", "fleet_manager"]),
    ("transit.import@soleymada-logistics.mg", "Tiana RAZAFINDRAKOTO (Resp. Transit Import)", "Soley@Import#2026", ["sale_manager"]),
    ("transit.export@soleymada-logistics.mg", "Faly RASOLOFO (Resp. Transit Export)", "Soley@Export#2026", ["sale_manager"]),
    ("agent.toamasina@soleymada-logistics.mg", "Njaka RABEMANANJARA (Agent Port Toamasina)", "Soley@Toamasina#2026", ["sale_salesman"]),
    ("agent.ivato@soleymada-logistics.mg", "Volatiana RAKOTONIRINA (Agent Aéroport Ivato)", "Soley@Ivato#2026", ["sale_salesman"]),
    ("declarant@soleymada-logistics.mg", "Haja ANDRIANJAFY (Déclarant en douane)", "Soley@Declarant#2026", ["sale_salesman"]),
    ("commercial.chef@soleymada-logistics.mg", "Lova RAVELOMANANA (Resp. Commercial)", "Soley@Chef#2026", ["sale_manager"]),
    ("commercial1@soleymada-logistics.mg", "Fanja RATSIMBAZAFY (Commerciale Tana A)", "Soley@Com1#2026", ["sale_salesman_all"]),
    ("commercial2@soleymada-logistics.mg", "Toky RAJAONARISON (Commercial Tana B)", "Soley@Com2#2026", ["sale_salesman_all"]),
    ("commercial3@soleymada-logistics.mg", "Hasina RAMANANTSOA (Commerciale Provinces)", "Soley@Com3#2026", ["sale_salesman_all"]),
    ("comptable@soleymada-logistics.mg", "Voahirana RASOANAIVO (Comptable)", "Soley@Compta#2026", ["account_manager", "purchase_user"]),
    ("facturation@soleymada-logistics.mg", "Miora RAHARISON (Facturation)", "Soley@Factu#2026", ["account_invoice", "sale_salesman"]),
    ("transport@soleymada-logistics.mg", "Dina RASOLONJATOVO (Resp. Transport / Flotte)", "Soley@Flotte#2026", ["fleet_manager", "purchase_user"]),
    ("assistant@soleymada-logistics.mg", "Tahina RAZANAMAHEFA (Assistante administrative)", "Soley@Assist#2026", ["sale_salesman"]),
]
GROUPS = {
    "sale_manager": "sales_team.group_sale_manager", "sale_salesman": "sales_team.group_sale_salesman",
    "sale_salesman_all": "sales_team.group_sale_salesman_all_leads", "account_manager": "account.group_account_manager",
    "account_invoice": "account.group_account_invoice", "purchase_user": "purchase.group_purchase_user",
    "purchase_manager": "purchase.group_purchase_manager", "fleet_manager": "fleet.fleet_group_manager",
}


def setup_users():
    GF = "group_ids" if has_field("res.users", "group_ids") else "groups_id"
    Users = env["res.users"].with_context(no_reset_password=True)
    admin = env.ref("base.user_admin")
    admin.write({"name": "Administrateur Soley Mada", "email": "admin@soleymada-logistics.mg", "password": ADMIN_PASSWORD,
                 "lang": "fr_FR", "tz": "Indian/Antananarivo"})
    base_group = env.ref("base.group_user").id
    by_login = {}
    for login, name, pwd, roles in USERS:
        u = Users.search([("login", "=", login)], limit=1)
        if not u:
            gids = {base_group}
            for r in roles:
                g = env.ref(GROUPS[r], raise_if_not_found=False)
                if g:
                    gids.add(g.id)
                else:
                    log("groupe introuvable:", GROUPS[r])
            u = Users.create({"name": name, "login": login, "email": login, "password": pwd, "lang": "fr_FR",
                              "tz": "Indian/Antananarivo", GF: [(6, 0, list(gids))]})
        by_login[login] = u
    env.cr.commit()
    log(f"{len(by_login)} utilisateurs + admin prêts")
    return [by_login["commercial1@soleymada-logistics.mg"], by_login["commercial2@soleymada-logistics.mg"],
            by_login["commercial3@soleymada-logistics.mg"]]


# ------------------------------------------------------------------ taxes / produits / fournisseurs / flotte
def get_tax(name, amount, use):
    T = env["account.tax"]
    t = T.search([("name", "=", name), ("type_tax_use", "=", use)], limit=1)
    return t or T.create({"name": name, "amount": amount, "amount_type": "percent", "type_tax_use": use})


def setup_catalog():
    taxes = {"tva": get_tax("TVA 20%", 20.0, "sale"), "exo": get_tax("Exonéré (export / débours) 0%", 0.0, "sale")}
    purchase_tax = get_tax("TVA 20% (achats)", 20.0, "purchase")
    P = env["product.product"]
    prods = {}
    for code, name in D.PRODUCTS.items():
        p = P.search([("default_code", "=", code)], limit=1)
        if not p:
            vals = {"name": name, "default_code": code, "type": "service", "list_price": 0.0, "sale_ok": True, "purchase_ok": False}
            if has_field("product.template", "invoice_policy"):
                vals["invoice_policy"] = "order"
            p = P.create(vals)
        prods[code] = p
    Partner = env["res.partner"]
    sup = {}
    for key, name in D.SUPPLIERS.items():
        s = Partner.search([("name", "=", name)], limit=1) or Partner.create(
            {"name": name, "is_company": True, "country_id": env.ref("base.mg").id, "supplier_rank": 1} if has_field("res.partner", "supplier_rank")
            else {"name": name, "is_company": True, "country_id": env.ref("base.mg").id})
        sup[key] = s
    # flotte (facultatif)
    try:
        if env["fleet.vehicle"].search_count([]) == 0:
            Brand, Model, Veh = env["fleet.vehicle.model.brand"], env["fleet.vehicle.model"], env["fleet.vehicle"]
            models = []
            for b, m in [("Isuzu", "FVR 6x2"), ("Hino", "500 FM"), ("Renault Trucks", "T High"), ("Mercedes-Benz", "Actros 2645")]:
                br = Brand.search([("name", "=", b)], limit=1) or Brand.create({"name": b})
                models.append(Model.create({"name": m, "brand_id": br.id}))
            for i in range(1, 13):
                Veh.create({"model_id": models[i % 4].id, "license_plate": f"{1000 + i * 37} TBA", "driver_id": False})
            log("12 camions créés")
    except Exception as e:   # noqa
        env.cr.rollback()
        log("flotte ignorée:", e)
    env.cr.commit()
    return taxes, purchase_tax, prods, sup


# ------------------------------------------------------------------ clients
def setup_partners(clients, sellers):
    P = env["res.partner"]
    Tag = env["res.partner.category"]
    tags = {}
    for t in ["Import", "Export"] + list(D.FREQ_LABEL.values()):
        tags[t] = Tag.search([("name", "=", t)], limit=1) or Tag.create({"name": t})
    mg = env.ref("base.mg")
    existing = {p.ref: p for p in P.search([("ref", "like", "CUST-")])}
    todo = [c for c in clients if c["id"] not in existing]
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        vals = []
        for c in chunk:
            v = {"name": c["name"], "is_company": True, "company_type": "company", "ref": c["id"], "street": c["street"],
                 "city": c["city"], "zip": c["zip"], "country_id": mg.id, "email": c["email"], "phone": c["phone"],
                 "vat": c["nif"], "company_registry": c["rcs"], "user_id": sellers[c["salesperson"]].id, "lang": "fr_FR",
                 "comment": f"STAT : {c['stat']}\nSecteur : {c['sector_label']}\nFlux : {c['flux'].upper()}\nRythme de commande : {c['freq_label']}",
                 "category_id": [(6, 0, [tags["Import" if c["flux"] == "import" else "Export"].id, tags[c["freq_label"]].id])]}
            if has_field("res.partner", "customer_rank"):
                v["customer_rank"] = 1
            vals.append(v)
        recs = P.create(vals)
        kids = []
        for c, r in zip(chunk, recs):
            existing[c["id"]] = r
            kids.append({"parent_id": r.id, "type": "contact", "name": f"{c['rep_first']} {c['rep_last'].title()}",
                         "function": c["rep_title"], "email": f"{D.slug(c['rep_first'])}.{D.slug(c['rep_last'])}@{c['email'].split('@')[1]}",
                         "phone": c["phone"]})
        P.create(kids)
        env.cr.commit()
        log(f"clients créés: {min(i + 100, len(todo))}/{len(todo)}")
    return existing


# ------------------------------------------------------------------ commandes
def run_orders(ds, partners, taxes, prods, bank, sellers):
    SO = env["sale.order"]
    tax_field = "tax_ids" if has_field("sale.order.line", "tax_ids") else "tax_id"
    done = set(SO.search([("client_order_ref", "like", "OT-")]).mapped("client_order_ref"))
    cl = {c["id"]: c for c in ds["clients"]}
    todo = [o for o in ds["orders"] if o["ot_ref"] not in done]
    log(f"commandes à créer: {len(todo)} (déjà présentes: {len(done)})")
    t0, n_err = time.time(), 0
    for n, o in enumerate(todo, 1):
        c = cl[o["client"]]
        try:
            with env.cr.savepoint():
                so = SO.create({
                    "partner_id": partners[o["client"]].id, "date_order": f"{o['ot_date']} 05:30:00", "client_order_ref": o["ot_ref"],
                    "user_id": sellers[c["salesperson"]].id, "commitment_date": f"{o['final']} 12:00:00",
                    "order_line": [(0, 0, {"product_id": prods[l["code"]].id, "name": l["desc"], "product_uom_qty": l["qty"],
                                           "price_unit": l["price"], tax_field: [(6, 0, [taxes[l["tax"]].id])]}) for l in o["lines"]],
                    "soley_flux": o["flux"], "soley_stage": o["stage"], "soley_regime": o["regime"], "soley_canal": o["canal"],
                    "soley_mode": o["mode"], "soley_marchandise": o["marchandise"], "soley_hs_code": o["hs"],
                    "soley_container_type": o["container_type"], "soley_container_no": o["container_no"], "soley_carrier": o["carrier"],
                    "soley_vessel": o["vessel"], "soley_voyage": o["voyage"], "soley_bl_no": o["bl_no"], "soley_bsc_no": o["bsc_no"],
                    "soley_dau_no": o["dau_no"], "soley_port_origin": o["port_origin"], "soley_port_dest": o["port_dest"],
                    "soley_dest_city": o["dest_city"], "soley_cif_usd": o["cif"], "soley_weight_kg": o["weight"],
                    "soley_date_bsc": o["bsc"], "soley_date_arrival": o["arrival"], "soley_date_dau": o["dau"],
                    "soley_date_release": o["release"], "soley_date_final": o["final"],
                })
                if o["status"] == "cancel":
                    so.action_cancel()
                    continue
                so.action_confirm()
                so.write({"date_order": f"{o['ot_date']} 05:30:00"})    # action_confirm remet la date du jour
                if o["invoice_date"]:
                    inv = so._create_invoices()
                    inv.write({"invoice_date": o["invoice_date"], "invoice_date_due": o["due_date"]})
                    inv.action_post()
                    if o["pay_date"]:
                        env["account.payment.register"].with_context(active_model="account.move", active_ids=inv.ids).create(
                            {"payment_date": o["pay_date"], "journal_id": bank.id})._create_payments()
        except Exception as e:   # noqa
            n_err += 1
            env.invalidate_all()
            log(f"!! {o['ot_ref']} ignorée: {str(e)[:150]}")
            if n_err > 50:
                raise
        if n % COMMIT_EVERY == 0:
            env.cr.commit()
            env.invalidate_all()
            el = time.time() - t0
            log(f"{n}/{len(todo)} commandes | {el/60:.1f} min | reste ~{(len(todo)-n)*el/n/60:.0f} min | erreurs: {n_err}")
    env.cr.commit()
    log(f"commandes terminées, erreurs: {n_err}")


# ------------------------------------------------------------------ factures fournisseurs
def run_bills(ds, sup, purchase_tax, bank):
    Move = env["account.move"]
    exp = env["account.account"].search([("account_type", "in", ("expense", "expense_direct_cost"))], limit=1)
    if not exp:
        log("!! aucun compte de charge trouvé: factures fournisseurs ignorées")
        return
    done = set(Move.search([("move_type", "=", "in_invoice"), ("ref", "like", "SM-")]).mapped("ref"))
    n = 0
    for b in ds["bills"]:
        ref = "SM-" + b["ref"]
        if ref in done:
            continue
        try:
            with env.cr.savepoint():
                line = {"name": f"Prestations {D.SUPPLIERS[b['supplier']]} - {b['date']:%m/%Y}", "quantity": 1, "price_unit": b["amount"],
                        "account_id": exp.id, "tax_ids": [(6, 0, [purchase_tax.id] if b["vat"] else [])]}
                bill = Move.create({"move_type": "in_invoice", "partner_id": sup[b["supplier"]].id, "invoice_date": b["date"], "ref": ref,
                                    "invoice_date_due": b["date"] + dt.timedelta(days=30), "invoice_line_ids": [(0, 0, line)]})
                bill.action_post()
                if b["pay_date"]:
                    env["account.payment.register"].with_context(active_model="account.move", active_ids=bill.ids).create(
                        {"payment_date": b["pay_date"], "journal_id": bank.id})._create_payments()
        except Exception as e:   # noqa
            env.invalidate_all()
            log(f"!! facture fournisseur {ref}: {str(e)[:120]}")
        n += 1
        if n % 100 == 0:
            env.cr.commit()
    env.cr.commit()
    log(f"{n} factures fournisseurs traitées")


def summary():
    SO, Move = env["sale.order"], env["account.move"]
    log("=== RÉSUMÉ ===")
    log("clients:", env["res.partner"].search_count([("ref", "like", "CUST-")]))
    log("commandes:", SO.search_count([("client_order_ref", "like", "OT-")]))
    log("factures clients postées:", Move.search_count([("move_type", "=", "out_invoice"), ("state", "=", "posted")]))
    log("factures fournisseurs postées:", Move.search_count([("move_type", "=", "in_invoice"), ("state", "=", "posted")]))


# ------------------------------------------------------------------ main
log(f"Génération du jeu de données (SCALE={D.SCALE}, {D.START} -> {D.END})")
ds = D.generate()
D.stats(ds)
setup_company()
sellers = setup_users()
taxes, purchase_tax, prods, sup = setup_catalog()
bank = env["account.journal"].search([("type", "=", "bank")], limit=1)
if not bank:
    raise SystemExit("Aucun journal de banque : le plan comptable n'est pas chargé ?")
partners = setup_partners(ds["clients"], sellers)
run_orders(ds, partners, taxes, prods, bank, sellers)
run_bills(ds, sup, purchase_tax, bank)
summary()
log("TERMINÉ")
