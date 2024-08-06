# Unified PD Entry and Exit Point
```{attention}
WIP
```

The goal of a unified entry and exit point is for all PDs in the system to follow a few common standard procedures for startup and exit. We have identified three main PD startup paths that currently cannot be combined any further (it either may not be possible or more work is required to combine them).

```{note}
All of the details below are AARCH64 specific. CellulOS currently does not support any other architecture.
```

## Three main setup pathways:
| PD type          | Defining feature                                | Setup Required                                                                                                                          | How user-given arguments are passed |
| ---------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Process-like PDs | Different ELF code and data section             | Prior to executing the PD, AUX vectors, some ELF data must be written on the stack. Once in the PD, Musllibc runtime initialization 	   | On the stack                        |
| Thread-like PDs  | Shared ELF code and data section (could be in different ADSes) | TLS needs to be written with IPC buffer and OSmosis per-PD data addresses.                                               | On the stack                        |
| Guest-OS PDs     | Raw binary is used, no loading performed | Dependent on the guest--for Linux, address of DTB must be passed in a register, and ARM SPSR register needs to be set                          | No user-given arguments             |

## Plan for abstracting the entry point for all PDs:
We will differentiate between three cases, 1) PDs with different code sections, 2) PDs with the same code sections 3) PDs whose binaries are never loaded (VMs). I currently don't think we need any more cases.

1) Write all arguments onto the stack, for non-guest PDs
2) Every non-guest PD's entry-point will be set to `_start`, and `x0` will hold an argument:
	1) For PDs with the same code sections, `x0` = the function address
	3) For PDs with different code sections, `x0 = 1` to indicate that the C runtime must be set up
3) Nothing will change for guest PDs. They will use their own entry point, and `x0` must be the address of the DTB (for Linux guests)
4) Modify `_start` to pass both the value in `x0` and the stack pointer to `__sel4_start_c`
5) modify `__sel4_start_c`:
	1) for PDs with separate code segments, we let it run `__sel4runtime_start_main` as usual
	2) for PDs with the same code segments, we cast the function address in `x0` to a function pointer, and call it with the arguments written on the stack
		1) `__sel4runtime_start_main` eventually calls `sel4runtime_exit` with a callback that does C runtime cleanup and OSmosis PD cleanup, which stops the TCB. 
		2) We'd want to keep all the musllibc contents intact when thread-like PDs exit, so the only thing that needs to be done is probably to call the OSmosis PD cleanup.

## `main` or entry function visible to the started PD
For process-like PDs, this is the standard `main(int argc, char **argv)` function. For thread-like PDs, this can be any function that takes the two, `int argc` and `char **argv` arguments.

## C runtime library
[sel4runtime](https://github.com/seL4/sel4runtime) provides most of the functions mentioned below. Explanations of modifications to these functions will be annotated with `[mod]`.

## CellulOS PD exit
When a CellulOS PD exits, it is expected that the PD requests the Root Task's PD component to terminate it perform any {doc}`cleanup policies </design/design_cleanup_policies>`.

## libc `_start`
The `_start` entry-point provided by `sel4runtime` passes a pointer to the top of the stack to the `__sel4_start_c` function in register `x0`. 
`[mod]` An additional "info" argument is passed in register `x1` to indicate which setup path a PD should take.

### `sel4utils` processes
`x1` will contain an enum value indicating the PD started was one set up by `sel4utils`, in which case, control is passed to the unmodified `sel4runtime` libc initialization functions.

### CellulOS process-like PDs
`x1` will contain an enum value indicating the PD started is a CellulOS PD. `[mod]` Control is passed to a custom CellulOS `sel4runtime` initialization function, which currently only calls the unmodified libc initialization functions and additionally sets the libc exit function to the [](#cellulos-pd-exit).

### CellulOS thread-like PDs
`x1` contains the function address for the thread-like PD to start execting. `[mod]` Control is passed to a custom entry function which sets the libc exit function similarly to the procedure for process-like PDs. The stack arguments and argument count are extracted and the user-provided function is simply called.



## extensible policies
supply a function which may be called prior to a process's `main` or a thread's function that executes some type of policy?
