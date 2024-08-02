(target_spawning_pds)=
# Spawning PDs
To do anything useful in CellulOS, we need to create and run units that can execute code. This page details how one might create and set up these units.
<!-- These units are made of three primary components: PD, ADS, CPU, which are termed as a `runnable` in CellulOS source code.  -->
## What exactly are PDs?
The term "PD" is often used throughout the documention to refer to an entity in the system that can execute code. However, an "execution unit" in CellulOS is comprised of a PD, ADS and CPU, and are referred to as `runnable`s in CellulOS source code. Creating runnables requires configuration of all three of these components. A runnable can be a thread, process, virtual machine, etc.

Runnables are set up for execution by specifying various configuration options to the `pd_creation` module, which allocates resources in a PD, sets up an ADS and a CPU, and combines them to form a runnable entity.

```{note}
There is ongoing work in the OSmosis model to further refine which nodes best represent an active entity in the system. For now, it is the PD node.
```

To avoid confusion and to conform to the current model, any references to the term "PD" on this page will still mean a unit of execution. However, keep in mind that it is technically comprised of an ADS and CPU component as well. E.g. "Starting a PD" actually means "starting a CPU which is bound to a PD". References to `runnable` mean the literal CellulOS structure consisting of a PD, CPU and ADS context.

## Pre-requisites for Spawning PDs
CellulOS currently does not provide a single "spawning" server which creates PDs and starts them. Any PD with RDEs to the PD, MO, ADS, CPU, and EP servers can spawn new PDs. 
With our current `sel4test` infrastructure, each test PD ran by the test driver has been given RDEs to all servers in the system, allowing it to spawn PDs by default.

### Reference for Creation
The `pd_creation` module configures PDs in reference from the PD which invokes it, termed the *creator PD*. Only resources which the creator PD either holds or can allocate can be given to the created PD.

### To Share or Not to Share
A resource given to a created PD is either:

1. `SHARED` with the creator PD, meaning any modifications to the resource by one PD is reflected in both.
2. `DISJOINT` from the creator PD, meaning the resource has been allocated for the created PD by the creator PD, however, it is unused by the creator PD at the time of creation.

```{note}
There is currently no concept of more granular permissions on CellulOS resources, as this is still being actively defined in the OSmosis model. If a CellulOS PD holds a resource, it has all permissions to it.
```

## The PD Configuration Interface
All configuration options are specified using the [pd_config_t](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L139) structure. You most often will not need to populate these configurations manually, unless you have a very specific PD setup. There are convenience functions which generation configurations for common PD types, such as [threads](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L188) and [processes](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L174) in the `pd_creation` module.


## Spawning a Process-like PD
 A process-like PD executes almost entirely separate from the creator PD. So, one must create a `runnable` populated with a freshly created PD, ADS, and CPU. There exists a convenience function in the `pd_creation` module for doing this,  [sel4gpi_configure_process()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L174).

 A configuration describing how the process-PD's ADS should be laid out, and what resources and RDEs should be given to it must then be given to the [sel4gpi_prepare_pd()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L199) function. Arguments that should be given to the process can be specified here as well.

 The convenience function, `sel4gpi_configure_process()`, both creates the components within the `runnable` and generates a configuration for process-PDs that can be given to `sel4gpi_prepare_pd`.
