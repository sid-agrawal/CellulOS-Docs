# Spawning Common PDs
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
