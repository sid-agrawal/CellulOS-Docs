# Unified PD Entry and Exit Point
The goal of a unified entry and exit point is for all PDs in the system to follow a few common standard procedures for startup and exit. We have identified three main PD startup paths that currently cannot be combined any further (it either may not be possible or more work is required to combine them).

```{note}
All of the details below are AARCH64 specific. CellulOS currently does not support any other architecture.
```

## Three main setup pathways:
| PD type          | Defining feature                                | Setup Required                                                                                                                          | How user-given arguments are passed |
| ---------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Process-like PDs | Different ELF code and data section             | Prior to executing the PD, AUX vectors, some ELF data must be written on the stack. Once in the PD, musl libc runtime initialization 	   | On the stack                        |
| Thread-like PDs  | Shared ELF code and data section (could be in different ADSes) | TLS needs to be written with IPC buffer and OSmosis per-PD data addresses.                                               | On the stack                        |
| Guest-OS PDs     | Raw binary is used, no loading performed | Dependent on the guest--for Linux, address of DTB must be passed in a register, and ARM SPSR register needs to be set                          | No user-given arguments             |

## `main` or entry function visible to the started PD
For process-like PDs, this is the standard `main(int argc, char **argv)` function. For thread-like PDs, this can be any function that takes the two, `int argc` and `char **argv` arguments. It may seems strange for secondary threads to receive arguments in the same way that the main thread does, however, recall that all arguments to CellulOS PDs [are passed as strings on the stack](target_pd_runtime_setup_passing_arguments) and that all threads are considered individual PDs.

## C runtime library
[sel4runtime](https://github.com/seL4/sel4runtime) provides most of the functions mentioned below. Explanations of modifications to these functions will be annotated with `[mod]`.

## CellulOS PD Exit Point
When a CellulOS PD exits, it is expected that the PD requests the Root Task's PD component to terminate it and perform any {doc}`cleanup policies </design/design_cleanup_policies>`. `sel4runtime` already provides an easy way to set a unified exit point, via the [sel4runtime_exit()](https://github.com/seL4/sel4runtime/blob/master/src/env.c#L206) function that is automatically called for any thread executed from the `sel4runtime` entry functions. CellulOS simply sets this exit point to the PD component's `pd_client_exit()` and ensures that every PD is executed through an entry function that eventually calls a proper exit. `sel4runtime_exit` also performs some additional destruction of libc data, as it is intended for exiting a process's main thread. `[mod]` CellulOS includes an exit function meant for secondary thread-PDs, which skips the libc destruction: [sel4runtime_exit_no_destruct](https://github.com/sid-agrawal/sel4runtime/blob/cellulos/src/env.c#L217).

## libc `_start`
The `_start` entry-point provided by `sel4runtime` passes a pointer to the top of the stack to the `__sel4_start_c` function in register `x0`. 
`[mod]` An additional "info" argument is passed in register `x1` to indicate which setup path a PD should take.

### `sel4utils` processes
`x1` will contain an enum value indicating the PD started was one set up by `sel4utils`, in which case, control is passed to the unmodified `sel4runtime` libc initialization functions.

### CellulOS process-like PDs
`x1` will contain an enum value indicating the PD started is a CellulOS PD. `[mod]` Control is passed to a custom CellulOS `sel4runtime` initialization function, [__sel4runtime_start_main_osm](https://github.com/sid-agrawal/sel4runtime/blob/14b51c9d61bab718dddca1fa1a10297e4fa6f445/src/start.c#L25), which currently only calls the unmodified libc initialization functions and, eventually, the [](#cellulos-pd-exit-point).

### CellulOS thread-like PDs
`x1` contains the function address for the thread-like PD to start expecting. In this pathway, it's expected that libc has already been initialized for whatever ADS the PD is executing in. `[mod]` Control is passed to a custom entry function, [__sel4runtime_start_entry_osm](https://github.com/sid-agrawal/sel4runtime/blob/14b51c9d61bab718dddca1fa1a10297e4fa6f445/src/start.c#L37), which simply calls the user-provided function with arguments extracted from the stack and, eventually, the [](#cellulos-pd-exit-point). 

## Guest-OS PD Entry
Guest-OS PDs are not routed through the entry and exit points described above. Their entry is simply the start address of the raw binary kernel image. 

### Linux Guests
The `x0` register is expected to hold the address to the beginning of the DTB image. Additionally, [SPSR_EL1.M[3:0]](https://developer.arm.com/documentation/ddi0595/2020-12/AArch64-Registers/SPSR-EL1--Saved-Program-Status-Register--EL1-?lang=en) needs to be set to `EL1h`.

## Custom startup and shutdown policies
Although not currently implemented, it is possible to use these unified entry and exit points to supply additional user-given functions that perform additional policy enforcements once executing within a new PD. For instance, a startup policy that prevents the new PD from ever allocating physical memory in some address range.
