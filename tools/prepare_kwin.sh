#!/bin/sh
# Tested against the Debian 13 amd64 cloud image; does not install system packages.
set -eu
cd "$(dirname "$0")/.."
[ "$(dpkg --print-architecture)" = amd64 ] || { echo 'Debian 13 amd64 runtime required' >&2; exit 1; }
[ -r /usr/share/keyrings/debian-archive-keyring.gpg ] || { echo 'Debian archive keyring required' >&2; exit 1; }
mkdir -p .cache/apt/lists/partial .cache/apt/cache/archives/partial .cache/apt/parts .cache/kwin/root .cache/kwin/native-qt
cat > .cache/apt/sources.list <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
SOURCES
cat > .cache/apt/apt.conf <<CONFIG
Dir::Etc::main "/dev/null";
Dir::Etc::parts "$PWD/.cache/apt/parts";
Dir::Etc::sourcelist "$PWD/.cache/apt/sources.list";
Dir::Etc::sourceparts "-";
Dir::State::lists "$PWD/.cache/apt/lists";
Dir::Cache "$PWD/.cache/apt/cache";
CONFIG
export APT_CONFIG="$PWD/.cache/apt/apt.conf"
/usr/bin/apt-get update
matrix_packages_dir=$(mktemp -d "$PWD/.cache/kwin/verified-debs.XXXXXX")
trap 'rm -rf "$matrix_packages_dir"' EXIT HUP INT TERM
matrix_prefix="$PWD/.cache/kwin/root"
matrix_manifest="$PWD/.cache/kwin/packages.txt"
cd "$matrix_packages_dir"
# Fresh directory: every extracted artifact comes from this verified APT download.
/usr/bin/apt-get download kwin-wayland libkwin6 kwin-common kwin-data libxcb-composite0 libkf6svg6 libqaccessibilityclient-qt6-0 libkf6idletime6 libkglobalacceld0 libqt6sensors6 libxcb-damage0 libkwaylandclient6 libplasmaactivities6 libkscreenlocker6 liblayershellqtinterface6 layer-shell-qt qml6-module-org-kde-layershell libkscreen-bin libkf6screen8 libkf6screendpms8 qt6-wayland libxcb-dpms0 konsole konsole-kpart libkf6pty6
: > "$matrix_manifest"
for package in ./*.deb; do
    dpkg-deb -x "$package" "$matrix_prefix"
    dpkg-deb -f "$package" Package Version >> "$matrix_manifest"
    sha256sum "$package" >> "$matrix_manifest"
done
# Keep distro Qt private modules out of the PySide client search path.
for library in "$matrix_prefix"/usr/lib/x86_64-linux-gnu/libQt6*.so*; do
    [ -e "$library" ] || [ -L "$library" ] || continue
    mv "$library" "$matrix_prefix/../native-qt/"
done
