# Rappi PM Hub

Personal PM dashboard for Juan Pablo — pulls from Google Calendar, Gmail (Gemini notes), and Slack.

## Local use

```bash
python3 serve.py
```

Opens at http://localhost:3000. The "Actualizar" button calls the local Claude CLI to refresh data.

## Remote auto-update (GitHub Pages)

### Setup once

1. Push this repo to GitHub (see below)
2. Enable GitHub Pages: Settings → Pages → Source: `main` branch, `/` (root)
3. Add secrets in Settings → Secrets → Actions:
   - `ANTHROPIC_API_KEY` — your Anthropic API key
4. Generate a Personal Access Token (PAT):
   - github.com/settings/tokens/new
   - Scope: `workflow` only
   - Copy the token
5. In the PM Hub UI: click the settings gear, paste PAT + set repo as `username/rappi-pm-hub`

### How it works

- **Auto-refresh:** GitHub Actions runs daily at 7:30am Bogota
- **Manual refresh:** The "Actualizar" button triggers `workflow_dispatch` via GitHub API using your PAT (stored in localStorage)
- After refresh, GitHub Pages redeploys in ~1 min

## Pushing to GitHub

```bash
cd ~/rappi-pm-hub
git add .
git commit -m "Initial commit"
# Create repo on github.com (private), then:
git remote add origin https://github.com/YOUR-USERNAME/rappi-pm-hub.git
git branch -M main
git push -u origin main
```
