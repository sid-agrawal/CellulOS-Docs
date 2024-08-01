# Unified PD Entry and Exit Point
```{attention}
WIP
```
The current method of starting PDs differs across the type of PD, and is too specific to process-like and thread-like PDs due to it being adapted from how seL4utils starts processes and threads.

## Summary of how the different PDs are currently set up:
| PD type          | Defining feature                                | Setup Required                                                                                                                          | How user-given arguments are passed |
| ---------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Process-like PDs | Different code section                          | Prior to executing the PD, AUX vectors, some ELF data must be written on the stack. <br>Once in the PD, Musllibc runtime initialization | On the stack                        |
| Thread-like PDs  | Same code section (could be in different ADSes) | TLS needs to be written with IPC buffer and OSmosis per-PD data addresses.                                                              | In general registers                |
| Guest-OS PDs     | Binary is never loaded                          | Address of DTB must be passed in a register, and ARM SPSR register needs to be set                                                      | No user-given arguments             |

## How each PD's entry-point current behaves
### Process-like PDs
1) Linker automatically sets the entry point to `__start`, in `crt0.S`. [Some easy-to-digest reference](http://www.muppetlabs.com/~breadbox/software/tiny/teensy.html)
2) `__start` calls `__sel4_start_c`, which ends up initializing the C runtime environment (e.g. the TLS, various C environment states from the AUX vectors), and other musllibc data (e.g. syscall pointers)
3) eventually,`__sel4_start_c` calls `sel4runtime_exit` which cleans up the PD

### Thread-like PDs
1) the CPU immediately jumps to the address of the function, and expects function arguments in `x0, x1, x2` registers
2) Since we jumped to the function directly, the return address (which is normally pushed onto the stack by compiled code) doesn't exist, and when the thread's function finishes executing, it currently page faults. 

### Linux-guest PDs
1) Similar to thread-like PDs, they jump immediately to an address within their kernel image.
2) `x0` must hold the address of the DTB

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

I will update this if I discover new things during implementation.
