# CV Job Matcher Agent

Cet agent utilise l'API Gemini pour adapter automatiquement votre CV LaTeX à une description de poste spécifique.

## Fonctionnalités

- ✅ **Grounded sur le contenu existant** : L'agent ne ment jamais et ne crée pas de compétences fictives
- ✅ **Reformulation intelligente** : Réorganise et reformule le contenu pour mettre en avant les compétences pertinentes
- ✅ **Préservation du format LaTeX** : Maintient l'intégrité du formatage LaTeX
- ✅ **Analyse contextuelle** : Utilise Gemini pour comprendre la job description et adapter le CV en conséquence

## Installation

```bash
pip install -r requirements.txt
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
python cv_matcher_agent.py --job-description "description du poste ici"
```

### Avec un fichier de job description

```bash
python cv_matcher_agent.py --job-description path/to/job_description.txt
```

### Options avancées

```bash
python cv_matcher_agent.py \
  --cv ./LaTeX/resume.tex \
  --job-description job_description.txt \
  --output ./LaTeX/resume_adapted.tex \
  --api-key "votre-clé-api" \
  --model gemini-1.5-pro
```

### Paramètres

- `--cv` : Chemin vers le fichier CV LaTeX (défaut: `./LaTeX/resume.tex`)
- `--job-description` : Description du poste (texte ou chemin vers un fichier)
- `--output` : Chemin de sortie pour le CV adapté (défaut: `./LaTeX/resume_adapted.tex`)
- `--api-key` : Clé API Gemini (ou variable d'environnement `GEMINI_API_KEY`)
- `--model` : Modèle Gemini à utiliser (défaut: `gemini-1.5-pro`)

## Utilisation dans GitHub Actions

L'agent est conçu pour être exécuté dans un workflow GitHub Actions. Voir `.github/workflows/cv-matcher.yaml` pour un exemple complet.

Le workflow :
1. Prend une job description en input
2. Exécute l'agent pour adapter le CV
3. Compile le CV LaTeX adapté en PDF
4. Upload le PDF comme artefact

## Exemple de workflow

```yaml
name: CV Job Matcher

on:
  workflow_dispatch:
    inputs:
      job_description:
        description: 'Job description to match CV against'
        required: true
        type: string

jobs:
  adapt-cv:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r agent/requirements.txt

      - name: Run CV Matcher Agent
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python agent/cv_matcher_agent.py \
            --job-description "${{ inputs.job_description }}"

      - name: Compile adapted CV to PDF
        uses: xu-cheng/latex-action@v3
        with:
          root_file: ./LaTeX/resume_adapted.tex
          latexmk_use_xelatex: true
        env:
          TEXINPUTS: "./LaTeX:"

      - name: Upload PDF artifact
        uses: actions/upload-artifact@v4
        with:
          name: adapted-cv-pdf
          path: resume_adapted.pdf
```

## Comment ça marche

L'agent suit ces étapes :

1. **Lecture du CV** : Lit le fichier LaTeX du CV original
2. **Extraction des sections** : Identifie les sections modifiables (tagline, expériences, compétences, etc.)
3. **Analyse avec Gemini** : Envoie le CV et la job description à Gemini avec des instructions strictes pour rester grounded
4. **Application des adaptations** : Remplace les sections du CV avec les versions adaptées
5. **Sauvegarde** : Écrit le nouveau CV LaTeX adapté

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
Si l'agent a du mal à parser la réponse de Gemini, vérifiez que vous utilisez un modèle récent (gemini-1.5-pro recommandé).

### Le CV adapté ne compile pas
L'agent préserve le format LaTeX, mais si la compilation échoue, vérifiez que le CV original compile correctement d'abord.

## Licence

Ce projet fait partie du repository JDResume.
