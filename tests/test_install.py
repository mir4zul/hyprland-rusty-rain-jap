import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/usr/share/quickshell/dms')

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name)
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.config))

    def run_installer(self, *args):
        return subprocess.run(['python3', str(ROOT/'install.py'), *args], env=self.env, capture_output=True, text=True)

    def test_check_writes_nothing(self):
        self.assertEqual(self.run_installer('--check').returncode, 0)
        self.assertEqual(list(self.config.iterdir()), [])

    def test_unsupported_source_preserves_config(self):
        source = self.config/'bad/Modules/Lock'
        source.mkdir(parents=True)
        (source/'LockSurface.qml').write_text('unsupported')
        self.assertNotEqual(self.run_installer('--source', str(self.config/'bad')).returncode, 0)
        self.assertFalse((self.config/'dms-live-rain-state.json').exists())
        self.assertFalse((self.config/'quickshell').exists())

    def test_roundtrip_preserves_user_config_and_edits(self):
        old = self.config/'quickshell/dms'
        old.mkdir(parents=True)
        (old/'sentinel').write_text('original')
        settings = self.config/'DankMaterialShell/settings.json'
        settings.parent.mkdir()
        settings.write_text(json.dumps({'unrelated': 12, 'acPostLockMonitorTimeout': 15}))
        self.assertEqual(self.run_installer().returncode, 0)
        surface=(old/'Modules/Lock/LockSurface.qml').read_text()
        self.assertIn('interval: 60000', surface)
        self.assertIn('rainDelay.stop();', surface)
        state=(self.config/'dms-live-rain-state.json').read_bytes()
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertEqual((self.config/'dms-live-rain-state.json').read_bytes(),state)
        data=json.loads(settings.read_text())
        data['batteryPostLockMonitorTimeout']=99
        settings.write_text(json.dumps(data))
        self.assertEqual(self.run_installer('--uninstall').returncode, 0)
        self.assertEqual((old/'sentinel').read_text(),'original')
        self.assertEqual(json.loads(settings.read_text()), {'unrelated':12,'acPostLockMonitorTimeout':15,'batteryPostLockMonitorTimeout':99})

    def test_copy_failure_leaves_previous_config(self):
        source=self.config/'source/Modules/Lock'
        source.mkdir(parents=True)
        (source/'LockSurface.qml').write_bytes((SOURCE/'Modules/Lock/LockSurface.qml').read_bytes())
        os.mkfifo(self.config/'source/cannot-copy')
        old=self.config/'quickshell/dms'
        old.mkdir(parents=True)
        (old/'sentinel').write_text('original')
        self.assertNotEqual(self.run_installer('--source',str(self.config/'source')).returncode,0)
        self.assertEqual((old/'sentinel').read_text(),'original')
        self.assertFalse((self.config/'dms-live-rain-state.json').exists())

    def test_activation_failure_rolls_back(self):
        mock = self.config/'bin'
        mock.mkdir()
        log = self.config/'service.log'
        programs = {
            'pacman': '#!/bin/sh\nexit 0\n',
            'qs': '#!/bin/sh\nexit 0\n',
            'dms': '#!/bin/sh\necho false\n',
            'systemctl': '#!/bin/sh\necho "$*" >> "$TEST_SERVICE_LOG"\ncase "$*" in\n *"is-active graphical-session.target"*) exit 0;;\n *"is-active"*|*"is-enabled"*) exit 1;;\n *"restart"*) exit 1;;\n *) exit 0;;\nesac\n'
        }
        for name, body in programs.items():
            path=mock/name
            path.write_text(body)
            path.chmod(0o755)
        env=dict(self.env, PATH=str(mock)+':'+os.environ['PATH'],
                 HYPRLAND_INSTANCE_SIGNATURE='test-session', TEST_SERVICE_LOG=str(log))
        result=subprocess.run(['bash',str(ROOT/'setup.sh')],env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Activation failed',result.stderr)
        self.assertFalse((self.config/'dms-live-rain-state.json').exists())
        self.assertFalse((self.config/'quickshell/dms').exists())
        self.assertIn('disable dms.service',log.read_text())
        self.assertIn('stop dms.service',log.read_text())

if __name__ == '__main__':
    unittest.main()
