# The Ramdisk Server

The ramdisk server is a simple app, intended to get the file system off the ground. It provides the ability to allocate, read, write, and free blocks.

## Blocks
The ramdisk server allocates a large, contiguous MO as the ramdisk. Blocks are page-sized chunks of the ramdisk; by default, the disk has 1024 blocks.

In order to use the ramdisk, clients must call `ramdisk_client_alloc_block` to call a block resource. The client is not able to choose which block it will receive, as we have not yet seen a need for this feature. Allocation is unique; no other allocation call will return the same block, unless if the block is first freed using `ramdisk_client_free_block`.

## Binding Shared Memory
A client of the ramdisk is likely to perform a large number of read/write operations. To reduce overhead, rather than sending an MO for data transfer with every operation, a ramdisk client "binds" an MO with the `ramdisk_client_bind` call. The ramdisk server will keep this MO attached to its own ADS and use it for read/write calls, until the client calls `ramdisk_client_unbind`. Note that the bound page will not be automatically released if a client PD crashes without calling unbind, see details [here](target_limitations_ramdisk_bound_page).