#!/bin/bash -eux
# ./docs/release.sh [patch|minor|major|x.y.z]

[[ $(basename $PWD) == docs ]] && cd ..


OLD=$(poetry version -s)

poetry version $1

NEW=$(poetry version -s)
DATE=$(date +%Y-%m-%d)

sed -i "/^## \[Unreleased\]/a \\\n## [$NEW] - $DATE" CHANGELOG.md
sed -i "/^\[Unreleased\]/s/$OLD/$NEW/" CHANGELOG.md
sed -i "/^\[Unreleased\]/a [$NEW] https://github.com/nim65s/matrix-webhook/compare/v$OLD...v$NEW" CHANGELOG.md

echo git add pyproject.toml CHANGELOG.md
echo git commit -m "Release v$NEW"
echo git tag -s "v$NEW" -m "Release v$NEW"
