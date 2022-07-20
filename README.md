# Jérôme Ducret Resume
[![GitHub Super-Linter](https://github.com/DucretJe/JDResume/actions/workflows/super-linter.yaml/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![LaTeX](https://github.com/DucretJe/JDResume/actions/workflows/latex.yaml/badge.svg)](https://github.com/DucretJe/JDResume/actions/workflows/latex.yaml)


This is the repository hosting my CV code.
It uses LaTeX and a GitHub Action to compile it.
It is created from [GiantMolecularCloud Template](https://github.com/GiantMolecularCloud/my-resume)

The dependencies on this repository are automatically handled by Renovate.

## How to

### Generate a new copy

* Go to `Actions`
* Choose `LaTeX` worfklow on the left menu
* Clic on `Run workflow` and choose `main` branch, then confirm with the green `Run workflow` button
* Clic on the new running `LaTeX` workflow (you may have to refresh your browser)
* Once it is done you can download the artifact

### Change this resume
In order to be able to merge a Pull Request on this repository, the PR has to:

* pass LaTeX Super Linter
* get my approval

## Documentation

* [GitHub Actions](https://docs.github.com/en/actions)
  * [checkout](https://github.com/marketplace/actions/checkout)
  * [latex-action](https://github.com/marketplace/actions/github-action-for-latex)
  * [super-linter](https://github.com/marketplace/actions/super-linter)
  * [upload-artifact](https://github.com/marketplace/actions/upload-a-build-artifact)
* [LaTeX](https://www.latex-project.org/)
* [Renovate](https://docs.renovatebot.com/)
