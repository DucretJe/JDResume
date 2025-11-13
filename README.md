# Jérôme Ducret Resume
[![GitHub Super-Linter](https://github.com/DucretJe/JDResume/actions/workflows/super-linter.yaml/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![LaTeX](https://github.com/DucretJe/JDResume/actions/workflows/latex.yaml/badge.svg)](https://github.com/DucretJe/JDResume/actions/workflows/latex.yaml)
[![CV Job Matcher](https://github.com/DucretJe/JDResume/actions/workflows/cv-matcher.yaml/badge.svg)](https://github.com/DucretJe/JDResume/actions/workflows/cv-matcher.yaml)


This is the repository hosting my CV code.
It uses LaTeX and a GitHub Action to compile it.
It is created from [GiantMolecularCloud Template](https://github.com/GiantMolecularCloud/my-resume)

The dependencies on this repository are automatically handled by Renovate.

## 🤖 AI-Powered CV Job Matcher

This repository now includes an AI agent that adapts your CV to match specific job descriptions! The agent uses Google's Gemini API to intelligently reformulate and highlight relevant skills while staying grounded on your actual experience.

### Features
- ✅ **Smart adaptation**: Analyzes job descriptions and adapts your CV accordingly
- ✅ **Truth-grounded**: Never invents skills or experiences
- ✅ **Intelligent reformulation**: Reorganizes and highlights relevant content
- ✅ **LaTeX preservation**: Maintains perfect formatting
- ✅ **Automated workflow**: Runs in GitHub Actions and produces PDF artifacts
- ✅ **Modular architecture**: Clean, maintainable code split into logical modules
- ✅ **Modern tooling**: Uses `uv` for blazing-fast dependency management

See [agent/README.md](agent/README.md) for detailed documentation.

## How to

### Generate a standard CV copy

* Go to `Actions`
* Choose `LaTeX` worfklow on the left menu
* Clic on `Run workflow` and choose `main` branch, then confirm with the green `Run workflow` button
* Clic on the new running `LaTeX` workflow (you may have to refresh your browser)
* Once it is done you can download the artifact

### Generate an AI-adapted CV for a specific job

* Go to `Actions`
* Choose `CV Job Matcher` workflow on the left menu
* Click on `Run workflow`
* Paste the job description in the text field (or specify a path to a file in the repository)
* Confirm with the green `Run workflow` button
* Wait for the workflow to complete
* Download the adapted CV PDF from the artifacts

**Note**: The first time you run this, you'll need to add your Gemini API key as a repository secret named `GEMINI_API_KEY`. Get your API key at [Google AI Studio](https://makersuite.google.com/app/apikey).

### Test the CV Matcher locally

You can test the agent locally before running it in GitHub Actions:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set your Gemini API key
export GEMINI_API_KEY='your-api-key-here'

# Run the test script
./test_agent_local.sh
```

This will adapt your CV using the example job description in `examples/job_description_sre.txt`.

Or run the agent directly:

```bash
cd agent
uv sync  # Install dependencies
uv run cv-matcher --job-description ../examples/job_description_sre.txt
```

### Change this resume
In order to be able to merge a Pull Request on this repository, the PR has to:

* pass LaTeX Super Linter
* get my approval

## Repository Structure

```text
JDResume/
├── LaTeX/                    # LaTeX CV source files
│   ├── resume.tex           # Main CV file
│   ├── my-resume.cls        # Custom LaTeX class
│   └── photo.jpg            # Profile photo
├── agent/                    # AI CV Matcher Agent
│   ├── pyproject.toml       # uv configuration & dependencies
│   ├── cv_matcher/          # Main package
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration & prompts
│   │   ├── latex_parser.py  # LaTeX extraction
│   │   ├── gemini_adapter.py # Gemini API integration
│   │   ├── latex_writer.py  # LaTeX writing
│   │   └── cli.py           # Command-line interface
│   └── README.md            # Agent documentation
├── examples/                 # Example job descriptions
│   ├── job_description_sre.txt
│   └── job_description_devops.txt
├── .github/workflows/        # GitHub Actions workflows
│   ├── latex.yaml           # Standard CV compilation
│   ├── cv-matcher.yaml      # AI CV adaptation workflow (uses uv)
│   └── super-linter.yaml    # Code linting
└── test_agent_local.sh      # Local testing script
```

## Documentation

* [GitHub Actions](https://docs.github.com/en/actions)
  * [checkout](https://github.com/marketplace/actions/checkout)
  * [latex-action](https://github.com/marketplace/actions/github-action-for-latex)
  * [super-linter](https://github.com/marketplace/actions/super-linter)
  * [upload-artifact](https://github.com/marketplace/actions/upload-a-build-artifact)
* [LaTeX](https://www.latex-project.org/)
* [Renovate](https://docs.renovatebot.com/)
* [Google Gemini API](https://ai.google.dev/)
* [uv - Python Package Manager](https://docs.astral.sh/uv/)
* [CV Matcher Agent Documentation](agent/README.md)
