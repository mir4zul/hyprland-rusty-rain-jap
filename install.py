#!/usr/bin/env python3
"""Install a reversible live rain overlay into a user copy of DMS."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=Path('/usr/share/quickshell/dms'))
parser.add_argument('--uninstall', action='store_true')
parser.add_argument('--check', action='store_true', help='Validate DMS compatibility without writing files')
args = parser.parse_args()
config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
dest = config / 'quickshell/dms'
state = config / 'dms-live-rain-state.json'
settings = config / 'DankMaterialShell/settings.json'
dropin = config / 'systemd/user/dms.service.d/live-rain.conf'
changes = {'lockScreenPowerOffMonitorsOnLock': False, 'acPostLockMonitorTimeout': 0,
           'batteryPostLockMonitorTimeout': 0, 'lockScreenVideoEnabled': False}

if args.uninstall:
    saved = json.loads(state.read_text())
    if dropin.exists():
        dropin.unlink()
    if (dest / '.dms-live-rain').exists():
        dest.rename(dest.with_name('dms-rain-disabled-' + str(time.time_ns())))
    if saved['previous_config']:
        Path(saved['previous_config']).rename(dest)
    data = json.loads(settings.read_text())
    for key, value in saved['settings'].items():
        if data.get(key) == changes[key]:
            if key in saved.get('missing_settings', []):
                data.pop(key, None)
            else:
                data[key] = value
    settings.write_text(json.dumps(data, indent=2) + '\n')
    state.unlink()
    print('Restored settings. Restart DMS while unlocked to activate.')
    raise SystemExit

if dropin.exists() and not state.exists():
    raise SystemExit('Existing live-rain service override; no changes made.')
if state.exists() and not args.check:
    raise SystemExit('Already installed. Uninstall before installing an updated DMS copy.')
source = args.source.resolve()
surface = (source / 'Modules/Lock/LockSurface.qml').read_text()
replacements = [
    ('if (videoScreensaver.active && videoScreensaver.inputEnabled) {',
     'if (liveRain.active) {\n            if (liveRain.inputEnabled) liveRain.dismiss();\n            event.accepted = true;\n            return;\n        }\n        if (videoScreensaver.active && videoScreensaver.inputEnabled) {'),
    ('enabled: !videoScreensaver.active', 'enabled: !videoScreensaver.active && !liveRain.active'),
    ('focus: !videoScreensaver.active', 'focus: !videoScreensaver.active && !liveRain.active'),
    ('opacity: videoScreensaver.active ? 0 : 1', 'opacity: (videoScreensaver.active || liveRain.active) ? 0 : 1'),
    ('    Component.onCompleted: forceActiveFocus()',
     '    Timer {\n        id: rainDelay\n        interval: 60000\n        onTriggered: if (root.isLocked) { liveRain.start(); root.forceActiveFocus(); }\n    }\n\n    LiveRain {\n        id: liveRain\n        anchors.fill: parent\n        onDismissed: Qt.callLater(() => lockContent.focusPasswordField())\n    }\n\n    Component.onCompleted: {\n        forceActiveFocus();\n        if (isLocked) rainDelay.restart();\n    }'),
    ('            if (SettingsData.lockScreenVideoEnabled) {\n                videoScreensaver.start();\n            }',
     '            rainDelay.restart();'),
    ('        lockContent.unlocking = false;',
     '        rainDelay.stop();\n        liveRain.dismiss();\n        lockContent.unlocking = false;')]
for old, new in replacements:
    if surface.count(old) != 1:
        raise SystemExit('Unsupported DMS LockSurface version; no changes made: ' + old)
    surface = surface.replace(old, new)
if args.check:
    print('PASS: DMS LockSurface supports the rain patch.')
    raise SystemExit
data = json.loads(settings.read_text()) if settings.exists() else {}
previous = ''
# Build the complete copy before moving any existing user configuration.
dest.parent.mkdir(parents=True, exist_ok=True)
staging = dest.with_name('dms-rain-staging-' + str(time.time_ns()))
settings_before = settings.read_bytes() if settings.exists() else None
try:
    shutil.copytree(source, staging, symlinks=True)
    (staging / 'Modules/Lock/LockSurface.qml').write_text(surface)
    shutil.copy2(Path(__file__).with_name('LiveRain.qml'), staging / 'Modules/Lock/LiveRain.qml')
    (staging / '.dms-live-rain').write_text('1\n')
except BaseException:
    if staging.exists():
        shutil.rmtree(staging)
    raise
try:
    if dest.exists() or dest.is_symlink():
        previous = str(dest.with_name('dms-before-rain-' + str(time.time_ns())))
        dest.rename(previous)
    staging.rename(dest)
    state.write_text(json.dumps({'previous_config': previous, 'missing_settings': [k for k in changes if k not in data], 'settings': {k: data.get(k) for k in changes}}, indent=2))
    dropin.parent.mkdir(parents=True, exist_ok=True)
    dropin.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/dms -c "' + str(dest) + '" run --session\n')
    data.update(changes)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + '\n')
except BaseException:
    if (dest / '.dms-live-rain').exists():
        shutil.rmtree(dest)
    if previous:
        Path(previous).rename(dest)
    if settings_before is not None:
        settings.write_bytes(settings_before)
    elif settings.exists():
        settings.unlink()
    state.unlink(missing_ok=True)
    dropin.unlink(missing_ok=True)
    if staging.exists():
        shutil.rmtree(staging)
    raise
print(f'Installed live rain in {dest}. Restart DMS while unlocked to activate.')
