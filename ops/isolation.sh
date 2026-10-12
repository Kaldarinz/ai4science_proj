#!/usr/bin/env bash
# Isolation of the course agent: it runs as OS user aiagent, and the bans
# marked [env] in AGENTS.md §4 are enforced by file permissions.
# Reproduces the home setup of 2026-10-04/08.
#
#   sudo --preserve-env=HTTPS_PROXY,HTTP_PROXY,NO_PROXY bash ops/isolation.sh
#
# The proxy variables are needed only where the network goes through a proxy
# (lab machine: 127.0.0.1:2080); sudo drops them otherwise and pip times out.
#
# Safe to re-run. Afterwards: log out and in (anton joins aiproj), then install
# the agent as aiagent; the script prints the commands at the end.
set -euo pipefail

OWNER=anton
AGENT=aiagent
GROUP=aiproj
PROJ=/srv/ai4science_proj
OLD=/home/$OWNER/dev/shad/ai4science_proj      # becomes a symlink to $PROJ
STORE=/home/$OWNER/dev/ablation_db/data/files/open
WRITABLE=(results src tests memory)            # plus diary.md
PY_PKGS=(numpy scipy pandas pytest pypdf)

[[ $EUID -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
as() { local u=$1; shift; sudo -u "$u" -H "$@"; }

echo "== 1. User $AGENT, group $GROUP"
getent group $GROUP >/dev/null || groupadd $GROUP
id $AGENT >/dev/null 2>&1 || useradd -m -s /bin/bash $AGENT
passwd -l $AGENT >/dev/null                    # no password: only sudo -iu
usermod -aG $GROUP $OWNER
usermod -aG $GROUP $AGENT
if id -nG $AGENT | grep -qwE 'sudo|docker|lxd|libvirt|adm'; then
  echo "$AGENT is in a privileged group: $(id -nG $AGENT)" >&2; exit 1
fi

echo "== 2. Homes closed to others"
chmod 750 /home/$OWNER /home/$AGENT

echo "== 3. Project in $PROJ"
if [[ -d $OLD && ! -L $OLD ]]; then
  [[ -e $PROJ ]] && { echo "$PROJ already exists; not moving $OLD" >&2; exit 1; }
  mv "$OLD" "$PROJ"
  ln -s "$PROJ" "$OLD"
  chown -h $OWNER:$OWNER "$OLD"
fi
cd "$PROJ"

echo "== 4. Article PDFs from the ablation_db file store"
# install -m 640, not cp: the store keeps files as 600, and cp keeps the mode.
tail -n +2 data/files.csv | while IFS=, read -r id file _role sha; do
  sha=${sha%$'\r'}
  src=$STORE/$sha/$file
  if [[ -f $src ]]; then
    install -d -o $OWNER -g $GROUP -m 2750 "data/articles/$id"
    install -o $OWNER -g $GROUP -m 640 "$src" "data/articles/$id/$file"
  else
    echo "   missing in the file store: $id $file" >&2
  fi
done

echo "== 5. Python for the agent: .venv owned by $OWNER, read-only for $GROUP"
PROXY_ENV=()
for v in HTTPS_PROXY HTTP_PROXY NO_PROXY https_proxy http_proxy no_proxy; do
  [[ -n ${!v:-} ]] && PROXY_ENV+=("$v=${!v}")
done
[[ -x .venv/bin/python ]] || as $OWNER python3 -m venv .venv
as $OWNER env "${PROXY_ENV[@]}" .venv/bin/pip install -q --disable-pip-version-check "${PY_PKGS[@]}"

echo "== 6. Permissions"
mkdir -p "${WRITABLE[@]}"
touch diary.md
chown -R $OWNER:$GROUP "$PROJ"
chmod -R u+rwX,g=rX,o= "$PROJ"                 # baseline: read-only for the agent
find "$PROJ" -type d -exec chmod g+s {} +      # new files land in $GROUP
for d in "${WRITABLE[@]}"; do
  chmod -R g+w "$d"
  find "$d" -type d -exec setfacl -m d:u::rwX,d:g::rwX,d:o::--- {} +
done
chmod g+w diary.md
find data -type d -exec setfacl -m d:u::rwX,d:g::r-X,d:o::--- {} +

echo "== 7. git shared by the group"
as $OWNER git -C "$PROJ" config core.sharedRepository group
chmod -R g+rwX .git
as $AGENT git config --global --replace-all safe.directory "$PROJ"
as $AGENT git config --global user.name "ai4science agent"
as $AGENT git config --global user.email "$AGENT@localhost"

echo "== 8. Checks as $AGENT"
fail=0
check() {  # description, command, expected yes/no
  local got=no
  as $AGENT bash -c "$2" >/dev/null 2>&1 && got=yes
  if [[ $got == "$3" ]]; then echo "   OK    $1"; else echo "   FAIL  $1 (got $got)"; fail=1; fi
}
check "reads /home/$OWNER: no"        "ls /home/$OWNER"                          no
check "reads AGENTS.md: yes"          "cat $PROJ/AGENTS.md"                      yes
check "reads article PDFs: yes"       "cat $PROJ/data/articles/*/*.pdf"          yes
check "writes results/: yes"          "touch $PROJ/results/.iso && rm $PROJ/results/.iso" yes
check "writes diary.md: yes"          "test -w $PROJ/diary.md"                   yes
check "writes checks/: no"            "touch $PROJ/checks/.iso"                  no
check "writes data/: no"              "touch $PROJ/data/.iso"                    no
check "writes project root: no"       "touch $PROJ/.iso"                         no
check "installs into .venv: no"       "touch $PROJ/.venv/.iso"                   no
check "runs project Python: yes"      "$PROJ/.venv/bin/python -c 'import numpy, scipy, pandas, pypdf, pytest'" yes
check "writes git objects: yes"       "test -w $PROJ/.git/objects && git -C $PROJ status" yes
check "uses sudo: no"                 "sudo -n true"                             no
rm -f "$PROJ"/{checks,data,.venv}/.iso "$PROJ/.iso"

cat <<EOF

Next, by hand:
  1. Log out and in, so that $OWNER is in $GROUP (check: id -nG).
  2. Install the agent as $AGENT; the wizard asks for the Yandex AI Studio key:
       sudo -iu $AGENT
       export HTTPS_PROXY=${HTTPS_PROXY:-} HTTP_PROXY=${HTTP_PROXY:-}   # skip if empty
       git clone https://github.com/andkhalov/AI4Science.git ~/AI4Science
       cd ~/AI4Science && ./setup.sh
       exit; sudo -iu $AGENT       # new login puts ~/.local/bin in PATH
       ai4science doctor
  3. Run the agent: sudo -iu $AGENT, then cd $PROJ && ai4science
EOF
exit $fail
