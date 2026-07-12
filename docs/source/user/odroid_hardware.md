(target_odroid_wiring)=
# Odroid-C4 Hardware Setup

This page covers the physical bench setup: how the serial console is wired to the board, and how the
board's power is switched. Get this right before you try to [boot anything](target_booting_assumptions) —
every mistake on this page produces a symptom that looks like a software problem.

## The two USB devices

| Role | Adapter we use | Chip | USB ID | Baud |
|---|---|---|---|---|
| Serial console | DTECH USB-to-TTL Serial Adapter | **PL2303** | `067b:2303` | **115200** 8N1 |
| USB power relay | LCUS-1 5V USB Relay Module | **CH340** | `1a86:7523` | **9600** 8N1 |

```{attention}
Always identify these by **chip**, never by `/dev/ttyUSB` number — the numbering changes across replug.
See [Identify the USB devices by chip](target_odroid_identify_devices) for the udev rule that gives them
stable names.
```

## Serial console wiring

The serial adapter connects to the Odroid-C4's **40-pin GPIO header**. Three leads, and only three:

| Signal | Adapter pin | Odroid-C4 40-pin header |
|---|---|---|
| Ground | GND | **pin 6** (GND) |
| Board → host | **RX** | **pin 8** (TXD) |
| Host → board | **TX** | **pin 10** (RXD) |
| Power | VCC | **leave disconnected** |

Three rules, each of which has a distinct failure signature:

- **TX and RX are crossed.** The adapter's **TX goes to the board's RX** (pin 10), and the adapter's
  **RX goes to the board's TX** (pin 8). Wiring them straight-through gives you **complete silence** —
  no output at all. That is a *different* symptom from
  [garbled output](target_odroid_garbled_serial); if you are seeing garbage, your TX/RX are fine and you
  have a different problem.
- **Common ground is mandatory.** The adapter's GND must go to the board's GND (pin 6). Without a shared
  reference the two ends disagree about what a logic level is, and you get intermittent nonsense.
- **3.3 V logic only.** The Odroid-C4's UART pins are **3.3 V**. Do **not** use a 5 V TTL adapter — it
  can damage the SoC.

**Leave the adapter's VCC lead disconnected.** The board is powered from its own supply through the
relay, not from the serial adapter. Back-feeding 5 V into the board over the serial header while it is
also powered from the barrel jack is a good way to get confusing behaviour.

```{note}
Pin numbering on the 40-pin header is the usual convention: pin 1 is the corner pin nearest the board
edge, odd pins in one row and even pins in the other. Cross-check against the
[HardKernel Odroid-C4 pinout](https://wiki.odroid.com/odroid-c4/hardware/expansion_connectors) if you
are unsure — a mis-count of one pin is the most common wiring error.
```

## Power path

```
5 V / 4 A supply  ──▶  CH340 USB relay  ──▶  Odroid-C4 power in
```

The relay lets a script power-cycle the board unattended, which is what makes the automated
[benchmark campaign](target_hw_benchmarking) possible. Control it at **9600 baud** with two 4-byte
commands:

```bash
printf '\xa0\x01\x01\xa2' > /dev/odroid-relay   # ON
printf '\xa0\x01\x00\xa1' > /dev/odroid-relay   # OFF
```

```{attention}
**The power relay is a suspect whenever serial output is garbled.** A relay that cannot deliver the
board's peak current will brown the board out as soon as u-boot spins up the CPU and initialises DDR,
and the symptom is corrupted serial that *gets worse as the boot proceeds* — not a wiring or baud
problem at all. If you hit this, bypass the relay and power the board directly from the supply to
confirm. The full differential diagnosis is in
[Serial port continuously prints garbage](target_odroid_garbled_serial).
```

## Network

The board TFTP-boots from the host over a **wired** link with **static** addresses on both ends — there
is no DHCP server on the bench network. Host is `10.42.0.1/24`, board is `10.42.0.2/24`. See
[Host Setup](target_odroid_host_setup).
