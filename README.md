# 🛵 tkretail - Backend de l'application de gestion de livraison

Bienvenue dans le backend de **tk-retail**, une application intelligente de gestion de livraisons conçue pour les livreurs, magasins et clients. Cette API REST robuste permet la gestion des livraisons, des livreurs, manageurs, administrateur, des clients, des statistiques commerciales, ainsi que l’analyse des zones de performance.

---

## 📁 Structure du projet

```text
tkdata-backend/
├── app.py                # Entrée principale de l’application Flask
├── config.py             # Configuration générale
├── dockerfile            # Dockerfile pour la containerisation
├── env/                  # Environnement virtuel (à ne pas versionner)
├── extensions.py         # Extensions Flask (JWT, Mongo, etc.)
├── local.yml             # Configuration locale (ex: Mongo URI)
├── makefile              # Commandes make pour le build et le lancement
├── models/               # Modèles de données (MongoDB)
├── requirements.txt      # Dépendances Python
├── routes/               # Fichiers de routes Flask (API)
├── run.py                # Script de lancement principal
├── schemas/              # Schémas de validation (Marshmallow)
├── services/             # Logique métier (statistiques, traitement, etc.)
├── uploads/              # Dossier pour les fichiers téléversés
├── utils/                # Fonctions utilitaires
└── README.md             # Ce fichier
```
---

## 🚀 Lancement de l'application

### ▶️ Exécution en local

1. **Cloner le dépôt**
```bash
git clone https://github.com/tkdata-delivery/tkdata-backend.git
cd tkdata-backend

```
2. **Créer et activer l’environnement virtuel**
```bash
python3 -m venv env
source env/bin/activate
```
3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```
4. **Lancer le serveur**

```bash
python run.py
```
# ou
```bash
flask run
```

### 🐳 Exécution avec Docker

1.  **Construire et démarrer le conteneur**

```bash
make build
```
### 🔒 Authentification & Sécurité

    JWT (JSON Web Tokens) est utilisé pour sécuriser les routes et authentifier les utilisateurs.

    Les utilisateurs peuvent être de différents types : admin, manager, livreur.

📦 Fonctionnalités clés

    🔄 Gestion des livraisons : création, suivi, paiement, statut de livraison.

    👤 Gestion des clients : affectation aux livreurs, statistiques d’achats.

    📊 Statistiques dynamiques :

        Chiffre d’affaires total

        Nombre total de livraisons

        Nombre de clients uniques

        Nombre de produits différents

        Évolution par période (jour/semaine/mois/année)

        Répartition par zones (villes, quartiers)

    📍 Analyse géographique :

        Zones de vente maximale (top villes/quartiers)

        Répartition des revenus par secteur

 ### NB nous avous mis dans le repertoire dump une base de donnée test lorsque tu utilise docker : importer le manuelle
 ```
# Essayez d'importer manuellement
docker exec -it mongodb mongorestore --verbose /data/dump/

# Attendre quelques secondes puis vérifier
docker exec -it mongodb mongosh

# Dans le shell MongoDB
show dbs
use delivery_db2
show collections
db.magasin.countDocuments()
``````

🔧 Dépendances principales

    Flask

    Flask-JWT-Extended

    Flask-PyMongo

    Marshmallow

    PyYAML

    Docker (optionnel)

    Python 3.10+

🧪 Tests


🧠 Bonnes pratiques

    Toutes les routes sont regroupées dans le dossier routes/.

    La logique métier est séparée dans services/ pour assurer une architecture propre.

    schemas/ permet la validation et sérialisation des données.

    models/ contient les interfaces avec MongoDB.

    utils/ regroupe les fonctions utilitaires réutilisables.

👨‍💻 Auteurs

Développé par l’équipe Dev de Klivar
Un projet conçu avec passion pour une logistique plus fluide et intelligente.
🌐 Dépôt GitHub

🔗 [https://github.com/tkdata-delivery/tkdata-backend.git](https://github.com/tkdata-delivery/tkdata-backend.git)
