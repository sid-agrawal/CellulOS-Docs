(target_hw_benchmarking)=
# Benchmarking on Real Hardware

Numbers measured under Qemu and numbers measured on an Odroid-C4 are not the same kind of object, and a
measurement harness that is correct under Qemu can be quietly, badly wrong on the board. This page is the
list of things that bit us while producing the startup measurements (process spawn and Linux-guest boot,
tracked vs untracked), and what to do instead.

If you are looking for the `sel4bench`/nanobench harness and its `benchmarks.csv` output, that is a
different tool — see [Benchmarking](target_benchmarking).

## Audit for serial I/O inside timed regions

```{attention}
**This is the single most important thing on this page.** Under Qemu the UART is effectively
instantaneous, so a stray `printf` inside a timed region costs nothing and you will never notice it. On
real hardware, **every line blocks on the 115200-baud UART for roughly 6–8 ms**. A debug print you forgot
about does not perturb your measurement — it *becomes* your measurement.

Before you trust any number measured on the board, audit the timed path for prints.
```

Two separate instances of this bug made the tracked configuration look far slower than it actually is.
Both are **fixed on the `cellulos` branch**, but they are worth understanding because the bug class will
recur.

### 1. `PD_CREATION_DBG` — `#define X 0` tested with `#ifdef`

`libsel4gpi/include/sel4gpi/pd_creation.h` contained:

```c
#define PD_CREATION_DBG 0
...
#ifdef PD_CREATION_DBG      /* WRONG: true for *any* definition, including 0 */
```

`#ifdef` asks whether the macro is *defined*, not whether it is *true*. Defining it to `0` — the
idiomatic way to say "off" — left it **on**. Sixteen debug `printf`s were therefore always compiled in,
and they fired **inside the timed region** of the tracked PD-spawn path.

The effect on the numbers was not subtle:

| | Tracked process spawn | Overhead vs untracked |
|---|---|---|
| With the stray prints | **70.9 ms** | **+756 %** |
| With them gone | **10.2 ms** | **+25.1 %** |

The header now uses `#if PD_CREATION_DBG`. To sweep for the same bug elsewhere:

```bash
grep -rn '#ifdef .*_DBG' projects/sel4-gpi/
```

Any hit that is paired with a `#define ... 0` is always-on.

### 2. `pd_client_dump()` inside VM creation

`apps/vmm/src/osm-vmm/vmm.c` called `pd_client_dump()` unconditionally while creating a guest. That
prints **a CSV row per model node and edge — around 220 lines** — from inside the timed VM-creation
phase. At 6–8 ms a line, that is well over a second of pure UART time attributed to VM creation.

It is now gated behind `GPI_EXTRACT_MODEL`, i.e. the `GPIExtractModel` CMake option. **Build your
benchmark images with `-DGPIExtractModel=OFF`.**

## Wall-clock source: use `CNTPCT_EL0`

- Read the ARM physical counter **`CNTPCT_EL0`**. This requires **`KernelArmExportPCNTUser=ON`** so that
  user level may read it.
- Do **not** use `CNTVCT_EL0`. The **virtual counter traps** unless it is explicitly exported; keep
  `KernelArmExportVCNTUser=OFF` and stay off it.
- The counter runs at approximately **1 GHz** on the C4, but **read `CNTFRQ_EL0` rather than hardcoding
  it** and convert ticks → milliseconds with that.

Reading `CNTPCT_EL0` is what lets you sanity-check a measured interval against a stopwatch, which is how
we caught the debug-print inflation above: 70.9 ms of "PD creation" is not a plausible amount of work,
and the counter agreed with the wall clock, so the time was real — it was just being spent in the UART.

## Timestamp VM boot phases on the HOST, not in the guest

```{attention}
The guest's own `printk` timestamps **cannot see host-side stalls**, and they look authoritative enough
that you will believe them.
```

Measuring the Linux-guest boot from inside the guest, the `Run /init` line appears at:

- **[1.044]** untracked
- **[1.064]** tracked

— a difference of about **2 %**, which would suggest the tracked VMM costs essentially nothing. The
**true host-side gap for that phase was about 2 seconds**.

The guest's clock only advances when the guest is running. Any time the host spends — in the VMM, in the
GPI server, blocked on the UART — is simply invisible to it. The guest cannot measure its own suspension.

**Always derive VM boot phase timings from host-side timestamps**: timestamp each line as it arrives at
the host on the serial console, and take your phase boundaries from those. That is what
`campaign.py` does.

## Automation: `scripts/odroid-c4-bench/`

The startup campaign is automated end-to-end in the OSmosis repo under `scripts/odroid-c4-bench/`.

### `campaign.py`

Runs an unattended measurement campaign: **relay power-cycle → interrupt u-boot → `tftpboot` → boot →
capture the console with a host-side timestamp on every line**, per configuration, for N iterations.

Its `CONFIGS` map is the canonical encoding of the measurement points:

| Config | Tests | Done regex |
|---|---|---|
| `process` | `GPIBM003` (untracked spawn) + `GPIBM004` (tracked spawn) | `All is well in the universe` |
| `vm-untracked` | `GPIVM002` (Linux guest, `sel4test-vmm`) | `buildroot login:` |
| `vm-tracked` | `GPIVM004` (Linux guest, `osm-vmm`) | `buildroot login:` |

It expects the corresponding prebuilt images to be present in `/srv/tftp` as `image`, `vm-untracked` and
`vm-tracked`, and it uses the host/board addresses `10.42.0.1` / `10.42.0.2`.

### `serial_shell.py`

Drives a root shell on the board's Linux over the serial console (log in, run a command, return the
output). This is how you bootstrap the board before it has any networking — see
[Linux and KVM on the Odroid-C4](target_odroid_kvm).

```{note}
These scripts currently hardcode `RELAY = /dev/ttyUSB0` and `CONSOLE = /dev/ttyUSB1`. That mapping is
**not stable** and may well be the reverse on your host. Install the udev rule from
[Identify the USB devices by chip](target_odroid_identify_devices) and point the scripts at
`/dev/odroid-relay` and `/dev/odroid-console` instead.
```
