# Repository rules for all agents

These rules apply to every agent and automated contributor working anywhere in
this repository.

## Mandatory publication checks

Treat every committed file as public. Before any push, every agent must:

1. Review the complete outgoing diff for private or sensitive information.
2. Review prose for grammar, spelling, and typographical errors.
3. Run `./scripts/preflight.sh` and resolve every reported problem.
4. Never bypass the pre-push hook with `--no-verify`.

The automated checks are a safety net, not a substitute for reviewing the
outgoing diff. Do not commit credentials, private keys, private contact details,
local filesystem paths, confidential material, or data that is not clearly
intended for public release. If publication intent is uncertain, stop and ask
the user.

## Private draft workspace

This repository is only for material approved for public release. Agents must
not create, copy, or leave drafts, ideas, research notes, source material, or
other non-public work anywhere in this checkout, including ignored and
untracked files.

Use the separately configured private workspace instead. Run
`./scripts/workspace.sh path` to confirm its location. To promote one explicit,
public-ready file, run:

```sh
./scripts/workspace.sh promote /path/to/source public/path/to/file
```

The promotion command refuses paths outside the private workspace, does not
stage the result, checks the copied file, and removes it if the checks fail.
Review the resulting diff before staging it. Never configure the private
workspace inside this repository, a Git worktree that shares this repository,
or a branch of this public remote.

Private work must remain compatible with the public site. Initialize a new
private workspace with `./scripts/workspace.sh initialize`. Agents must keep
its `index.html` in the same site format as this landing page, run
`./scripts/workspace.sh check` after changes, and use
`./scripts/workspace.sh preview` to inspect it locally before promoting files.
The private workspace has its own `AGENTS.md`; its rules apply whenever work is
performed there.

Start every new post with `./scripts/workspace.sh new-post SLUG`. That command
creates the post only in the private workspace and installs its recorded checks
and hooks there. Never create a new post directly in this public repository.
The link to the private workspace is local Git configuration only; do not add a
tracked filesystem path, submodule, remote URL, or reference that could expose
the private workspace.

## Site structure

- Keep `/index.html` as the public landing page.
- Give the landing page one clear, visible headline in an `h1` element.
- Keep public-facing copy concise, accessible, and responsive.

## Completion standard

Do not report a change as ready to push until `./scripts/preflight.sh` passes.
When handing work back to the user, state whether the checks were run and
whether they passed.
