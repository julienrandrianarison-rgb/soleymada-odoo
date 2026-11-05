from odoo import fields, models

STAGES = [
    ('ot', "Ordre de transit reçu"),
    ('bsc', "BSC validé (GasyNet)"),
    ('booking', "Booking & positionnement"),
    ('port', "Prise en charge port / aéroport"),
    ('empotage', "Empotage & plombage"),
    ('dau', "DAU enregistrée"),
    ('controle', "Contrôle douanier"),
    ('mainlevee', "Mainlevée"),
    ('transport', "Transport en cours (RN2)"),
    ('livre', "Livré"),
    ('embarque', "Embarqué / exporté"),
    ('cancel', "Annulé"),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    soley_flux = fields.Selection([('import', "Import"), ('export', "Export")], string="Flux", index=True)
    soley_stage = fields.Selection(STAGES, string="Étape du dossier", index=True)
    soley_regime = fields.Selection([('IM4', "IM4 - Mise à la consommation"), ('IM5', "IM5 - Admission temporaire"),
                                     ('IM7', "IM7 - Entrepôt sous douane"), ('EX1', "EX1 - Exportation définitive")], string="Régime douanier")
    soley_canal = fields.Selection([('vert', "Vert"), ('jaune', "Jaune"), ('rouge', "Rouge")], string="Canal douane")
    soley_mode = fields.Selection([('maritime', "Maritime"), ('aerien', "Aérien")], string="Mode")
    soley_marchandise = fields.Char(string="Marchandise")
    soley_hs_code = fields.Char(string="Code SH")
    soley_container_type = fields.Char(string="Type conteneur")
    soley_container_no = fields.Char(string="N° conteneur")
    soley_carrier = fields.Char(string="Armateur / transporteur")
    soley_vessel = fields.Char(string="Navire")
    soley_voyage = fields.Char(string="Voyage")
    soley_bl_no = fields.Char(string="N° B/L - LTA")
    soley_bsc_no = fields.Char(string="N° BSC")
    soley_dau_no = fields.Char(string="N° DAU")
    soley_port_origin = fields.Char(string="Port / aéroport d'origine")
    soley_port_dest = fields.Char(string="Port / aéroport de destination")
    soley_dest_city = fields.Char(string="Ville de livraison / collecte")
    soley_cif_usd = fields.Float(string="Valeur CIF (USD)")
    soley_weight_kg = fields.Float(string="Poids brut (kg)")
    soley_date_bsc = fields.Date(string="Date BSC")
    soley_date_arrival = fields.Date(string="Arrivée navire / empotage")
    soley_date_dau = fields.Date(string="Date DAU")
    soley_date_release = fields.Date(string="Date mainlevée")
    soley_date_final = fields.Date(string="Livraison / embarquement")
