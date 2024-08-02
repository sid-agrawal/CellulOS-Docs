# The File Server

## The File System
The file system is an extracted and modified version of the [xv6 OS](https://github.com/mit-pdos/xv6-public)'s file system. It is not a fully-functional file system. For instance, it does not implement mutual exclusion, so the file server must be single-threaded. 

The files that are originally from xv6 OS are:
- `/apps/xv6fs/src/fs_server/`
    - `bio.c`
    - `file.c`
    - `fs.c`
    - `mkfs.c`
    - `sleeplock.c`
    - `spinlock.c`

`/apps/xv6fs/src/fs_server/sysfile.c` is roughly adapted from SkyBridge, and provides the 'syscalls' that the fs_server can make to the file system.

`/apps/xv6fs/src/fs_server/fs_server.c` is the server code that processes client requests by calling the file system. It also implements the block functions that the file system expects. The file system expects that `xv6fs_bread` / `xv6fs_bwrite` will read/write the block of the corresponding logical block number (ie. the block numbers the file system uses internally, from 0 to max block number). The file server dispatches these requests to the ramdisk; see the section below for more detail.

## Interaction with Ramdisk
The file system currently has a fixed size such that one file system will need half of the ramdisk. This size could be configurable per-FS instead.

```
// Size of file system in blocks
#define FS_SIZE (RAMDISK_SIZE_BYTES / RAMDISK_BLOCK_SIZE) / 2
```

Upon startup of a file server, it requests the number of blocks corresponding to FS_SIZE from the ramdisk. The file server keeps the capability for each block in a static array, indexed by logical block number. When `xv6fs_bread` / `xv6fs_bwrite` is called, the file server retrieves the corresponding block's endpoint capability from the array, and sends the request to the ramdisk.

## File Resources

A file resource in the implementation represents an open file, although closed files continue to exist in the file system. A PD can create a new file resource by opening an existing, closed file by pathname, or by creating a new file entirely. Implicitly, a PD with a request edge to a file server has a hold edge to every file in the namespace, although it would be unnecessary for it to actually hold every file resource if it is not using them. When the model state is extracted, the file server indicates that client PDs hold every file in the namespace(s) they have access to.

## File Namespaces
The file server implements a specific type of namespace, where namespaces are by default disjoint, and each namespace consists of the files within a particular namespace directory. 

When a file server creates a new namespace, it requests a new resource space from the root task, which also creates a new RDE for the PD that requested the namespace (the RDE is the file server endpoint badged with the space ID). If the resource space has ID X, then the file server makes a new directory `/nsX/`. The effect is that, if the file server receives a request badged with space ID X, it will only allow opening/creating files within the `/nsX/` directory. Thus, namespaces are by default disjoint, but if a PD has access to a namespace X and a file resource linked to by another namespace Y, it may link a name from namespace X to the same file resource.

Currently, model extraction ignores file names. I seems possible to also show file names as resources in model extraction, without actually implementing file names as resources.

```{note}
The question of whether / how to show file names in the model state is not fully fleshed out, and requires further investigation.
```

## File Client

The file client `/apps/xv6fs/src/fs_client/fs_client.c` is the compatibility layer between libc and the file server. The file client tracks file descriptors at a per-PD level, so that libc may refer to file descriptors, and the file client converts an FD to a file resource before forwarding the request to the file server.
- Since we do not model an FD as a resource, two processes cannot share a file offset (eg. as a parent and child would after a fork). A file offset is not an inherent property of a file, but rather a state being tracked by a process. A shared file offset could be modeled by something more general like “shared variable” resource, or even a memory object.
