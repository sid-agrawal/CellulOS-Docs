(target_odroid_kvm)=
# Linux and KVM on the Odroid-C4

CellulOS has [two VMM implementations](target_virtual_machine_monitor), and a natural question is how
they compare against a *real* hypervisor on the same silicon. That means running **Linux with KVM** on
the Odroid-C4.

You cannot do this with HardKernel's stock image. This page explains why — there are two independent
blockers, and the second one is subtle enough that fixing only the first leaves you stuck — and gives the
rebuild that works.

## Why the stock image cannot run KVM

**Blocker 1: `CONFIG_KVM` is off.** HardKernel's Ubuntu 22.04 image ships a **Linux 4.9 BSP kernel**
with `CONFIG_KVM` disabled. There is no `/dev/kvm`. This is true even though the CPUs *do* start at EL2,
so the hardware is perfectly capable — it is purely a kernel config decision.

**Blocker 2: the device tree hides half the GIC.** This is the one that will waste your afternoon. Even
after you turn `CONFIG_KVM` on, the vendor kernel still cannot run KVM, because its device tree declares
only **GICD** and a **truncated GICC** — it omits **GICH** (hypervisor control) and **GICV** (virtual CPU
interface) entirely.

KVM's vGICv2 needs all four regions. Without GICH and GICV in the DT it has no way to inject virtual
interrupts, so it refuses to initialise regardless of the config flag.

## The fix

Rebuild the vendor kernel with KVM enabled *and* a corrected GIC node.

### 1. Get the source

```bash
git clone --depth 1 --branch odroidg12-4.9.y https://github.com/hardkernel/linux.git
# 4.9.337
```

### 2. Enable KVM

```
CONFIG_KVM=y
CONFIG_KVM_ARM_HOST=y
```

### 3. Patch the device tree

In `arch/arm64/boot/dts/amlogic/mesonsm1.dtsi`, the `gic` node must claim `arm,gic-400` and declare all
four regions:

| Region | Base | Size |
|---|---|---|
| GICD (distributor) | `0xffc01000` | `0x1000` |
| GICC (CPU interface) | `0xffc02000` | `0x2000` |
| GICH (hypervisor control) | `0xffc04000` | `0x2000` |
| GICV (virtual CPU interface) | `0xffc06000` | `0x2000` |

Note that GICC is also **widened from `0x0100` to `0x2000`**, matching mainline
`meson-g12-common.dtsi`. The resulting node:

```dts
gic: interrupt-controller@2c001000 {
        compatible = "arm,gic-400", "arm,cortex-a15-gic", "arm,cortex-a9-gic";
        ...
        reg = <0x0 0xffc01000 0 0x1000>,   /* GICD */
              <0x0 0xffc02000 0 0x2000>,   /* GICC */
              <0x0 0xffc04000 0 0x2000>,   /* GICH */
              <0x0 0xffc06000 0 0x2000>;   /* GICV */
};
```

The patch is saved in the OSmosis repo at
`scripts/odroid-c4-bench/odroid-c4-kvm-gic.patch`.

### 4. Cross-compile with gcc-11

```{attention}
Use **gcc-11**. A 4.9 kernel tree is far too old for gcc-13 and the build will fail with errors that have
nothing to do with anything you changed.
```

```bash
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC=aarch64-linux-gnu-gcc-11 -j$(nproc) Image.gz dtbs
```

### 5. Install

Copy the resulting **`Image.gz`** and the **patched dtb** into the board's FAT boot partition, mounted at
**`/media/boot`**.

```{attention}
**Back up the originals first.** `/media/boot` holds the only copy on the card, and a bad kernel there
means re-flashing the SD.
```

### 6. Confirm it worked

On the next boot, `dmesg` should show:

```
kvm: Hyp mode initialized successfully
kvm: vgic-v2@ffc04000
```

and `/dev/kvm` should exist. The `vgic-v2@ffc04000` line is the direct payoff from the DT patch — that
address is GICH, which the stock tree never declared.

## Board Linux practicalities

Small things, each of which cost us time:

- **Login is `root` / `odroid`.**

- **There is no DHCP on the wired link** — the host side is a static `10.42.0.1/24` (see
  [Host Setup](target_odroid_host_setup)). Give the board a static `10.42.0.2/24` and persist it with
  `systemd-networkd`:

  ```ini
  # /etc/systemd/network/10-wired.network
  [Match]
  Name=eth0

  [Network]
  Address=10.42.0.2/24
  Gateway=10.42.0.1
  ```
  ```bash
  systemctl enable --now systemd-networkd
  ```

- **The C4 has no RTC.** Its clock is years off after every power cycle, and `apt` consequently rejects
  the repository release files ("Release file is not yet valid"). Set the date before touching `apt`:

  ```bash
  date -s "2026-07-11 12:00:00"     # or use timedatectl/NTP once networking is up
  ```

- **Before networking exists**, drive the board over the serial console with
  `scripts/odroid-c4-bench/serial_shell.py`, which handles the login prompt and returns command output.
