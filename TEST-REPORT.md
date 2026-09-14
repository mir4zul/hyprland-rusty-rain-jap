# Verification — 2026-09-14

Environment: existing Arch Linux installation, DMS 1.5.3, Quickshell git 0.3.1. Tests use temporary configuration directories; the active desktop configuration was not changed by this test run.

Passed five automated tests (`python3 -m unittest discover -s tests -v`):

- Compatibility preflight writes no configuration.
- Unsupported DMS source is rejected without installation.
- Install/uninstall restores an existing user DMS directory and original settings, preserves subsequent user edits, and rejects duplicate installation without overwriting its backup.
- Injected file-copy failure preserves the previous configuration.
- Simulated DMS activation failure rolls back the fresh rain install and restores inactive/disabled service state. Service commands are mocked in this test; this is not a real desktop failure test.

Also passed Bash syntax validation and local dependency preflight (no missing packages).

Fixed during verification: missing settings are removed on uninstall instead of becoming null; the DMS copy is staged before moving existing configuration; failed installation restores configuration; fresh-install activation failure triggers rollback. Package installations/system upgrades are not rolled back.

Not verified: clean-machine pacman installation; graphical VM boot; real 60-second lock-to-rain timing and password unlock; other DMS versions, distributions, GPUs or multi-monitor layouts. This environment has no qemu-system-x86_64, virt-install or /dev/kvm. Docker is installed but a container would not establish graphical lock-screen compatibility.

Automatic dependency support remains Arch-based only. No claim of universal compatibility is made.
