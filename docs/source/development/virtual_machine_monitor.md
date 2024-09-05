# The User-Space Virtual Machine Monitor
There are two VMM implementations in *CellulOS*, both ported from seL4's Microkit [libvmm](https://github.com/au-ts/libvmm). 
One implementation uses only seL4 utility libraries present in the [sel4test](https://github.com/seL4/sel4test) project, and the other uses only CellulOS APIs.

## Status of different VMM Implementations


|  guestOS  |  microkit  | non-OSM (sel4utils)  |     OSM     |     QEMU     |
| --------- | ---------- | -------------------- | ----------  | -----------  | 
|   Linux   |    Yes (Odroid and Qemu)     |        Yes (Odroid and Qemu)           |     Yes (Odroid and Qemu)     |  Assumed Yes |
|  baby-VM  |     NA     |        Yes - Qemu, Not fully working on Odroid          |     Yes - Qemu, Not fully working on Odroid      |     Yes      |

## Building the Linux image from scratch
The instructions here are similar to the [libvmm instructions](https://github.com/au-ts/libvmm/blob/main/examples/simple/board/qemu_virt_aarch64/README.md). 

1. Clone the Linux repo: `git clone --depth 1 --branch v5.18 https://github.com/torvalds/linux.git`
2. For the regular build, copy the `linux_config` file from `board/{platform}`, where `platform` is either `qemu_arm_virt` or `odroidc4`: `cp linux_config linux/.config`
    - For the debug build, copy the `linux_debug_config` file instead.
3. Update the `.config` with default values for any missing options: `make ARCH=arm64  CROSS_COMPILE=aarch64-none-elf- olddefconfig`
    - You will be prompted to manually select config values if this step is omitted
4. Build the kernel: `make ARCH=arm64 CROSS_COMPILE=aarch64-none-elf- all -j$(nproc)`
5. The image to give to the CellulOS VMM is at `linux/arch/arm64/boot/Image`. 
    - If compiling the debug version, the image with symbols that can be loaded in GDB is at `linux/vmlinux`.

## Building the Buildroot image from scratch
There has been no change to this process for CellulOS, and we follow the [libvmm instructions](https://github.com/au-ts/libvmm/tree/main/examples/simple/board/qemu_virt_aarch64#buildroot-rootfs-image).

## Source File Organization
The source files for both implementations exist under one parent directory, [sel4-gpi/apps/vmm](https://github.com/sid-agrawal/sel4-gpi/tree/cellulos/apps/vmm) and are further divided between children `sel4test-vmm` and `osm-vmm` directories. Most source files are not implementation specific, and pass around references to a `vm_context_t` struct, which are defined by implementation specific headers. There are a few common file headers, which are under `gpivmm` directories. 

Due to the two implementations sharing many common files, with most functions expecting one implementation of the `vm_context_t` struct, only one set of source files can be built at a time. This is toggled via a CMake config variable: `GPIVMMImplementation`, which can either be: `sel4test-vmm` or `osm-vmm`. See the [CMakeLists.txt](https://github.com/sid-agrawal/sel4-gpi/tree/cellulos/apps/vmm) file for details.

## VM Setup
Currently, only a Linux guest on AARCH64 is supported. The guest is given a 256MB region of RAM, pass-through access to the vGIC CPU interface and serial UART device. Access to the GIC distributor is emulated by the VMM.

### Root Task configurations for sufficient memory
**These workarounds/configurations have already been implemented, but are documented here for future reference.**

The Linux guest image, DTB, and init ramdisk are all embedded in the `sel4test-tests` image's ELF, thus bloating it by a few tens of MBs. Each of these components are embedded as separate ELF sections, with a global variable pointing to the start of each section (see [package_guest_images.S](https://github.com/sid-agrawal/sel4-gpi/tree/cellulos/apps/vmm)). This causes a few issues with ELF loading that *have already been solved*, but are documented here in case they come up again.

#### Root Task CSpace Size
The `sel4test-tests` image is then embedded in the `sel4test-driver`'s  ELF through the `CPIO` archive, (which is just *one* ELF section with everything that has been added to the archive). This is loaded by the early boot `ElfLoader` tool, which loads the ELF using small pages, and thus burning through CSpace slots extremely quick. It is necessary to set the Root Task's initial CNode size to something sufficient (e.g. 17) to allow for storage of these page capabilities. See sel4-gpi's root [CMakeLists.txt](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/CMakeLists.txt) file for where this is set.

#### Root Task Virtual Memory Pool Size
The Root Task's (a.k.a. sel4test's Test Driver) allocator must be set to a virtual memory pool with enough range to be able to allocate ~50MB of untyped in order to load the sel4tests-test's ELF image. See the `ALLOCATOR_VIRTUAL_POOL_SIZE ` variable in [apps/sel4test-driver/src/main.c](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-driver/src/main.c). 

#### Untyped Given to Tests
After the Root Task is bootstrapped, it tries to split some of its untyped memory pool to provide to the sel4tests-test process. If the guest RAM will be allocated from untyped memory (see [QEMU Guest RAM Allocation](target_qemu_guest_ram_alloc) for an example where it is not), ensure that the Root Task provides the sel4tests-test process with sufficient untyped to do so. See the `TEST_UNTYPED_SIZE` variable in [apps/sel4test-driver/src/main.c](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-driver/src/main.c). 

(target_qemu_guest_ram_alloc)=
## QEMU Guest RAM Allocation
By the default QEMU configuration, the Root Task only gets access to approximately 300MB of untyped (non-device) memory. This is not enough to set up the guest, and there are two solutions:

### Increase the amount of memory configured for QEMU
This is not the recommended choice, as there are a couple of variables in different places that need to changed:
1) If you're running QEMU on WSL, the WSL config must be updated to allow it more RAM. 
2) When building the kernel, there are a few platform config files generated that detail physical addresses of various device regions, including untyped RAM ranges. For QEMU, the untyped RAM size can be configured via CMake. See the `QEMU_MEMORY` variable in [config.cmake](https://github.com/sid-agrawal/seL4/blob/2037b75bf29c39d8b1da5e5c5b0bac15086bc95a/src/plat/qemu-arm-virt/config.cmake#L162). The units here are in MB.
3) When running the simulation script, which invokes the `qemu` command, the memory size to give to QEMU's guest (e.g. our CellulOS system) must be passed in using the `-m` argument (the default unit is MB - specify `G` for GB). 
	1) It's definitely possible to mismatch the memory size set here and the one set in the kernel's cmake config file. If the kernel's cmake config value is less than the one given to the simulation script, the system will crash.

### Use the QEMU memory region reserved specifically for guests
See [overlay-reserve-vm-memory.dts](https://github.com/sid-agrawal/seL4/blob/2037b75bf29c39d8b1da5e5c5b0bac15086bc95a/src/plat/qemu-arm-virt/overlay-reserve-vm-memory.dts) for the physical addresses of this region. The Root Task is given capabilities to this region so, it can simply be allocated. 

## Test Process Device Memory Allocation
There is no action required for this section, it is documented due to the behaviour being a bit obscure and easy to miss.

The sel4test Test Driver sets up an RPC channel between itself and all test processes for "backup" memory allocations. Each test process gets its own VKA allocator, that can all send IPC requests back to the Test Driver when it cannot fulfill an allocation request. See the `init_allocator` function in `sel4tests-test` [main.c](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-tests/src/main.c#L121). 

For instance, when a certain device region is allocated in a test process, it makes a silent IPC request to the Task Driver for the region. For device regions that the Test Driver itself tries to set up prior to running tests (e.g. the UART, timer), it caches the device frames it has allocated. Upon receiving an allocation request, it makes a copy of the frame capability to transfer to the test process. See `serial_utspace_alloc_at_fn` in sel4test-driver's [main.c](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-driver/src/main.c#L632). 

## Handling VM Faults and Interrupts
When a PD initializes itself as a VMM, it will use the same endpoint to listen for faults from all guest-PDs that it handles. It creates a fault-handling thread that blocks on this endpoint, and requests for starting new guests are handled by the original thread. 
In both `sel4test` and `osm` VMM implementations, the fault-handling thread's TCB is binded to a notification that is binded to various interrupts. This way, the VMM's fault-handling thread can be unblocked from listening on the fault endpoint when it receives an interrupt. 

### Distinguishing Faults from Interrupts
In order to distinguish faults from interrupts, the highest bit of the endpoint/notification badge is set to indicate that the VMM has been unblocked by an interrupt signal. For faults, the remaining lower bits encode the ID of the guest which is faulting (since the VMM uses the same endpoint to handle faults for ALL guests which it starts). For interrupts, the remaining lower bits encode the interrupt ID.

### Fault Handling
Faults generated by the guest first trap into the seL4 kernel, which then performs an `seL4_Call()` on behalf of the guest, using its fault endpoint. This blocks the guest-PD until it is either explicitly resumed by the VMM, or it receives a reply.
Upon receiving the fault, the VMM handles it and, *in some cases*, manually resumes the guest-PD by increasing the guest's program counter and writing to its TCB registers. *In other cases* (particularly during interrupts), the VMM resumes the guest-PD by performing an `seL4_Reply()`.

An overview of how the guest, VMM, and Kernel interact when handling faults or interrupts is show below:
```{image} ../images/VMM_structure.jpg
    :width: 700px
```

A sequence diagram of the fault handling process is show below:
```{image} ../figures/vmm_faults.png
    :width: 700px
```


### Interrupt Forwarding
Devices that have not been passed-through to the guest will forward interrupts to the seL4 kernel. 

#### VPPIs and VGIC Maintenance Interrupts
*Specifically* for VPPIs (Virtual Private Peripheral Interrupts) and VGIC Maintenance Interrupts, the kernel delivers the interrupt to the VMM as a fault from the guest. A sequence diagram of the interrupt handling process is shown below:
```{image} ../figures/vmm_special_irqs.png
    :width: 700px
```

#### Other types of Interrupts
Interrupts other than VPPIs and VGIC Maintenance Interrupts are signaled through a notification, only if the interrupt handler has been binded to the notification. 

Devices that have been passed through to the guest will directly interrupt the guest without trapping into the VMM. It can still trap into the VMM if it requires intervention from the host. For instance, when the serial UART device is waiting for user-input, this traps into the VMM, as the user interacts with the guest's console through the host.

#### Interrupt Handler Notification for OSmosis PDs
For the OSmosis VMM implementation, the notification bound to the VMM's fault-handler thread's TCB is the same one that is used for {doc}`deadlock avoidance </design/deadlocks>`. OSmosis PDs are automatically allocated an endpoint, and upon assigning a CPU to the PD, the CPU's TCB is binded to the PD's notification. This allows the CPU to be unblocked from listening on any endpoint when the PD's notification is signaled. 
By default, a badged version of the notification is used by the Root Task. For the PD to be able to receive interrupts, the `pd_client_irq_handler_bind()` API call mints another badge on this notification for the interrupt, and binds it to an seL4 IRQ handler.
This currently only allows one interrupt to be handled by a PD at a time.

#### Interrupt Handler Caps
The seL4 interrupt handler cap of a given IRQ ID can be retrieved *only once* throughout the entire system, however it can be copied as many times as needed. To allow multiple PDs (including non-OSmosis ones) to retrieve this cap, the GPI server stores an array of retrieved IRQ handler caps. This array is shared with the sel4test driver thread. OSmosis PDs retrieve these IRQ handler caps through CellulOS API calls, and non-OSmosis PDs contact the sel4test driver through their fault endpoints.

## ARM GIC Distributor and vCPU Interface
The VMM currently gives the guest-PD pass-through to the GIC's virtual CPU interface region. The guest-PD uses this interface to determine whether it has received an interrupt, and to indicate that it has handled any pending interrupts. VGIC Maintenance Interrupts are generated (and trapped to the seL4 kernel, then VMM) in response to the guest-PD activities in the vCPU interace. More information from the ARM manual is [here](https://developer.arm.com/documentation/ihi0048/b/GIC-Support-for-Virtualization?lang=en).

The GIC distributor region is not hardware-virtualized and must be emulated by the VMM for the guest-PD. The guest will try to enable and disable specific interrupts by reading and writing to this region, which will generate page faults. Upon receiving these page faults, the VMM detects that the faulting address is within the GIC distributor region, determines which GIC distributor register is being accessed based on an offset from the base distributor address, and reads/writes the emulated register.

## Known Limitation: OdroidC4 Serial Device Contention 
As CellulOS doesn't handle any page faults, a PD may silently crash when it encounters one. We have added printing within the seL4 kernel when a page fault occurs, to make it more visible for debugging. If in kernel debug mode, when the VMM allows its guest-PDs pass-through to the serial device, it will clobber the kernel's usage of the serial device and vice versa. 

As described in the [](#arm-gic-distributor-and-vcpu-interface) section, the guest-PD will cause page faults when it tries to access the GIC distributor, which then causes the kernel to print a debug message. On the odroid, these debugging kernel prints will clobber something in the guest-PD and prevent it from enabling interrupt forwarding for its hardware timer. This causes an infinite loop of timer interrupts being delivered to the VMM, which will keep getting dropped the guest, since it was previously prevented from enabling the forwarding of the timer interrupt.

To prevent this, we have currently just disabled the page-fault debug prints from within the kernel on the odroid.

## Running the `sel4test` VMM tests
There are four [system tests](target_vmm_tests) for starting a VMM and a guest-PD. The OSmosis VMM runs the VMM and guest-PD as OSmosis PDs, which get cleaned up by the CellulOS cleanup policies, and thus can be run consecutively without issue. The sel4test VMM, however, does not get properly cleaned up by the sel4test driver, and thus will encounter resource allocation issues if ran consecutively.

## OdroidC4 CellulOS Image Relocation
On the Odroid, by default, early-boot ELFLoader tries to load the sel4test-driver image somewhere around physical address `0x3000000`.The secure monitor region starts at `0x5000000`, so the image cannot extend past this. This normally works if the driver's image is small enough (e.g. Linux guest image isn't embedded in the ELF or the static heap size isn't too large). 

However, in our current setup, it is not enough, and the sel4test-driver image must be loaded at a much later address. See [elfloader-tool/src/common.c](https://github.com/sid-agrawal/seL4_tools/blob/7234614e99577f2030f8a71f7f5c8c1578eaf266/elfloader-tool/src/common.c#L34) for where to change this if it causes an issue down the line.

## References to `GUEST_VCPU_ID`
The GIC distributor region emulation is done per CPU. The current implementation assumes the guest does not have `SMP` enabled, and has references to `GUEST_VCPU_ID` floating around, which is just for convenience, as an index to the first (and only) virtual CPU. 

## Kernel Serial Driver vs. User-space Serial Driver
By default, we build seL4 on debug mode, so all user-space printing is routed to the kernel's serial driver through a debug syscall. The user-space serial driver (provided by the `sel4platsupport` library) can be enabled by toggling the `LibSel4PlatSupportUseDebugPutChar` CMake config option. 

```{note}
This currently only works for the `sel4test` VMM implementation, as the sel4platsupport library's serial driver uses the seL4 utils VKA allocators for getting device frames. We haven't implemented an OSmosis-only serial driver, nor have we refactored sel4platsupport library to use CellulOS API calls, so this will not work for OSmosis PDs.
```

