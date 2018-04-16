#!/usr/bin/env bash

set -e

exit_cleanup() {
    cd $pwd
}

trap exit_cleanup EXIT

pwd=`pwd`

mkdir -p deps

DEPS=$(cat deps.ini)

for DEP in ${DEPS}; do
    split=(${DEP//==/ })
    repo=${split[0]}
    version=${split[1]}

    if [[ ! -d "deps/${repo}" ]]; then
        git clone git@github.com:Automatic/${repo} deps/${repo}
    fi
    cd deps/${repo}
    if [[ "$(git tag -l --points-at HEAD)" =~ (^|[[:space:]])${version}($|[[:space:]]) ]]; then
        cd - > /dev/null
        continue
    fi
    if [[ "$(cat .git/HEAD)" != "ref: refs/heads/master" ]]; then
        git checkout master
    fi
    if [[ "$(git diff --cached --abbrev=40 --full-index --raw --ignore-submodules)" != "" ]]; then
        echo "repo state for ${repo} is dirty, aborting"
        exit 2
    fi
    if [[ "$(git diff --abbrev=40 --full-index --raw --ignore-submodules)" != "" ]]; then
        echo "repo state for ${repo} is dirty, aborting"
        exit 3
    fi
    git fetch origin
    git reset --hard origin/master
    git checkout $version
    cd - > /dev/null
done

echo "All dependencies up-to-date"
