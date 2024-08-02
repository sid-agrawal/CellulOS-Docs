# The User-Space Virtual Machine Monitor

```{attention}
WIP
```

There are two VMM implementations in *CellulOS*, both ported from seL4's Microkit [libvmm](https://github.com/au-ts/libvmm). 
One implementation only seL4 utility libraries present in the [sel4test](https://github.com/seL4/sel4test) project, and the other uses only CellulOS APIs.

## Source File Organization
The source files for both implementations exist under one parent directory, [sel4-gpi/apps/vmm](https://github.com/sid-agrawal/sel4-gpi/tree/cellulos/apps/vmm) and are further divided between children `sel4test-vmm` and `osm-vmm` directories. There are a few common source files and headers, which are under `vmm-common` directories. 

Due to the two implementations sharing identical function names whose arguments are differences in pointer types, only one set of source files can be built at a time (building both will result in a source file from one implementation potentially overwriting the other's). This is toggled via a CMake config variable: `VMMImplementation`, which can either be: `sel4test-vmm` or `osm-vmm`. See the [CMakeLists.txt](https://github.com/sid-agrawal/sel4-gpi/tree/cellulos/apps/vmm) file for details.

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

## OdroidC4 CellulOS Image Relocation
On the Odroid, by default, early-boot ELFLoader tries to load the sel4test-driver image somewhere around physical address `0x3000000`.The secure monitor region starts at `0x5000000`, so the image cannot extend past this. This normally works if the driver's image is small enough (e.g. Linux guest image isn't embedded in the ELF or the static heap size isn't too large). 

However, in our current setup, it is not enough, and the sel4test-driver image must be loaded at a much later address. See [elfloader-tool/src/common.c](https://github.com/sid-agrawal/seL4_tools/blob/7234614e99577f2030f8a71f7f5c8c1578eaf266/elfloader-tool/src/common.c#L34) for where to change this if it causes an issue down the line.

## References to `GUEST_VCPU_ID`
The GIC distributor region emulation is done per CPU. The current implementation assumes the guest does not have `SMP` enabled, and has references to `GUEST_VCPU_ID` floating around, which is just for convenience, as an index to the first (and only) virtual CPU. 

## (WIP) Old Notes
### Specific Memory Regions

These need to be set up in the vCPU’s vspace

- Linux image’s DTS expects guest RAM at `0x40000000` (default is 256 MB)
    - Guest’s DTB and RAM Disk addresses are then just placed within this region
- Serial device address (board-dependent)
    - for QEMU, one page at a specified region
    - for the Odroid, three different pages and regions (not sure why)
- GIC device address (specific to ARM and board-dependent)

### Caps/Resourced Needed for VMM to Setup Guest

Currently running VMM as a sel4test process, but if we were to run it just as an independent process, we would need:

- VKA
- RT’s IRQControl cap (or a minted handler)
- access to its own vspace and the root page table for its vspace
- an ASID Pool (if using a previously created one)
- a simple object (currently on used to get the RT’s TCB for setting scheduling priority to max - need to look into whether it will still be scheduled to run if priority is set using only the test or other parent process’s TCB)

### Loading in VM Images

- requires ~40MB total, ensure that whatever process is loading the VM has enough of this in untyped
    - If we run out of memory, check the following:
        - virtual pool range of the loading process’s allocation manager
        - the amount of untyped memory available for the loader (is it being given to other things first?)
        - the loading process’s cspace size - may run out of slots (although if mapping is done with large pages, this shouldn’t really be an issue)
- binaries are placed in ELF under specific sections and with specific symbol names, see `projects/sel4-gpi/vmm/tools/package_guest_images.S`
    - to build as part of the sel4test-driver, requires passing in path of the guest kernel image (currently built separately), guest DTB image (built from a DTS using `dtc`), and a guest RAM disk image (currently built separately)
    - this is then `memcpy`'d to the expected virtual addresses for the guest, which is kind of wasteful - is there some way we can avoid this (maybe via linker script)?

### Build Quirks

- original VMM is linked using LLVM’s LLD instead of GCC’s default `ld`, can be specified in cmake with `add_link_options("-fuse-ld=lld")`
    - currently doesn’t work, as cmake can’t find `lld` in PATH despite it being included
    - also using GCC’s default linker doesn’t seem to have any issues at the moment
- the rest of the entire project specifies board names with hypens, e.g. `qemu-arm-virt`, but the VMM uses underscores, since certain symbols are defined using the board name (which can’t have hyphens)
    - currently, we just swap to the correct name in CMakeLists.txt if we’re building the vmm files, but this could (should?) change b/c we should ideally parse the DTS for this

 

### Microkit Quirks

- refer to `tool/microkit/**main**.py` if you need to figure out what some arbitrarily hardcoded slot number is referring to (use specifically Ivan’s fork: `git clone [https://github.com/Ivan-Velickovic/microkit.git](https://github.com/Ivan-Velickovic/microkit.git) --branch dev`)
- microkit doesn’t use any threads, and ends up disabling the TLS keyword, which conflicts with our current system (which relies of sel4 runtime and does require proper definition of the TLS keyword) → see comment in microkit repo: `monitor/src/main.c`

### Future TODO

- most interrupts (except for serial device) are currently disabled b/c it was previously routed through microkit’s version of IPC (e.g. a “channel” between a defined PD and the microkit monitor)
    1. to convert it, get a ref to the RT’s IRQControl cap, then mint an IRQ handler off of this
    2. set up a notification object for the interrupt, and something to listen for notifications on it
    3. pair this notification object with the IRQ handler
- further investigate how it’s possible that `libsel4platsupport` is able to set up a serial device during bootstrapping of the RT, and we can then get a frame cap to the *same* region in the VMM → could be giving the VMM process the same untyped memory chunk that `libsel4platsupport` is using
- set up fault handler - VMM currently has a fault EP, but just doesn’t do anything with it
- there are a bunch of statically defined cap slots holding various caps (remnant from Microkit) that haven’t been dynamically allocated yet - it currently isn’t an issue bc our VM doesn’t do anything after booting up
- In current state of project, VMM test can never reserve enough for the guest RAM region for some reason → potentially caused by MO cap forging taking up a lot of virtual range
- set up a blocking loop for VMM to handle faults and interrupts for guest - currently just indefinitely yielding

### Misc Stuff

- define `ZF_LOG_LEVEL` in CMakeLists.txt to get the sel4 util logs showing
- attempted to enable dynamic morecore. for some reason, it’s being called before the initial static mem for morecore is even initialized
    - happens somewhere in `sel4utils_bootstrap_vspace_with_bootinfo_leaky`, specifically a call to the vspace function for allocating new pages

