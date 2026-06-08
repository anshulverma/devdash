#!/usr/bin/env bash
# Lockstep versioning: stamp one version across the npm package, the Python
# package, and the contract constants. Usage: scripts/set-version.sh 0.1.0
# (the release workflow derives the version from the git tag).
set -euo pipefail
VERSION="${1:?usage: set-version.sh X.Y.Z}"
VERSION="${VERSION#v}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# npm UI package
node -e "const f='$ROOT/packages/ui/package.json';const p=require(f);p.version='$VERSION';require('fs').writeFileSync(f,JSON.stringify(p,null,2)+'\n')"
# Python package
python3 - "$ROOT/packages/api/src/devdash/version.py" "$VERSION" <<'PY'
import re, sys
path, version = sys.argv[1], sys.argv[2]
s = open(path).read()
s = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', s)
open(path, "w").write(s)
PY
python3 - "$ROOT/packages/api/pyproject.toml" "$VERSION" <<'PY'
import re, sys
path, version = sys.argv[1], sys.argv[2]
s = open(path).read()
s = re.sub(r'(?m)^version = "[^"]*"', f'version = "{version}"', s, count=1)
open(path, "w").write(s)
PY
echo "stamped version $VERSION (npm + python)"
