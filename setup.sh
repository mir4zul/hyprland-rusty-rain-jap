#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash setup.sh [--check | --uninstall]'
    echo 'One-command setup for Arch Linux and Arch-based Hyprland sessions.'
    exit 0
fi
mode=${1:-install}
[[ $mode == install || $mode == --check || $mode == --uninstall ]] || { echo 'Unknown option' >&2; exit 1; }
[[ $EUID != 0 ]] || { echo 'Run as your desktop user, not with sudo. Package installation asks for sudo itself.' >&2; exit 1; }
source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
    *' arch '*) ;;
    *) echo 'Automatic dependency installation currently supports Arch-based Linux only.' >&2; exit 1 ;;
esac
[[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] || { echo 'Run this from a terminal inside your Hyprland session.' >&2; exit 1; }
config=${XDG_CONFIG_HOME:-$HOME/.config}
state="$config/dms-live-rain-state.json"
packages=()
command -v python3 >/dev/null || packages+=(python)
command -v dms >/dev/null || packages+=(dms-shell dms-shell-hyprland)
command -v qs >/dev/null || packages+=(quickshell)
pacman -Q noto-fonts-cjk >/dev/null 2>&1 || packages+=(noto-fonts-cjk)
pacman -Q qt6-multimedia >/dev/null 2>&1 || packages+=(qt6-multimedia)
if [[ $mode == --check ]]; then
    printf 'Missing packages: %s\n' "${packages[*]:-none}"
    if [[ -f $state ]]; then
        echo 'Rain is already installed.'
    elif command -v python3 >/dev/null && [[ -f /usr/share/quickshell/dms/Modules/Lock/LockSurface.qml ]]; then
        python3 install.py --check
    else
        echo 'DMS compatibility will be checked after dependencies are installed.'
    fi
    exit 0
fi
systemctl --user is-active graphical-session.target >/dev/null || { echo 'The systemd graphical session is not active; desktop configuration has not been changed.' >&2; exit 1; }
if systemctl --user is-active --quiet dms; then
    [[ $(dms ipc call lock isLocked) == false ]] || { echo 'Unlock the desktop before running setup.' >&2; exit 1; }
fi
if [[ $mode == --uninstall ]]; then
    python3 install.py --uninstall
    systemctl --user daemon-reload
    systemctl --user restart dms
    echo 'Rain removed. Shared system packages and the DMS service are retained.'
    exit 0
fi
if ((${#packages[@]})); then
    echo 'Installing missing dependencies. Pacman will show its package/system upgrade transaction for confirmation.'
    sudo pacman -Syu --needed "${packages[@]}"
fi
command -v dms >/dev/null
command -v qs >/dev/null
systemctl --user cat dms.service >/dev/null
was_active=false
was_enabled=false
systemctl --user is-active --quiet dms && was_active=true
systemctl --user is-enabled --quiet dms && was_enabled=true
fresh_install=false
rollback() {
    result=$?
    trap - ERR
    if [[ $fresh_install == true ]]; then
        echo 'Activation failed; restoring the previous rain configuration.' >&2
        python3 install.py --uninstall || echo 'Automatic configuration restore failed; inspect the saved state file.' >&2
        systemctl --user daemon-reload || true
        if [[ $was_enabled == false ]]; then systemctl --user disable dms.service || true; fi
        if [[ $was_active == true ]]; then
            systemctl --user restart dms.service || true
        else
            systemctl --user stop dms.service || true
        fi
    fi
    exit "$result"
}
trap rollback ERR
if [[ ! -f $state ]]; then
    python3 install.py --check
    python3 install.py
    fresh_install=true
else
    echo 'Keeping the existing rain installation and its original backup.'
fi
systemctl --user daemon-reload
systemctl --user enable dms.service
systemctl --user restart dms.service
systemctl --user is-active --quiet dms.service
sleep 2
dms ipc call lock isLocked >/dev/null
printf '\nSetup complete. Lock with: dms ipc call lock lock\nRain starts 60 seconds after the DMS lock.\n'
echo 'Existing shortcuts that run hyprlock still use hyprlock; use the DMS lock command for rain.'
