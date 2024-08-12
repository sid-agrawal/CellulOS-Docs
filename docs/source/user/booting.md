# Booting the System
Once you have completed the setup steps outlined in the [README](https://github.com/sid-agrawal/OSmosis), you can start running CellulOS.
You should have created a build folder either for Qemu or Odroid-C4, depending on how you want to run the system.

You most likely want to run a particular test or a suite of tests (pre-written tests [listed here](target_system_tests)).
- From your build folder, run `ccmake .`
- Modify the `LibSel4TestPrinterRegex` option to match the test(s) you intend to run.
- If you are running any [CellulOS tests](target_system_test_types), then you must also enable the [GPIServerEnabled](target_configuration_options) option.

After modifying the settings, build the image with `ninja`.

## Booting on Qemu
From the Qemu build folder, booting is as simple as `./simulate`!
Exit using `ctrl-a-x`.

For instructions on using GDB with Qemu, see [debugging](target_debugging_gdb).

(target_booting_assumptions)=
## Booting on Odroid-C4
Assumptions:
- The host computer is running Linux.
- The Odroid's UART is connected to `/dev/ttyUSB0` using a USB to TTL Serial Adapter.
    - You can inspect the connected devices with `sudo dmesg | grep tty`.
    - We use the `DTECH USB to TTL Serial Adapter with PL2303TA`.
- You have a USB smart switch connected to `/dev/ttyUSB1`.
    - We use the `LCUS-1 5V USB Relay Module CH340 USB Control Switch`.

### Initial Setup
```{attention}
Add instructions to setup tftpboot and DNS server.
```

### Running an image
1. Copy the built image from the build folder to the tftpboot folder: 
```
cp <odroid_build_folder>/images/sel4test-driver-image-arm-odroidc4 /srv/tftp/image
```

2. Access the serial console:
```
sudo picocom -b 115200 -f n  /dev/ttyUSB0
````
3. Open a new terminal window and power-cycle the machine:
```
sudo su

echo -en '\xa0\x01\x00\xa1' > /dev/ttyUSB1 # Power off
echo -en '\xa0\x01\x00\xa1' > /dev/ttyUSB1 # Second try may be required

echo -en '\xa0\x01\x01\xa2' > /dev/ttyUSB1 # Power on
echo -en '\xa0\x01\x01\xa2' > /dev/ttyUSB1 # Second try
```
3. Wait for uboot to be ready for input (indicated by `=>`), then load the image with tftpboot: 
```
tftpboot 0x20000000 <host_ip>:image; go 0x20000000
```

- Replace `<host_ip>` with the host machine's IP address, for `lindt` it is `10.42.0.1`. 

<br />

You may find these bash aliases convenient:
```
alias picocom0="sudo picocom -b 115200 -f n  /dev/ttyUSB0"
alias picocom1="sudo picocom -b 115200 -f n  /dev/ttyUSB1"
alias off0="echo -en '\xa0\x01\x00\xa1' | sudo tee /dev/ttyUSB0 > /dev/null"
alias off1="echo -en '\xa0\x01\x00\xa1' | sudo tee /dev/ttyUSB1 > /dev/null"
alias on0="echo -en '\xa0\x01\x01\xa2' | sudo tee /dev/ttyUSB0 > /dev/null"
alias on1="echo -en '\xa0\x01\x01\xa2' | sudo tee /dev/ttyUSB1 > /dev/null"
```
- The USB devices may switch places after a reboot of the host machine, so both versions of the commands are included.

### Troubleshooting

#### Serial port continuously prints garbage

1. Try to connect and disconnect the USB cables (serial and power).
2. If 1 doesn’t help, try [booting Linux on the board](https://wiki.odroid.com/getting_started/os_installation_guide#tab__odroid-c4hc4) with another SD card, then return to the UBoot SD card.