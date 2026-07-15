# GitHub setup

## Repository name

**GeneWeave** → recommended repo name: `geneweave`

Documentation URL after deploy:

```text
https://mohamadysn.github.io/geneweave/
```

## 1. Create the repository on GitHub

From the project root:

```bash
git init
git add .
git commit -m "Initial commit: GeneWeave — multi-database gene annotation"

git remote add origin git@github.com:mohamadysn/geneweave.git
git branch -M main
git push -u origin main
```

Or if the repo already exists on GitHub (with an empty README):

```bash
git remote add origin git@github.com:mohamadysn/geneweave.git
git pull origin main --allow-unrelated-histories
git push -u origin main
```

**Important:** do not commit build artifacts. Keep these out of git (already listed in `.gitignore`):

- `dist/`, `build/` — PyInstaller binaries
- `.venv/`, `venv/` — local virtualenvs
- `results/`, `.cache/` — run outputs and cache

## 2. Enable GitHub Pages

1. Open your repo on GitHub → **Settings** → **Pages**
2. Under **Build and deployment** → **Source**, select **GitHub Actions**
3. Push to `main` — the workflow `.github/workflows/publish-docs.yml` deploys automatically

## 3. Update the site URL

Edit `docs/_quarto.yml` and set `website.site-url` to match your GitHub Pages URL (with trailing slash):

```yaml
website:
  site-url: https://mohamadysn.github.io/geneweave/
```

The CI workflow also passes `--site-url` automatically on each deploy.

## 4. Local documentation (HTTP)

Preview with live reload (opens browser at `http://127.0.0.1:8088`):

```bash
python3 docs/render.py
```

Serve the built static site over HTTP:

```bash
python3 docs/render.py --build --serve
```

## 5. Desktop binaries (optional)

Build Linux / Windows standalone apps locally:

```bash
bash scripts/build_linux.sh
scripts\build_windows.bat
```

Or use CI: push a tag `v1.1.0` (or run **Build desktop binaries** manually).  
Artifacts are uploaded; tagged pushes create a GitHub Release.

See [docs/desktop.qmd](docs/desktop.qmd) for full details.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `publish-docs.yml` | Push to main | Build Quarto site → GitHub Pages |
| `ci.yml` | Push / PR | Python import check + dry-run |
| `build-desktop.yml` | Tag `v*` or manual | PyInstaller binaries + optional Release |
