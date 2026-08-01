#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(git -C "$script_dir/.." rev-parse --show-toplevel)
repo_root=$(cd "$repo_root" && pwd -P)

fail() {
    echo "Workspace safety check failed: $*" >&2
    exit 1
}

private_workspace() {
    configured_path=$(git -C "$repo_root" config --local --get jeff.privateDraftsPath || true)
    test -n "$configured_path" || fail "no private workspace is configured"
    test -d "$configured_path" || fail "configured private workspace does not exist"

    workspace_root=$(cd "$configured_path" && pwd -P)
    case "$workspace_root" in
        "$repo_root" | "$repo_root"/*)
            fail "private workspace must be outside this public repository"
            ;;
    esac

    workspace_common=$(git -C "$workspace_root" rev-parse --git-common-dir 2>/dev/null) \
        || fail "private workspace must be a separate local Git repository"
    repo_common=$(git -C "$repo_root" rev-parse --git-common-dir)
    case "$workspace_common" in
        /*) ;;
        *) workspace_common="$workspace_root/$workspace_common" ;;
    esac
    case "$repo_common" in
        /*) ;;
        *) repo_common="$repo_root/$repo_common" ;;
    esac
    workspace_common=$(cd "$workspace_common" && pwd -P)
    repo_common=$(cd "$repo_common" && pwd -P)
    test "$workspace_common" != "$repo_common" \
        || fail "private workspace must not share this repository's Git history"

    public_origin=$(git -C "$repo_root" remote get-url origin 2>/dev/null || true)
    workspace_origin=$(git -C "$workspace_root" remote get-url origin 2>/dev/null || true)
    if test -n "$public_origin" && test "$public_origin" = "$workspace_origin"; then
        fail "private workspace must not use this public repository's origin"
    fi

    printf '%s\n' "$workspace_root"
}

command_name=${1:-path}

case "$command_name" in
    path)
        test "$#" -le 1 || fail "usage: $0 path"
        private_workspace
        ;;
    initialize)
        test "$#" = 1 || fail "usage: $0 initialize"
        workspace_root=$(private_workspace)
        mkdir -p "$workspace_root/.githooks" "$workspace_root/scripts"
        if test ! -e "$workspace_root/index.html"; then
            cp "$repo_root/index.html" "$workspace_root/index.html"
        fi
        cp "$repo_root/templates/workspace-AGENTS.md" "$workspace_root/AGENTS.md"
        cp "$repo_root/templates/workspace/preflight.sh" "$workspace_root/scripts/preflight.sh"
        cp "$repo_root/templates/workspace/pre-commit" "$workspace_root/.githooks/pre-commit"
        cp "$repo_root/templates/workspace/pre-push" "$workspace_root/.githooks/pre-push"
        chmod +x "$workspace_root/scripts/preflight.sh" \
            "$workspace_root/.githooks/pre-commit" \
            "$workspace_root/.githooks/pre-push"
        git -C "$workspace_root" config --local jeff.publicSitePath "$repo_root"
        git -C "$workspace_root" config --local core.hooksPath .githooks
        (cd "$workspace_root" && ./scripts/preflight.sh)
        echo "Private workspace initialized with recorded checks and the public site contract."
        ;;
    check)
        test "$#" = 1 || fail "usage: $0 check"
        workspace_root=$(private_workspace)
        (cd "$workspace_root" && ./scripts/preflight.sh)
        ;;
    preview)
        test "$#" -le 2 || fail "usage: $0 preview [PORT]"
        workspace_root=$(private_workspace)
        preview_port=${2:-8000}
        case "$preview_port" in
            '' | *[!0-9]*) fail "preview port must be a number" ;;
        esac
        test "$preview_port" -ge 1024 && test "$preview_port" -le 65535 \
            || fail "preview port must be between 1024 and 65535"
        "$repo_root/scripts/workspace.sh" check
        echo "Preview available only on this computer at http://127.0.0.1:$preview_port"
        exec python3 -m http.server "$preview_port" --bind 127.0.0.1 --directory "$workspace_root"
        ;;
    new-post)
        test "$#" = 2 || fail "usage: $0 new-post SLUG"
        post_slug=$2
        case "$post_slug" in
            '' | -* | *- | *--* | *[!a-z0-9-]*)
                fail "post slug must use lowercase letters, numbers, and single hyphens"
                ;;
        esac
        "$repo_root/scripts/workspace.sh" initialize
        workspace_root=$(private_workspace)
        post_path="$workspace_root/posts/$post_slug/index.html"
        test ! -e "$post_path" || fail "a private post already exists with this slug"
        mkdir -p "$(dirname "$post_path")"
        cp "$repo_root/templates/post.html" "$post_path"
        "$repo_root/scripts/workspace.sh" check
        echo "Started private post posts/$post_slug/index.html. Preview it before promotion."
        ;;
    promote)
        test "$#" = 3 || fail "usage: $0 promote SOURCE DESTINATION"
        workspace_root=$(private_workspace)
        source_path=$2
        destination=$3

        "$repo_root/scripts/workspace.sh" check

        test -f "$source_path" || fail "source is not a file"
        source_path=$(cd "$(dirname "$source_path")" && pwd -P)/$(basename "$source_path")
        test ! -L "$source_path" || fail "source must not be a symbolic link"
        case "$source_path" in
            "$workspace_root"/*) ;;
            *) fail "source must be inside the configured private workspace" ;;
        esac

        case "$destination" in
            '' | /* | . | .. | ../* | */../* | */..)
                fail "destination must be a relative path inside this repository"
                ;;
        esac
        target_parent=$(dirname "$repo_root/$destination")
        mkdir -p "$target_parent"
        target_parent=$(cd "$target_parent" && pwd -P)
        case "$target_parent" in
            "$repo_root" | "$repo_root"/*) ;;
            *) fail "destination must resolve inside this public repository" ;;
        esac
        target_path="$target_parent/$(basename "$destination")"
        test ! -e "$target_path" && test ! -L "$target_path" || fail "destination already exists; review changes manually"

        cp "$source_path" "$target_path"
        cleanup_target=true
        trap 'if [ "$cleanup_target" = true ]; then rm -f "$target_path"; fi' EXIT HUP INT TERM

        if ! "$repo_root/scripts/preflight.sh" --path "$destination"; then
            fail "copied file did not pass publication checks and was removed"
        fi

        cleanup_target=false
        trap - EXIT HUP INT TERM
        echo "Promoted $destination. Review it with git diff before staging."
        ;;
    *)
        fail "usage: $0 {path|initialize|check|preview [PORT]|new-post SLUG|promote SOURCE DESTINATION}"
        ;;
esac
