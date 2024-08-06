# PD Runtime Setup
## Conditions for setup method
There are currently three different setup methods which the `pd_creation` module employs based on what the ADS and CPU configurations imply. 

1. If both the ELF code and data segments between the creator and created PD are disjoint, and ELF must be loaded, requiring the entire C runtime to be initialized.
    - Auxiliary vectors, ELF header data and environmental values (if any exist) will be written on the stack in addition to user-provided arguments
2. If both the ELF code and data segments are shared, no ELF will be loaded. It's inferred that the C runtime must have already been initialized in the data segment of the creator PD, and thus only the TLS needs to be set up. 
    - the TLS and user-given arguments will be written on the stack
3. If the CPU has been elevated, it's assumed that the PD is a guest OS and nothing is set up. 

(target_pd_runtime_setup_passing_arguments)=
## Passing Arguments to the PD
All arguments are passed to PDs as strings and are written on the stack, except for guest-OS PDs. The `pd_creation` module takes word arguments and converts them into strings. This is primarily because all our PDs are currently spawned programatically, and word arguments are more practical. 

### Stack Layout for C runtime setup
```{image} ../figures/stack_layout_full.jpg
```

### Stack Layout with TLS setup
```{image} ../figures/stack_layout_thread.jpg
```

## The Root Task's Role in PD configuration
All configuration is currently done within the client via the `pd_creation` module, by combining various, smaller API clls to the Root Task. 
The goal was to keep the Root Task as simple as possible, and to not store any runtime specific data, nor to make any decisions on how a PD should be set up. 
However, there is a limitation of our resource-server to client communication protocol, where we do not send large messages that may require setting up an additional shared message buffer beyond the seL4 IPC buffer or bypass the nanopb interface. 
Due to this, some runtime-specific data which are too large to send through our current communication protocol is stored in the Root Task, which result in the Root Task making a few small runtime-setup decisions.

### `pd_client_runtime_setup()`
This is the only API call where the Root Task will make decisions on how a PD should be set up. Since the Root Task does not store nor is provided any of the user-configuration data, it makes simple inferences on how to set up the PD, based on the minimal runtime-specific data stored in various components. The inferences follow those listed in [](#conditions-for-setup-method).

### ELF metadata
The Root Task performs ELF loading, for convenience, through the `ads_client_load_elf()` API call. The PD component will store a bit of ELF metadata within a PD object's metadata. 
Why is this information not stored in the ADS object's metadata?
1. Multiple ELFs may be loaded into one ADS. The ADS object could store a list of some sort, but there is currently no use-case for this in CellulOS.
2. A PD is likely running only one ELF code segment at a time, and there is currently no drawback to associating a PD with its ELF metadata. 
3. A thread-like PD will not have any ELF-loading done, and existence of ELF metadata in a PD object is used to determine whether to write C runtime data onto the stack. If ELF data was associated with the ADS, which will always have ELF data initialized, the setup inference will incorrectly set up the entire C runtime for thread-PDs

```{note}
This is not really a big limitation, it would be trivial to move where this data is held and change a bit of logic.
```

### Elevated CPUs
The existence of a binded seL4 VCPU object with a CellulOS CPU object determines whether the CPU is meant for a guest-OS PD.

## TLS setup
Why is ELF loading done by the Root Task but the TLS setup done by a client PD? TLS setup is done for thread-like PDs, who share ADSes with another PD. Its TLS needs to have the same image, which is dependent on a static portion of the ELF, and setting up a thread-PD from within the Root Task causes the PD to fault, as the TLS images do not match.

```{note}
There is a chance that it is faulting due to another reason, and TLS setup from within the Root Task may be possible. We have not explored this deeper.
```

Only two variables are written in a CellulOS PD's TLS: the address of the IPC buffer, and the address of the [shared OSmosis data frame](target_glossary_shared_data).


