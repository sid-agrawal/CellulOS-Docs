# Design Quirks

This captures some quirks of the design that my be unintuitive.

(target_design_ads_capability)=
## ADS Capability
The ADS component of the root task handles both address space and VMR allocation.  ADS allocation is equivalent to resource space (RESSPC) allocation, and although there is a separate endpoint for RESSPCs, ADS allocation is still a separate component due to both legacy code and convenience. The ADS and VMR components are also combined for convenience, but it can cause some confusion during usage.

There are three different endpoints, with different badges, that can be used to communicate with the ADS/VMR server:
1. The ADS RDE: To allocate new address spaces 
2. The VMR RDE: To allocate new VMRs for a specific ADS
3. The ADS resource: To perform operations on a particular address space

The VMR RDE endpoint has a separate CellulOS cap type from the ADS RDE endpoint, and the ADS component accepts requests from badges of both types.
When an ADS is allocated, the *VMR RDE* endpoint is installed in client PD and only the *ADS resource* endpoint is returned from the allocation API call.  **Attemping to attach MOs with the returned endpoint will result in a server error.**
The client PD can retrieve the VMR RDE endpoint of the newly allocated ADS by using one of the utility functions in `pd_utils`, `sel4gpi_get_rde_by_space_id(ads_id, GPICAP_TYPE_VMR)`, where `ads_id` is the ID of the allocated ADS that's also returned by the ADS allocation API call.

```{note}
Returning root task IDs of resources may seem like poor design, and while we do agree, the ID returned is only relative to other ADSes and could easily be masked by the ADS component. We leave implementation of this feature to future improvements.
```

PDs who have their ADS set up for them by another PD can access their VMR RDE by the `sel4gpi_get_bound_vmr_rde()` utility function. Similarly, any PD can access the *ADS resource* of the ADS currently binded to its CPU by the `sel4gpi_get_ads_conn()` utility function.
The ADS RDE endpoint is only accessible to PDs who have been explicitly given this RDE from another priviledged PD.

```{warning}
For HighJMP PDs, The `sel4gpi_get_bound_vmr_rde()` and `sel4gpi_get_ads_conn()` utility functions only return endpoints to the *originally bounded* ADS. Currently, the PD must maintain a reference to its alternate ADS for resource operations. 
A very implementation-specific explanation is provided below.
```

For HighJMP PDs, changing ADSes is an operation done on the CPU resource. In order to update the binded ADS resource and VMR endpoint references within the PD's [shared OSmosis data frame](target_glossary_shared_data), the root task would need to get the PD's CSlot for those endpoints, which isn't always tracked. An ADS endpoint is given to the CPU component during the `cpu_change_vspace` API call, but this is unwrapped into its badge values, and still cannot be used to update the PD's shared OSmosis data.

## App PD Heaps
The Root Task and test PDs all use static-sized and statically allocated heaps, embedded in ELF data. Apps and non-root-task server PDs all have static-sized and *dynamically* allocated heaps, all of which start at the address defined by the `PD_HEAP_LOC` macro. The chosen address is an arbitrary one that is known to be free after a PD's ADS has been set up. The motive for this is convenience in isolating the heap for the HighJMP PD's ADSes.