The configuration, by default, provides the process-PD with RDEs to the MO server (which the creator PD should already have, in order to spawn PDs). If the creator PD has other RDEs to share with the process, it can be done by adding it to the configuration using [sel4gpi_add_rde_config()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L275).

 Then, all that's left is to call [sel4gpi_start_pd()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L207), which starts the CPU that was created within the `runnable` and was bound to the PD.

 In general, the sequence of calls are:
 
 1. `sel4gpi_configure_process`
 2. `sel4gpi_prepare_pd`
 3. `sel4gpi_start_pd`

 See the [pd_capability](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-tests/src/tests/pd_capability.c#L36) test, which starts a simple "Hello World" process, for reference.

## Creating Threads
In CellulOS, threads of a process are considered their own PD. However, they share the same ADS as the creator PD, and thus its `runnable` structure will reference the same ADS as the creator PD's. For threads, all RDEs and MOs in the creator PD are shared with the created PD. Similar to spawning processes, there exists convenience functions for creating threads within the `pd_creation` module, [sel4gpi_configure_thread](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L188), and the sequence of calls are identical to that of spawning processes.

```{warning}
Since CellulOS threads are individual PDs, they also have separate CSpaces from one another, and requires care in ensuring capability slot references between threads are valid. We currently do not implement any type of CSpace synchronization between thread-PDs.
```

See the [cpu_capability](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/apps/sel4test-tests/src/tests/cpu_capability.c#L90) test for reference.

## Custom PD Configuration
### Address Space Configuration
The bulk of the PD configuration process is in managing address space layout. [ads_config_t](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L116) allows the user the provide a list of virtual memory regions (VMR) to create in a given ADS.

#### Sharing Modes
How the VMR is given to the created PD depends on whether it is `SHARED` or `DISJOINT` from the creator PD, and the info that must be supplied to the ADS configuration system varies depending on this sharing mode. The table below details how various VMRs may be set up, depending on the sharing mode.

| Region | Sharing Mode | Setup Behaviour |
|--------|--------------|-----------------|
| All VMRs  | SHARED | The same physical pages are mapped in both ADSes (normally to the same virtual addresses as well). |
| Most VMRs | DISJOINT | A new VMR of the specified size will be allocated at the specified virtual address. A pre-existing MO can be provided to be mapped at this VMR. If not provided, a new MO will be allocated.  |
| Stack | DISJOINT | Identical to how DISJOINT VMRs are allocated, except with an additional guard page that is NOT backed by a physical page. |
| Code | DISJOINT | An ELF image must be specified along with this VMR, and ELF loading will be perfomed. |

(target_spawning_pds_shared_vmrs)=
#### `SHARED` VMRs
For convenience, a VMR which the creator PD wishes to share with the created PD can be described in the config options by only specifying a VMR type. The ADS config system will request the ADS server to search for a VMR of that type in the creator's ADS. This convenience option only works for VMRs which have a special type (e.g. the stack, heap, ELF data, etc.), where only one such VMR exists in an ADS. Otherwise, the user must specify all other info describing the VMR to the ADS config system.

#### Deep-Copied VMRs
VMRs in the created PD which should share the same content as a VMR in the creator PD but are mapped to different physical pages are considered `DISJOINT` VMRs. There is additional effort needed from the creator PD outside of the `pd_creation` module to deep-copy a VMR:

1. Allocate a new MO of the same size as the one mapped to the VMR to deep-copy
2. Map the MO into the creator PD's ADS, copy the contents of the deep-copied VMR into the new MO
3. In the VMR description to give to the ADS config system, set the VMR as `DISJOINT`, but provide the newly allocated MO. The config system will attach this MO, with the copied contents, into a VMR in the new ADS

#### VMR Descriptions
Not all fields of the VMR description ([vmr_config_t](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L84)) need to be filled in. Whether a field needs to be filled in depends on its sharing mode. The table below details which fields need to be specified, for each sharing mode:

|    Option    | SHARED | DISJOINT |         Default (when optional)         |
|--------------|------------|--------------|-----------------------------------------|
| type         | required   | required     |                                         |
| start        | required`^1`   | optional     | any available virtual address           |
| dest_start   | optional   | ignored      | `start`                                 |
| region_pages | required`^1` | required     |                                         |
| page_bits    | ignored    | optional     | 4K pages                                |
| mo           | ignored    | optional     | new MO will be allocated                |

`^1`: This field is only optional if the VMR type is a special type, as described in [`SHARED` VMRs](target_spawning_pds_shared_vmrs).

### CPU Configuration
A CPU may need higher priviledges to access a few system registers. In seL4, this corresponds to binding a VCPU object to a TCB, and is done when the `elevated_cpu` config option is toggled.

### RDE Configuration
The created PD can be given all or a subset of the RDEs which the creator PD can request from. The convenience function [sel4gpi_add_rde_config()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L275) can be used to specify that an RDE of a certain resource type and namespace should be shared with the created PD.

### Fault Handling
The creator PD can specify a fault handler for the created PD by setting the fault endpoint in the configuration. If none are specified, a new fault endpoint will be allocated for the PD, which the creator can retrieve to listen on.

### Linked PDs
You may want some PDs to be automatically terminated when another PD exits (for instance, additional threads when the main thread of a process exits). To create a PD which gets terminated when the creator PD exits, the `link_with_current` config option can be toggled. For thread-PDs, this option is automatically set if using `sel4gpi_configure_thread()`.

## Non-standard PD Types
### Spawning a HighJMP PD
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

Since the stack, IPC buffer, and ELF code segments are all special VMR types, the VMR description can use the convenience option described in [`SHARED` VMRs](target_spawning_pds_shared_vmrs).

The CPU can then be configured to swap between ADSes on demand using `cpu_client_change_vspace()`.



### Threads With Isolated Stacks
In CellulOS, threads with isolated stacks exist in a separate ADS from the main thread, but share most of the main thread's VMRs. An isolated thread-PD can be created like so:

1. Create a new `runnable`, allocating new a PD, ADS and CPU. A convenience function [sel4gpi_new_runnable()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/pd_creation.h#L163) exists for this purpose.
2. Configure the ADS to share ELF regions, the heap, and any other desired VMR with the new thread. Configure the stack and IPC buffer to be disjoint VMRs.
3. Give the configuration to `sel4gpi_prepared_pd()`
4. Start the thread using `sel4gpi_start_pd()`


```{warning}
Due to the secondary thread existing in a separate ADS, any additional changes to the main thread's ADS that should be reflected in the secondary thread's ADS needs to be done manually by the main thread (e.g. by mapping a VMR in both ADSes). 
```
