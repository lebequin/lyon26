# Lyon 2026 - Porte à Porte

Application Django de gestion du porte-à-porte pour les campagnes de mobilisation.

## Fonctionnalités

- **Carte interactive** : Visualisation des immeubles sur une carte Leaflet avec marqueurs colorés selon le statut
- **Gestion des visites** : Enregistrement des visites avec comptage des portes frappées/ouvertes
- **Statistiques par bureau de vote** : Suivi de la couverture et progression par bureau
- **Thème clair/sombre** : Interface adaptable avec basculement via le menu latéral
- **Interface responsive** : Fonctionne sur desktop et mobile

## Stack technique

- **Backend** : Django 5.0+
- **Frontend** : Tailwind CSS, HTMX, Leaflet.js
- **Base de données** : SQLite (dev) / PostgreSQL (prod)

## Installation

### Prérequis

- Python 3.11+
- pip

### Installation

```bash
# Cloner le repository
git clone <repository-url>
cd lyon26

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# Appliquer les migrations
python3 manage.py migrate

# Créer un superutilisateur
python3 manage.py createsuperuser

# Lancer le serveur
python3 manage.py runserver
```

## Configuration

Les variables d'environnement sont gérées via le fichier `.env` :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SECRET_KEY` | Clé secrète Django (obligatoire) | - |
| `DEBUG` | Mode debug | `False` |
| `ALLOWED_HOSTS` | Hôtes autorisés (séparés par virgules) | `''` |
| `DATABASE_URL` | URL de connexion à la base de données | `sqlite:///db.sqlite3` |
| `LANGUAGE_CODE` | Code langue | `fr-fr` |
| `TIME_ZONE` | Fuseau horaire | `Europe/Paris` |

### Exemples de DATABASE_URL

```bash
# SQLite (développement)
DATABASE_URL=sqlite:///db.sqlite3

# PostgreSQL (production)
DATABASE_URL=postgres://user:password@localhost:5432/lyon26
```

## Structure du projet

```
lyon26/
├── lyon26/              # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── mobilisation/        # App principale
│   ├── models/
│   │   └── visit.py     # Modèle Visit
│   ├── views.py         # Vues (Dashboard, API, etc.)
│   └── urls.py
├── territory/           # App données territoriales
│   ├── models/
│   │   ├── building.py  # Modèle Building
│   │   ├── voting_desk.py
│   │   └── district.py
│   └── admin.py
├── templates/           # Templates HTML
│   ├── base.html
│   └── mobilisation/
├── static/              # Fichiers statiques
│   └── css/
└── requirements.txt
```

## Modèles de données

### Territory

- **District** : Arrondissement/circonscription
- **VotingDesk** : Bureau de vote (code, nom, localisation)
- **Building** : Immeuble (adresse, nombre d'électeurs, coordonnées GPS)

### Mobilisation

- **Visit** : Visite de porte-à-porte
  - Lié à un ou plusieurs immeubles
  - Compteurs : portes frappées, portes ouvertes
  - Date et commentaires

## Accès Admin

Interface d'administration Django disponible sur `/admin/`

```
URL: http://localhost:8000/admin/
```

## API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Dashboard avec carte |
| `/bureaux/` | GET | Liste des bureaux de vote |
| `/bureaux/<code>/` | GET | Détail d'un bureau de vote |
| `/api/buildings/` | GET | JSON des immeubles pour la carte |
| `/api/visit/` | POST | Enregistrer une visite |

## Développement

### Lancer les tests

```bash
python3 manage.py test
```

### Collecter les fichiers statiques (production)

```bash
python3 manage.py collectstatic
```

## Production

Pour un déploiement en production :

1. Définir `DEBUG=False` dans `.env`
2. Générer une nouvelle `SECRET_KEY`
3. Configurer `ALLOWED_HOSTS`
4. Utiliser PostgreSQL
5. Configurer un serveur web (nginx + gunicorn)

```bash
# Générer une SECRET_KEY
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Licence

Projet privé - Tous droits réservés
