#!/bin/bash
# Ventoy starszych wersji wstrzykuje hooki do /lib/dracut/hooks.
# Nowy dracut używa /var/lib/dracut/hooks i /usr/lib/dracut/hooks.
# Fedora ma /lib -> usr/lib: katalogi muszą istnieć przed uruchomieniem /init
# (przed hookami cmdline, a nie dopiero przez skrypt startowy).
check() {
    return 255
}

depends() {
    echo dmsquash-live
}

install() {
    local base hook
    for base in /usr/lib/dracut/hooks /var/lib/dracut/hooks; do
        for hook in cmdline pre-udev pre-trigger initqueue initqueue/finished \
                    initqueue/settled initqueue/timeout pre-mount mount pre-pivot cleanup; do
            inst_dir "$base/$hook"
        done
    done
}
