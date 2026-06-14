# Publishing Notes

This file is for the project maintainer. It is not required for end users.

## GitHub Repository

Check the worktree before publishing:

```powershell
git status --short
git diff --check
```

Stage the project files:

```powershell
git add README.md docs/PUBLISHING.md pyproject.toml Dockerfile .dockerignore .github lm_studio_watchdog
git status --short
git commit -m "Add Docker packaging and publish workflow"
```

If the repository has no remote yet:

```powershell
git branch -M main
git remote add origin https://github.com/HBaz92/LM-Studio_Watch-Dog.git
git push -u origin main
```

If the remote already exists:

```powershell
git push
```

## License Decision

Before making the repository public, decide whether the project should be open source.

Common options:

- Add an MIT license if users are allowed to use, copy, modify, and redistribute the project.
- Add another license such as Apache-2.0 if you want explicit patent terms.
- Keep the repository private if you do not want to grant reuse rights.

If you add a license file, the public README can include a short section such as:

```markdown
## License

MIT License. See [LICENSE](LICENSE).
```

## Docker Hub and GHCR

The workflow at `.github/workflows/docker-publish.yml` publishes images to:

```text
hassanbaz92/lm-studio-watchdog
ghcr.io/hbaz92/lm-studio-watchdog
```

Create a Docker Hub access token, then add these GitHub repository secrets:

```text
DOCKERHUB_USERNAME = hassanbaz92
DOCKERHUB_TOKEN    = <Docker Hub access token>
```

Push to `main`, or create a version tag:

```powershell
git tag v1.0.10
git push origin main --tags
```

## Manual Docker Publish

```powershell
docker login
docker build -t hassanbaz92/lm-studio-watchdog:1.0.10 .
docker tag hassanbaz92/lm-studio-watchdog:1.0.10 hassanbaz92/lm-studio-watchdog:latest
docker push hassanbaz92/lm-studio-watchdog:1.0.10
docker push hassanbaz92/lm-studio-watchdog:latest
```
