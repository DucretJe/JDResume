# CV Job Matcher Agent

Cet agent utilise l'API Gemini pour adapter automatiquement votre CV LaTeX à une description de poste spécifique.

## Fonctionnalités

- ✅ **Grounded sur le contenu existant** : L'agent ne ment jamais et ne crée pas de compétences fictives
- ✅ **Reformulation intelligente** : Réorganise et reformule le contenu pour mettre en avant les compétences pertinentes
- ✅ **Préservation du format LaTeX** : Maintient l'intégrité du formatage LaTeX
- ✅ **Analyse contextuelle** : Utilise Gemini pour comprendre la job description et adapter le CV en conséquence
- ✅ **Architecture modulaire** : Code organisé en modules logiques et maintenables
- ✅ **Gestion moderne des dépendances** : Utilise `uv` pour une installation ultra-rapide

## Architecture

Le projet est structuré en modules logiques :

```text
agent/
├── pyproject.toml              # Configuration uv et dépendances
└── cv_matcher/                 # Package principal
    ├── __init__.py
    ├── config.py               # Configuration et constantes
    ├── latex_parser.py         # Extraction des sections LaTeX
    ├── gemini_adapter.py       # Adaptation avec Gemini API
    ├── latex_writer.py         # Application des modifications
    └── cli.py                  # Interface en ligne de commande
```

## Installation

Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances Python.

### Installer uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installer les dépendances

```bash
cd agent
uv sync
```

## Configuration

Vous avez besoin d'une clé API Gemini. Vous pouvez l'obtenir sur [Google AI Studio](https://makersuite.google.com/app/apikey).

Définissez la clé API comme variable d'environnement :

```bash
export GEMINI_API_KEY="votre-clé-api-ici"
```

## Utilisation

### Utilisation basique

```bash
cd agent
uv run cv-matcher --job-description "description du poste ici"
```

### Avec un fichier de job description

```bash
cd agent
uv run cv-matcher --job-description ../examples/job_description_sre.txt
```

### Options avancées

```bash
cd agent
uv run cv-matcher \
  --cv ../LaTeX/resume.tex \
  --job-description ../examples/job_description_devops.txt \
  --output ../LaTeX/resume_adapted.tex \
  --api-key "votre-clé-api" \
  --model gemini-2.5-flash
```

### Paramètres

- `--cv` : Chemin vers le fichier CV LaTeX (défaut: `./LaTeX/resume.tex`)
- `--job-description` : Description du poste (texte ou chemin vers un fichier)
- `--output` : Chemin de sortie pour le CV adapté (défaut: `./LaTeX/resume_adapted.tex`)
- `--api-key` : Clé API Gemini (ou variable d'environnement `GEMINI_API_KEY`)
- `--model` : Modèle Gemini à utiliser (défaut: `gemini-2.5-flash`)

## Utilisation dans GitHub Actions

L'agent est conçu pour être exécuté dans un workflow GitHub Actions. Voir `.github/workflows/cv-matcher.yaml` pour un exemple complet.

Le workflow :
1. Prend une job description en input
2. Installe uv et les dépendances (avec cache pour performance)
3. Exécute l'agent pour adapter le CV
4. Compile le CV LaTeX adapté en PDF
5. Upload le PDF comme artefact

Le workflow utilise `uv` pour une installation ultra-rapide des dépendances et une gestion efficace du cache.

## Comment ça marche

L'agent suit ces étapes :

1. **Lecture du CV** (`LaTeXParser`) : Lit le fichier LaTeX du CV original
2. **Extraction des sections** (`LaTeXParser`) : Identifie les sections modifiables (tagline, expériences, compétences, etc.)
3. **Analyse avec Gemini** (`GeminiAdapter`) : Envoie le CV et la job description à Gemini avec des instructions strictes pour rester grounded
4. **Application des adaptations** (`LaTeXWriter`) : Remplace les sections du CV avec les versions adaptées
5. **Sauvegarde** (`LaTeXWriter`) : Écrit le nouveau CV LaTeX adapté

Chaque module a une responsabilité claire :
- **`config.py`** : Configuration et templates de prompts
- **`latex_parser.py`** : Parsing et extraction du contenu LaTeX
- **`gemini_adapter.py`** : Communication avec l'API Gemini
- **`latex_writer.py`** : Écriture des modifications dans le LaTeX
- **`cli.py`** : Interface en ligne de commande

## Règles strictes de l'agent

L'agent suit ces règles pour garantir l'intégrité :

- ❌ N'invente JAMAIS de compétences ou d'expériences
- ❌ N'exagère JAMAIS les capacités
- ✅ Reformule uniquement le contenu existant
- ✅ Réorganise pour mettre en avant les points pertinents
- ✅ Utilise les mots-clés de la job description quand approprié
- ✅ Préserve le format LaTeX original

## Dépannage

### Erreur : "Gemini API key not provided"
Assurez-vous d'avoir défini la variable d'environnement `GEMINI_API_KEY` ou de passer la clé via `--api-key`.

### Erreur JSON parsing
Si l'agent a du mal à parser la réponse de Gemini, vérifiez que vous utilisez un modèle récent (gemini-2.5-flash recommandé).

### Le CV adapté ne compile pas
L'agent préserve le format LaTeX, mais si la compilation échoue, vérifiez que le CV original compile correctement d'abord.

### uv command not found
Installez uv avec : `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Développement

### Structure du code

Le code est organisé en modules avec séparation des responsabilités :

- Parsing LaTeX séparé de la logique d'adaptation
- Adapter Gemini isolé pour faciliter les tests
- Configuration centralisée dans un module dédié
- CLI simple qui orchestre les modules

### Ajouter de nouvelles fonctionnalités

1. **Nouvelles sections LaTeX** : Modifiez `latex_parser.py` pour extraire de nouvelles sections
2. **Nouveaux modèles** : Changez le modèle dans `config.py`
3. **Prompts personnalisés** : Modifiez `ADAPTATION_PROMPT_TEMPLATE` dans `config.py`

### Tests

```bash
# Tester localement avec un exemple
cd agent
uv run cv-matcher --job-description ../examples/job_description_sre.txt
```

### Avantages de l'architecture modulaire

- **Maintenabilité** : Chaque module a une responsabilité unique
- **Testabilité** : Les modules peuvent être testés indépendamment
- **Extensibilité** : Facile d'ajouter de nouvelles fonctionnalités
- **Lisibilité** : Code plus court et plus facile à comprendre

## Licence

Ce projet fait partie du repository JDResume.
