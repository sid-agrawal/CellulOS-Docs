# Flexible PD Configuration
## Address Space Configuration
The bulk of the PD configuration process is in managing address space layout. [ads_config_t](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L116) allows the user the provide a list of virtual memory regions (VMR) to create in a given ADS.

### Sharing Modes
How the VMR is given to the created PD depends on whether it is `SHARED` or `DISJOINT` from the creator PD, and the info that must be supplied to the ADS configuration system varies depending on this sharing mode. The table below details how various VMRs may be set up, depending on the sharing mode.

| Region | Sharing Mode | Setup Behaviour |
|--------|--------------|-----------------|
| All VMRs  | SHARED | The same physical pages are mapped in both ADSes (normally to the same virtual addresses as well). |
| Most VMRs | DISJOINT | A new VMR of the specified size will be allocated at the specified virtual address. A pre-existing MO can be provided to be mapped at this VMR. If not provided, a new MO will be allocated.  |
| Stack | DISJOINT | Identical to how DISJOINT VMRs are allocated, except with an additional guard page that is NOT backed by a physical page. |
| Code | DISJOINT | An ELF image must be specified along with this VMR, and ELF loading will be perfomed. |

### `SHARED` VMRs
For convenience, a VMR which the creator PD wishes to share with the created PD can be described in the config options by only specifying a VMR type. The ADS config system will request the ADS server to search for a VMR of that type in the creator's ADS. This convenience option only works for VMRs which have a special type (e.g. the stack, heap, ELF data, etc.), where only one such VMR exists in an ADS. Otherwise, the user must specify all other info describing the VMR to the ADS config system.

### Deep-Copied VMRs
VMRs in the created PD which should share the same content as a VMR in the creator PD but are mapped to different physical pages are considered `DISJOINT` VMRs. There is additional effort needed from the creator PD outside of the `pd_creation` module to deep-copy a VMR:

1. Allocate a new MO of the same size as the one mapped to the VMR to deep-copy
2. Map the MO into the creator PD's ADS, copy the contents of the deep-copied VMR into the new MO
3. In the VMR description to give to the ADS config system, set the VMR as `DISJOINT`, but provide the newly allocated MO. The config system will attach this MO, with the copied contents, into a VMR in the new ADS

### VMR Descriptions
Not all fields of the VMR description ([vmr_config_t](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L84)) need to be filled in. Whether a field needs to be filled in depends on its sharing mode. The table below details which fields need to be specified, for each sharing mode:

|    Option    | SHARED | DISJOINT |         Default (when optional)         |
|--------------|------------|--------------|-----------------------------------------|
| type         | required   | required     |                                         |
| start        | required`^1`   | optional     | any available virtual address           |
| dest_start   | optional   | ignored      | `start`                                 |
| region_pages | required`^1` | required     |                                         |
| page_bits    | ignored    | optional     | 4K pages                                |
| mo           | ignored    | optional     | new MO will be allocated                |

`^1`: This field is only optional if the VMR type is a special type, as described in [](#shared-vmrs).

## CPU Configuration
A CPU may need higher priviledges to access a few system registers. In seL4, this corresponds to binding a VCPU object to a TCB, and is done when the `elevated_cpu` config option is toggled.

## RDE Configuration
The created PD can be given all or a subset of the RDEs which the creator PD can request from. The convenience function [sel4gpi_add_rde_config()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L275) can be used to specify that an RDE of a certain resource type and namespace should be shared with the created PD.

## Sharing Resources
Sharing VMR resources are handled by the ADS configuration system, as described above. Other individual resources, such as MOs or files can be shared using the `pd_client_send_cap()` API call, which currently must be done outside of the `pd_creation` module.

For convenience, all resources of a certain type can be shared in one API call, which is configured by using the `gpi_res_type_cfg` option. This is a list of resource types to be shared in bulk with the created PD. 

```{warning}
This bulk sharing of resources by type currently only allows sharing of MO resources. While theoretically possible, it currently does not make sense to send all of the creator PD's CPU, ADS, EP resources to the created PD. For non-core resources (e.g. resources not managed by the Root Task), this is a [limitation](target_known_limits_non_core_res_transfer) of CellulOS, where complete tracking of non-core resources has not yet been implemented.
```

## Fault Handling
The creator PD can specify a fault handler for the created PD by setting the fault endpoint in the configuration. If none are specified, a new fault endpoint will be allocated for the PD, which the creator can retrieve to listen on.

## Linked PDs
You may want some PDs to be automatically terminated when another PD exits (for instance, additional threads when the main thread of a process exits). To create a PD which gets terminated when the creator PD exits, the `link_with_current` config option can be toggled. For thread-PDs, this option is automatically set if using `sel4gpi_configure_thread()`.

# Non-standard PD Types
## Spawning a HighJMP PD
<!-- mention how the ADS setup could be transparent to the user by wrapping all KVstore calls in another layer
    add a page describing what HighJMP is and reference it here
 -->
A PD which is capable of HighJMP address-space switching is considered a single PD, which holds two ADSes.
CellulOS currently implements HighJMP requiring user-involvement. This means that the HighJMP PD is aware of its separate ADSes and is directly responsible for setting up additional ADSes and switching between them. One can imagine an implementation where the ADS management is pushed into a client-library, where the ADS switching is transparent to the PD. There is nothing preventing such an implementation in CellulOS.

With respect to our current implementation, the HighJMP PD can be created by spawning a process as usual. Once inside the process, the PD can create a new ADS and configure it using [sel4gpi_ads_configure()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L262).

The VMRs that must be specified for a HighJMP ADS are:

- Deep-copied Heap
- Deep-coped ELF data segment
- Shared Stack
- Shared IPC Buffer
- Share ELF code segment

Since the stack, IPC buffer, and ELF code segments are all special VMR types, the VMR description can use the convenience option described in [](#shared-vmrs).

The CPU can then be configured to swap between ADSes on demand using `cpu_client_change_vspace()`.



## Threads With Isolated Stacks
In CellulOS, threads with isolated stacks exist in a separate ADS from the main thread, but share most of the main thread's VMRs. An isolated thread-PD can be created like so:

1. Create a new `runnable`, allocating new a PD, ADS and CPU. A convenience function [sel4gpi_new_runnable()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L163) exists for this purpose.
2. Configure the ADS to share ELF regions, the heap, and any other desired VMR with the new thread. Configure the stack and IPC buffer to be disjoint VMRs.
3. Give the configuration to `sel4gpi_prepared_pd()`
4. Start the thread using `sel4gpi_start_pd()`


```{warning}
Due to the secondary thread existing in a separate ADS, any additional changes to the main thread's ADS that should be reflected in the secondary thread's ADS needs to be done manually by the main thread (e.g. by mapping a VMR in both ADSes). This is a [known limitation](target_known_limits_ads_config) of Cellulos.
```
