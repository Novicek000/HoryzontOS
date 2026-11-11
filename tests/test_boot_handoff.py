import os
import pathlib
import subprocess
import tempfile
import time

helper = pathlib.Path(__file__).resolve().parents[1] / 'share/libexec/stop-plymouth'
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp)
    scripts = {
        'timeout': '#!/bin/bash\nshift; shift\nexec /usr/bin/timeout --kill-after=0.05s 0.1s "$@"\n',
        'sleep': '#!/bin/bash\nexec /bin/sleep 0.01\n',
        'pkill': '#!/bin/bash\necho "$*" >> "$CALLS"\nif [ "$1" = -TERM ] && [ "$MODE" != stubborn ]; then touch "$STOPPED"; fi\n',
        'plymouth': '''#!/bin/bash
echo "$*" >> "$CALLS"
case "$1" in
  --ping)
    [ "$MODE" = absent ] && exit 1
    [ -f "$STOPPED" ] && exit 1
    [ "$MODE" = ping_hung ] && exec /bin/sleep 30
    exit 0;;
  quit)
    [ "$MODE" = normal ] && { touch "$STOPPED"; exit 0; }
    exec /bin/sleep 30;;
esac
''',
    }
    for name, content in scripts.items():
        (p / name).write_text(content)
        (p / name).chmod(0o755)
    for mode in ['absent', 'normal', 'hung', 'stubborn', 'ping_hung']:
        calls, stopped = p / 'calls', p / 'stopped'
        calls.unlink(missing_ok=True)
        stopped.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f'{p}:/usr/bin:/bin', MODE=mode, CALLS=str(calls), STOPPED=str(stopped))
        start = time.monotonic()
        r = subprocess.run(['bash', str(helper)], env=env, capture_output=True, text=True, timeout=5)
        log = calls.read_text()
        assert r.returncode == 0, (mode, r.stderr)
        assert '--wait' not in log
        if mode == 'absent':
            assert 'quit' not in log
        elif mode == 'normal':
            assert 'quit' in log and '-TERM' not in log
        else:
            assert '-TERM -x plymouthd' in log, (mode, log)
            if mode == 'stubborn':
                assert '-KILL -x plymouthd' in log, (mode, log)
        print(f'{mode}: PASS ({time.monotonic() - start:.2f}s)')
