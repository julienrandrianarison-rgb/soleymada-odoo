# SOLEY MADA TRANSPORT & LOGISTICS SARL — base Odoo fictive (2020-2025)

Entreprise fictive de transit / transport / dédouanement (Madagascar). Base Odoo locale, déployable en ligne,
avec 500 clients, ~15 800 dossiers de transit (OT) facturés et encaissés sur 6 ans, utilisateurs et sauvegarde.

## Démarrage (local)
Prérequis : Docker + Docker Compose.

    cd soleymada-odoo
    # 1) test rapide (≈15 min) : mettre SCALE=0.05 dans .env ; version complète : SCALE=1.0
    ./scripts/init.sh                     # complet : plusieurs heures -> nohup ./scripts/init.sh > init.log 2>&1 &
    # 2) ouvrir http://localhost:8069

Le chargement est **reprenable** : si il s'interrompt, relancer uniquement la commande de l'étape 2 de `init.sh`.

## Comptes
| Rôle | Login | Mot de passe |
|---|---|---|
| **Administrateur Odoo** | `admin` | `Soley@Admin#2026` |
| **Mot de passe maître (menu Backup/Restore)** | — | `SoleyMaster#2026` |
| Directeur Général | dg@soleymada-logistics.mg | Soley@DG#2026 |
| Directrice Opérations | ops@soleymada-logistics.mg | Soley@Ops#2026 |
| Resp. Transit Import | transit.import@soleymada-logistics.mg | Soley@Import#2026 |
| Resp. Transit Export | transit.export@soleymada-logistics.mg | Soley@Export#2026 |
| Agent Port Toamasina | agent.toamasina@soleymada-logistics.mg | Soley@Toamasina#2026 |
| Agent Aéroport Ivato | agent.ivato@soleymada-logistics.mg | Soley@Ivato#2026 |
| Déclarant en douane | declarant@soleymada-logistics.mg | Soley@Declarant#2026 |
| Resp. Commercial | commercial.chef@soleymada-logistics.mg | Soley@Chef#2026 |
| Commerciale Tana A / Tana B / Provinces | commercial1 / commercial2 / commercial3 @soleymada-logistics.mg | Soley@Com1#2026 / Com2 / Com3 |
| Comptable | comptable@soleymada-logistics.mg | Soley@Compta#2026 |
| Facturation | facturation@soleymada-logistics.mg | Soley@Factu#2026 |
| Resp. Transport / Flotte | transport@soleymada-logistics.mg | Soley@Flotte#2026 |
| Assistante administrative | assistant@soleymada-logistics.mg | Soley@Assist#2026 |

Ces mots de passe sont des valeurs de démonstration : **les changer avant toute mise en ligne**.

## Contenu de la base
- 500 clients (CUST-001 à CUST-500), 300 import / 200 export, répartition Tana 60 %, Toamasina 15 %, Mahajanga 10 %, Nord 10 %, autres 5 %.
  Les clients cités dans votre document (MadaTech, SAVA Aromates, Vahona…) sont repris avec leurs NIF/STAT/RCS.
- Chaque client a un rythme de commande systématique (hebdo, bimensuel, mensuel, bimestriel, trimestriel), une date d'arrivée
  (les clients à numéro bas sont les plus anciens), et ~8 % arrêtent leur activité en cours de période.
- Cycle complet de chaque dossier : Ordre de transit → BSC → prise en charge port/aéroport (ou booking/empotage) → DAU →
  canal vert/jaune/rouge → mainlevée → transport RN2 / embarquement → facture → paiement.
  Onglet « Transit & Douane » sur chaque commande (régime IM4/IM5/IM7/EX1, conteneur, navire, B/L, BSC, DAU, dates…).
- Réalisme : inflation, taux USD/Ar, flambée du fret 2021-2022, creux COVID (mars-juin 2020), saisonnalité vanille/girofle,
  TVA 20 % sur les prestations import, 0 % sur export et débours, clients bons/mauvais payeurs, factures impayées en retard,
  dossiers en cours en fin de période, 2 % de commandes annulées.
- Factures fournisseurs mensuelles (armateurs, douane, MICTSL, GasyNet, transporteurs…) et paiements correspondants.
- 12 camions dans le module Flotte.
- `export/clients.csv` et `export/commandes.csv` : copie du jeu de données (vérification / import n8n).

## Sauvegarde (menu Backup)
- Interface : http://localhost:8069/web/database/manager → Backup (mot de passe maître ci-dessus) / Restore.
- Ligne de commande : `./scripts/backup.sh` → `backups/soleymada_AAAA-MM-JJ_HHMM.zip`.
- Pour distribuer une base « prête à l'emploi » : après `init.sh`, faire un Backup, puis sur n'importe quel serveur
  Odoo de **même version** (avec le dossier `addons/soley_logistics`) : Restore.

## Mise en ligne
1. VPS Linux + Docker, copier ce dossier, `./scripts/init.sh` ou Restore du .zip.
2. Reverse proxy HTTPS (Caddy/Nginx) vers le port 8069, puis `proxy_mode = True` dans `config/odoo.conf`.
3. Changer TOUS les mots de passe (`.env`, `odoo.conf`, utilisateurs). Pour fermer le menu Backup au public : `list_db = False`
   (la route /web/database/manager disparaît ; utiliser alors `backup.sh`) ou la restreindre par IP au niveau du proxy.
4. Odoo Online (SaaS) n'accepte pas les modules personnalisés ; utiliser un serveur auto-hébergé ou Odoo.sh.

## Notes d'adaptation par rapport à votre document
- Période : 01/01/2020 → 31/12/2025 comme demandé (modifiable : `START_DATE` / `END_DATE`). Votre document mentionne des
  commandes SO-2026-xxx ; les références sont ici au format Odoo standard (S00001…) et le n° OT (ex. OT-2024-IMP-0123) est dans « Référence client ».
- Le STAT/RCS de Soley Mada portait l'année 2025, incompatible avec 5 ans d'activité : remplacé par 2019.
- Les valeurs en Ar de votre document (ex. 18 500 000 Ar de panneaux solaires) sont des valeurs marchandises ; ici la facture
  = honoraires + frais + débours douaniers, et la valeur CIF est dans le dossier.
