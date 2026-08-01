# Private workspace rules for all agents

This is a local private workspace for developing material that may later be
promoted to the public Jeff Kline site. Nothing here is public by default.

## Required workflow

1. Start each post only with the paired public repository's
   `scripts/workspace.sh new-post SLUG` command. Posts live in
   `posts/SLUG/index.html` in this private repository.
2. Preserve the public HTML contract in every HTML file: HTML5 doctype,
   language, UTF-8 and viewport metadata, one `main` element, one visible
   `h1`, and four-space indentation.
3. Run `./scripts/preflight.sh` after every change and before every commit or
   push. Never bypass the private pre-commit or pre-push hooks.
4. Run `scripts/workspace.sh preview` from the paired public repository to view
   the private site locally before promoting any file.
5. Promote only reviewed, public-ready files through `workspace.sh promote`.
   Do not manually copy material into the public repository.

The paired public repository path is stored only in this workspace's local Git
configuration under `jeff.publicSitePath`. Do not add this private workspace as
a remote or worktree of the public repository.
