# Troubleshooting Development Errors

```{attention}
WIP, things to be added:
- common pitfall with the ADS and VMR client contexts
- "insufficient memory" VKA error that occurs due to freeing before all caps are deleted
```

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