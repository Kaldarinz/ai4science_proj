#!/usr/bin/env bash
# File modes of the agent isolation: read-only for the agent except the
# writable folders and diary.md. Run by ops/isolation.sh (as root) and,
# copied to .git/hooks/post-checkout, after each branch switch (as anton):
# checkout writes files with the umask, which makes them readable or
# writable for the group. As anton, files owned by aiagent cannot be
# changed; those errors are expected and dropped.
set -uo pipefail
[[ $# -lt 3 || $3 == 1 ]] || exit 0            # hook: branch switches only

GROUP=aiproj
PROJ=/srv/ai4science_proj
WRITABLE=(results memory)                      # plus diary.md; supplied code is read-only
cd "$PROJ" || exit 1
q() { "$@" 2>/dev/null; }

q chgrp -R $GROUP "$PROJ"
q chmod -R u+rwX,g=rX,o= "$PROJ"               # baseline: read-only for the agent
q find "$PROJ" -type d -exec chmod g+s {} +    # new files land in $GROUP
for d in "${WRITABLE[@]}"; do
  q chmod -R g+w "$d"
  q find "$d" -type d -exec setfacl -m d:u::rwX,d:g::rwX,d:o::--- {} +
done
q chmod g+w diary.md
# Narrow writing workspace. The sticky bit protects Anton-owned entries
# (e.g. the class) from removal/replacement by aiagent. Edit the shared
# manuscript in place; create generated fragments and builds under paper/.
q chmod g+w,+t paper
q chmod g+w paper/paper.tex GLOSSARY.md lit/lit.md
q find paper lit research -type d -exec setfacl -m d:u::rwX,d:g::r-X,d:o::--- {} +
q chmod 600 README.md                          # for the human only
for d in data checks tools src tests; do
  q find "$d" -type d -exec setfacl -m d:u::rwX,d:g::r-X,d:o::--- {} +
done
q chmod -R g+rwX .git                          # the agent commits
echo "perms: agent permissions restored"
