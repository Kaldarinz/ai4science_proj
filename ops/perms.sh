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
WRITABLE=(results src tests memory)            # plus diary.md
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
q chmod 600 README.md                          # for the human only
q find data -type d -exec setfacl -m d:u::rwX,d:g::r-X,d:o::--- {} +
q chmod -R g+rwX .git                          # the agent commits
echo "perms: agent permissions restored"
