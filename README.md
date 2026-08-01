# Jeff Kline's public website

This repository contains the public GitHub Pages site at `jeff-kline.github.io`.
The headline landing page is [`index.html`](index.html).

## Required checks

Every change must pass a privacy review and a writing review before it is
pushed. Install the committed hook once per clone:

```sh
git config core.hooksPath .githooks
```

Run the same checks at any time with:

```sh
./scripts/preflight.sh
```

The checks also run in GitHub Actions. See [`AGENTS.md`](AGENTS.md) for the rules
that apply to all agents and automated contributors.

## Private drafts

Do not place non-public drafts in this public repository, including ignored
files. The separately configured private workspace is the only location for
iterative work that is not ready to publish. Use `./scripts/workspace.sh path`
to check the configured location, and use `./scripts/workspace.sh promote` only
when deliberately moving a reviewed file into this repository.

Initialize the private workspace once with:

```sh
./scripts/workspace.sh initialize
```

It starts with the same landing-page structure as the public site. Use
`./scripts/workspace.sh check` to enforce the shared HTML contract and
`./scripts/workspace.sh preview` to view the draft locally before promotion.

Start a post in the private workspace, never here:

```sh
./scripts/workspace.sh new-post my-post-slug
```

Private preflight checks and Git hooks are recorded in that workspace. Its
local configuration points back to this repository without publishing a path
or URL.
