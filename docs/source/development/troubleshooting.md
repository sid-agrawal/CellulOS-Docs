# Troubleshooting Development Errors

# Debugging Tools
## Clean Rebuild
Occasionally builds will fail, especially after adding / deleting files. Deleting the build folder and clearing ccache should fix it.

For Qemu:
```
rm -r -f qemu-build
ccache -C
mkdir qemu-build
cd qemu-build
../init-build.sh -DAARCH64=TRUE -DPLATFORM=qemu-arm-virt -DSIMULATION=TRUE
```

For Odroid-D4:
```
rm -r -f odroid-build
ccache -C
mkdir odroid-build
cd odroid-build
../init-build.sh -DPLATFORM=odroidc4
```

## Debug Prints
The debug options for the GPI server are located in `projects/sel4-gpi/libsel4gpi/include/sel4gpi/debug.h`:
- `OSDB_TOPIC` sets which components are allowed to print.
- `OSDB_LEVEL` sets the level of verbosity for the enabled topics.

(target_debugging_gdb)=
## Qemu with GDB
1. From the Qemu build folder, run `./simulate --extra-qemu-args "-S -s"`.
2. Open a new terminal window in the Qemu build folder, run `gdb-multiarch <image_path>`, replacing `<image_path>` with the location of the image you want to debug.
    - Root task image: `gdb-multiarch apps/sel4test-driver/sel4test-driver`
    - Test process image: `apps/sel4test-driver/sel4test-tests/sel4test-tests`
    - Other app images are in the `apps/sel4test-driver/` directory
3. Once GDB starts up, connect to Qemu with `target remote :1234`.

## Loading debug symbols from musllibc
By default, debug symbols are not loaded from musllibc. If you want to set a breakpoint inside `malloc.c`, for example, you will need to extract the symbols.
1. Enable musllibc debug: in `/projects/musllibc/makefile` line 57, change `${ENABLE_DEBUG}` to `--enable-debug`. 
    - I have not figured out how to properly set the flag, as build errors occured when I tried to set it from the cmake file.
2. Extract the desired object file: eg. to extract malloc, run `ar -xv apps/sel4test-driver/musllibc/build-temp/stage/lib/libc.a malloc.o` from the build folder.
3. Now the symbols should be loaded automatically in GDB.

## addr2line
If the system fails with a page fault, it will print the image name and PC where the fault occurred. Use addr2line to find the file & line where the error occurred:
```
addr2line -e apps/sel4test-driver/<image_path> 0x<PC>
```

If this returns `???`, the fault may have occurred in a library call, eg. `memset`. Another way to determine where the fault occurred is using `objdump`:
```
<aarch64-none-elf_toolchain_path>/bin/aarch64-none-elf-objdump -DS apps/sel4test-driver/<image_path> | less
```
- You will need to determine the location of the correct objdump depending on where you installed your `aarch64-none-elf` toolchain.
- Piping to `less` allows you to search with `/`, then input the PC value, and determine what function the fault occurred in.

# Common development pitfalls
## Server error when contacting the ADS component
If an "invalid request" error is returned while attempting to attach or remove a VMR from an ADS, double-check that the *VMR RDE* for the ADS endpoint is being used to send the request. See the [ADS capability quirks](target_design_ads_capability) section for more details.

## Insufficient untyped memory after resources are freed
The VKA allocator may throw a bunch of errors about "insufficient memory to allocate untypeds" despite it being extremely unlikely for the system to have run out of memory (e.g. after something has just been freed). This is caused by freeing an object *before* all descendant capabilities to the object have been deleted. Freeing an object causes the underlying untyped memory to be returned to the VKA allocator's free memory pool. If a capability to the memory *when it was typed* still exists, attempts to retype the untyped memory will fail, causing the VKA allocator to think it is out of memory, and returning the misleading "insufficient memory" error. 

This may not *always* be the cause of this error, but a good way to tell is by using the `seL4_DebugCapIsLastCopy` syscall. This will return true if there exists a copy of a given capability from the current CSpace in *any existing CSpace*.

Potential solutions include:
1. Revoking the capability before freeing - this is a quick and easy (from the developer's perspective, not in terms of the kernel's efforts) to deal with the error, but leaves references to the revoked caps invalid.
2. For CellulOS tracked resources, toggling the `GPI_DEBUG` log topic, and ensuring that reference counts for the problem capability increase/decrease according to expectation.
3. Checking both CNodes and TCBs as potential capability containers. TCBs are often forgotten about as containers that capabilities may need to be freed from.
