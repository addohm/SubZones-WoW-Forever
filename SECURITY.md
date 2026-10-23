# Security

## Reporting a problem

Contact the maintainer through GitHub (@addohm), for example via a private security advisory on this repository. Please don't open a public issue for a vulnerability.

## Secrets

SubZones-WoW-Forever uses no secrets:

- **The addon:** runs inside the game client, with no network access or credentials.
- **The data tools:** read the local game install, and download only public files from Blizzard's CDN anonymously. The CDN hosts and paths come from the install's own `.build.info`.

`.gitignore` excludes secret-looking files (`.env`, keys, tokens) anyway. Never commit them.

## Access

The repository is public; only the owner can push to `main`. Releases are zips of the `SUBZONES/` folder in `releases/`, uploaded to CurseForge and Wago by the owner, so there is no production environment to grant access to.
