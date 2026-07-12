# Booting the System
Once you have completed the setup steps outlined in the [README](https://github.com/sid-agrawal/OSmosis), you can start running CellulOS.
You should have created a build folder either for Qemu or Odroid-C4, depending on how you want to run the system.

You most likely want to run a particular test or a suite of tests (pre-written tests [listed here](target_system_tests)).
- From your build folder, run `ccmake .`
- Modify the `LibSel4TestPrinterRegex` option to match the test(s) you intend to run.
- If you are running any [CellulOS tests](target_system_test_types), then you must also enable the [GPIServerEnabled](target_configuration_options) option.

After modifying the settings, build the image with `ninja`.

```{tip}
`ccmake` is interactive, which is fine for a one-off but useless in a script. The equivalent
non-interactive form, which is what all our scripts and the benchmark campaign use, is:
`cmake -S $gpi -B $build -DLibSel4TestPrinterRegex=<Test>` where `$gpi` and `$build` are the paths to
`projects/sel4-gpi` and the build directory. See the [Odroid-C4 build recipe](target_odroid_build) below.
```

## Booting on Qemu
From the Qemu build folder, booting is as simple as `./simulate`!
Exit using `ctrl-a-x`.

For instructions on using GDB with Qemu, see [debugging](target_debugging_gdb).

(target_booting_assumptions)=
## Booting on Odroid-C4

Assumptions:
- The host computer is running Linux.
- The Odroid-C4's UART is wired to a **3.3 V** USB-to-TTL serial adapter, and the board's power is
  switched by a **USB relay module**. If you are wiring the board up for the first time, read
  [Odroid-C4 Hardware Setup](target_odroid_wiring) first — the serial leads are crossed and a missing
  common ground is silent.
- The host serves boot images over TFTP and both host and board have **static IPs** (there is no DHCP
  server on the bench network). See [Host Setup](target_odroid_host_setup) below.

(target_odroid_identify_devices)=
### Identify the USB devices by chip, not by port number

```{attention}
Do **not** assume `/dev/ttyUSB0` is the console and `/dev/ttyUSB1` is the relay, or vice versa.
The `ttyUSB*` numbering is assigned in enumeration order and **changes across replug and host reboot**.
Getting this backwards means you send relay power bytes to the console adapter (nothing happens, and you
conclude the relay is dead) or open a 115200 terminal on the relay (nothing happens, and you conclude
the board is dead). Both cost hours.
```

Identify each adapter by its **USB chip ID** instead. The two devices are different chips, so this is
unambiguous:

| Role | Adapter we use | Chip | USB ID | Baud |
|---|---|---|---|---|
| Serial console | DTECH USB-to-TTL Serial Adapter | **PL2303** | `067b:2303` | **115200** 8N1 |
| USB power relay | LCUS-1 5V USB Relay Module | **CH340** | `1a86:7523` | **9600** 8N1 |

```bash
lsusb | grep -iE '067b:2303|1a86:7523'

# Resolve each chip to whichever /dev/ttyUSB* node it landed on this time:
for d in /sys/class/tty/ttyUSB*; do
  dev=$(basename "$d")
  ids=$(udevadm info -q property -n "/dev/$dev" \
        | grep -E '^ID_VENDOR_ID=|^ID_MODEL_ID=' | cut -d= -f2 | paste -sd:)
  case "$ids" in
    067b:2303) echo "CONSOLE (PL2303) = /dev/$dev" ;;
    1a86:7523) echo "RELAY   (CH340)  = /dev/$dev" ;;
  esac
done
```

The durable fix is a udev rule that gives each device a stable symlink, so nothing has to guess again:

```
# /etc/udev/rules.d/99-odroid-bench.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", SYMLINK+="odroid-console", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="odroid-relay",   MODE="0666"
```

```bash
sudo udevadm control --reload && sudo udevadm trigger
ls -l /dev/odroid-console /dev/odroid-relay
```

Adding yourself to the `dialout` group (`sudo usermod -aG dialout $USER`, then log out and back in)
removes the need for `sudo` on the serial devices entirely.

These aliases are then unambiguous:

```bash
# Console: PL2303, 115200 8N1, no flow control.
alias board-console="picocom -b 115200 -f n /dev/odroid-console"

# Relay: CH340, 9600 8N1.  Command bytes: ON = A0 01 01 A2 , OFF = A0 01 00 A1
alias board-on="printf  '\xa0\x01\x01\xa2' > /dev/odroid-relay"
alias board-off="printf '\xa0\x01\x00\xa1' > /dev/odroid-relay"
```

```{note}
The relay sometimes drops the first byte sequence after it is plugged in; sending the command a second
time is harmless (it is idempotent) and is what our scripts do.
```

(target_odroid_host_setup)=
### Host Setup: TFTP and static IPs

u-boot fetches the image over TFTP. There is **no DHCP and no DNS** involved — both ends get static
addresses. Our convention, used by every script in `scripts/odroid-c4-bench/`, is **host `10.42.0.1`,
board `10.42.0.2`, images served from `/srv/tftp`**.

```bash
sudo apt install tftpd-hpa

# /etc/default/tftpd-hpa
#   TFTP_USERNAME="tftp"
#   TFTP_DIRECTORY="/srv/tftp"
#   TFTP_ADDRESS=":69"
#   TFTP_OPTIONS="--secure"
sudo systemctl restart tftpd-hpa

# Static IP on the wired interface facing the board:
sudo ip addr add 10.42.0.1/24 dev <wired-iface>
sudo ip link set <wired-iface> up
```

(target_odroid_build)=
### Building an image for the Odroid-C4

```bash
mkdir odroid-build && cd odroid-build
../init-build.sh -DPLATFORM=odroidc4 \
  -DLibSel4TestPrinterRegex=GPIBM004 \
  -DGPIServerEnabled=ON \
  -DGPIVMMImplementation=osm-vmm
ninja
```

The flags that matter when building a measurement image:

| Flag | Meaning |
|---|---|
| `-DPLATFORM=odroidc4` | Target the board rather than Qemu. |
| `-DLibSel4TestPrinterRegex=<regex>` | Which test(s) to run. |
| `-DGPIServerEnabled=ON\|OFF` | Run the [GPI server](target_glossary_gpi_server); required for any `OSM` (tracked) test. |
| `-DGPIExtractModel=ON\|OFF` | Dump the OSmosis model state during tests. **Leave `OFF` when benchmarking** — see [benchmarking on hardware](target_hw_benchmarking). |
| `-DGPIVMMImplementation=osm-vmm\|sel4test-vmm` | Selects the **tracked** vs **untracked** VMM. Only one can be compiled at a time. |

The four configurations behind the startup measurements:

| Test | What it measures | `GPIServerEnabled` | `GPIVMMImplementation` |
|---|---|---|---|
| `GPIBM003` | process spawn, **untracked** (sel4utils) | `OFF` | n/a |
| `GPIBM004` | process spawn, **tracked** (osm) | `ON` | n/a |
| `GPIVM002` | Linux guest boot, **untracked** | `OFF` | `sel4test-vmm` |
| `GPIVM004` | Linux guest boot, **tracked** | `ON` | `osm-vmm` |

```{attention}
Building the VMM for `odroidc4` fails out of the box: `apps/vmm/board/odroidc4/rootfs.cpio.gz` is
gitignored and therefore absent from a fresh clone. See
{doc}`the VMM page </development/virtual_machine_monitor>` for the one-line workaround.
```

### Running an image

1. Copy the built image from the build folder to the TFTP folder:
   ```bash
   cp <odroid_build_folder>/images/sel4test-driver-image-arm-odroidc4 /srv/tftp/image
   ```
   You can keep several prebuilt images in `/srv/tftp` under different names and pick between them at
   the u-boot prompt; `scripts/odroid-c4-bench/campaign.py` expects `image`, `vm-untracked` and
   `vm-tracked`.

2. Attach to the serial console **first**:
   ```bash
   picocom -b 115200 -f n /dev/odroid-console
   ```
   The u-boot autoboot window is only about **2 seconds**. If you power the board on before you are
   attached, you will miss it and the board will boot whatever is on the SD card.

3. In a second terminal, power-cycle the board with the relay:
   ```bash
   printf '\xa0\x01\x00\xa1' > /dev/odroid-relay   # power off
   sleep 1
   printf '\xa0\x01\x01\xa2' > /dev/odroid-relay   # power on
   ```

4. Interrupt the autoboot as soon as output appears. **Which prompt you get depends on which SD card is
   in the slot** — there are two entirely different u-boots in circulation:

   | SD card | u-boot | Prompt | Autoboot window | Interrupt with |
   |---|---|---|---|---|
   | seL4 / CellulOS card | mainline **u-boot 2023.07** | `=>` | ~2 s | **Enter** |
   | HardKernel Ubuntu card | vendor **u-boot 2015.01** | `odroidc4#` | ~2 s | **Enter**, **space**, or **Ctrl-C** |

5. Set the static IPs, then TFTP the image and jump to it:
   ```
   => setenv ipaddr 10.42.0.2
   => setenv serverip 10.42.0.1
   => tftpboot 0x20000000 image
   => go 0x20000000
   ```

   ```{attention}
   The `ipaddr` / `serverip` lines are **not optional**. Without an IP of its own, u-boot falls into a
   **BOOTP/DHCP retry loop** looking for a server that does not exist on the bench network, and
   `tftpboot` never completes. If the u-boot environment is writable, `saveenv` persists them so you
   only do this once per card.
   ```

### Troubleshooting

(target_odroid_garbled_serial)=
#### Serial port continuously prints garbage

There are two distinct failure modes here and they have **different signatures**. Classify yours before
you start swapping cables — they have completely different fixes.

**Symptom A — garbled uniformly, from the very first byte.**
This is a **baud/framing mismatch**. The corruption is there in the bootROM's first characters and does
not get better or worse as the boot proceeds. Confirm the console is **115200 8N1 with no flow control**
(`picocom -b 115200 -f n`), and confirm you are actually talking to the PL2303 console adapter and not
the CH340 relay (see [above](target_odroid_identify_devices)).

**Symptom B — garbling that gets *worse* as the boot proceeds.**
This is the board **browning out through a failing or underpowered USB power relay**, and it is the one
that cost us the most time. The signature is unmistakable once you look for it:

- The **printable-byte ratio decays across the boot**: roughly **67 % printable** during bootROM/BL2,
  collapsing to **20–30 %** once u-boot brings up the CPU and initialises DDR — i.e. exactly when the
  board's current draw jumps.
- The board **never reaches a usable prompt**.
- **Diagnosis: bypass the relay and power the board directly from the supply.** For us this took the
  console from ~25 % printable to **100 % clean**.

The discriminator worth internalising: **a baud mismatch garbles uniformly; a brownout garbles
progressively, correlated with load.**

To classify your own symptom, capture a boot and watch the printable ratio over time:

```bash
python3 - <<'EOF'
import serial, time
con = serial.Serial('/dev/odroid-console', 115200, timeout=0.2)
t0 = time.time()
while time.time() - t0 < 30:
    b = con.read(512)
    if b:
        ok = sum(32 <= c < 127 or c in (10, 13, 9) for c in b)
        print(f"{time.time()-t0:6.1f}s  printable {100*ok/len(b):5.1f}%")
EOF
```

A ratio that starts around 67 % and falls to ~25 % is Symptom B. (`scripts/odroid-c4-bench/silence_check.py`
and `filtered_tail.py` in the OSmosis repo do the same job.)

If you must power-cycle unattended, use a relay and supply that can actually deliver the board's peak
current, rather than passing board power through a small USB relay module.

**If neither of the above applies**, the older folk remedies are still worth a try — they did work for us
once, before we understood the brownout:

1. Unplug and replug the USB cables (serial and power).
2. [Boot Linux on the board](https://wiki.odroid.com/getting_started/os_installation_guide#tab__odroid-c4hc4)
   from another SD card, then return to the u-boot SD card.
