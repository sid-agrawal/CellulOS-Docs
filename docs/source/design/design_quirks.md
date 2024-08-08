# Design Quirks

This captures some quirks of the design that my be unintuitive.

(target_design_ads_capability)=
## ADS Capability
The ADS capability, like the PD capability, is not an entity in the model. The ADS capability is a resource in implementation only, providing a PD with the ability to perform certain operations on an entire address space.

```{note}
We suspect that the semantics of these implementation-only resources will be captured by new model edges or permissions in the future.
```

When a PD allocates an ADS, the ADS component returns the *ADS capability*. A PD may perform the following operations with an ADS capability:
1. Bind the ADS to a CPU.
2. Send the ADS resource to another PD.
3. Copy contents of the ADS to another ADS it has possession of.
4. Load an ELF image to the ADS. This is a convenience function which could alternatively be implemented on the client side, using VMR resources as described below.

When allocating an ADS, the root task creates a new resource space of type VMR, and adds a new RDE for it to the caller PD. Note that the ADS capability is not used to reserve or map memory to the address space, and you will see a server error if you attempt to do so. 
A PD uses this *VMR RDE* to manage the new address space's virtual memory regions. In other words, to modify the memory of an address space with ID `x`, a PD uses the RDE of type VMR with resource space ID `x` to allocate VMR resources. These VMR resources are specific to address space `x`. You can retrieve the RDE using `sel4gpi_get_rde_by_space_id(x, GPICAP_TYPE_VMR)`.

```{note}
Revealing the true ID for ADS resources may seem like poor design, and while we do agree, the ID returned is only relative to other ADSes and could easily be masked by the ADS component. We leave implementation of this feature to the future.
```

A PD may perform the following operations with a VMR capability:
1. Map an MO to the VMR. This makes the MO's physical memory accessible through the parent address space.
2. Delete the VMR. This removes the virtual memory region from the parent address space and page tables.

### Implicit VMRs
Often, we simply want to attach an MO to an address space, and we do not care to manage a VMR resource. For these cases, you can use the convenience functions of the VMR API with a VMR RDE:
- `vmr_client_attach_no_reserve`: This combines the reserve and attach operations, allocating a VMR of the correct size to directly attach an MO. This does not return a VMR resource, but the VMR exists implicitly and will appear in the model state.
- `vmr_client_delete_by_vaddr`: To remove an implicit VMR, we refer to it by the region's start address.

### Combined Components
The root task's ADS component handles both address spaces and virtual memory regions; ie. it receives requests for allocations and operations on resources of type ADS and VMR. These components are combined for convenience since they are highly interdependent. Both components have individual client api files, but share an RPC protocol (`ads_component_rpc.proto`) and an implementation component (`ads_component.c`).

### Endpoint Type Summary

There are four types of endpoints related to address spaces and virtual memory:
1. **ADS RDE**: Allows the creation of new address spaces. A PD will only have this if it was explicitly shared from another, privileged PD.
2. **ADS Capability**: Allows performing operations on a specific address space. Sny PD can access the ADS resource of the ADS currently bound to its CPU using the `sel4gpi_get_ads_conn()` utility function.
3. **VMR RDE**: Allows the allocation of virtual memory regions within a specific address space. PDs who have their ADS set up for them by another PD can access their VMR RDE by the `sel4gpi_get_bound_vmr_rde()` utility function.
4. **VMR Capability**: Allows mapping or deleting a particular virtual memory region.

```{warning}
For HighJMP PDs, The `sel4gpi_get_bound_vmr_rde()` and `sel4gpi_get_ads_conn()` utility functions only return endpoints to the *originally bound* ADS. Currently, the PD must maintain a reference to its alternate ADS for resource operations. 
A very implementation-specific explanation is provided below.
```

For HighJMP PDs, swapping to a different ADS is an operation done on the CPU resource. In order to update the binded ADS resource and VMR endpoint references within the PD's [shared OSmosis data frame](target_glossary_shared_data), the root task would need to get the PD's CSlot for those endpoints, which isn't always tracked. An ADS endpoint is given to the CPU component during the `cpu_change_vspace` API call, but this is unwrapped into its badge values, and still cannot be used to update the PD's shared OSmosis data.

## App PD Heaps
The Root Task and test PDs all use static-sized and statically allocated heaps, embedded in ELF data. Apps and non-root-task server PDs all have static-sized and *dynamically* allocated heaps, all of which start at the address defined by the `PD_HEAP_LOC` macro. The chosen address is an arbitrary one that is known to be free after a PD's ADS has been set up. The motive for this is convenience in isolating the heap for the HighJMP PD's ADSes.

