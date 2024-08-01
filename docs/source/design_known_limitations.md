# Known Limitations
This page details undesired behaviours or missing pieces of the current system, pending future development.

(target_limitations_badge_scalability)=
## Badge Scalability
```{image} images/badge_bits.png
  :width: 300
```
We use the 64-bit badge value of endpoint capabilities to track their purpose - either as RDEs or as resources. For convenience and efficiency, all relevant information is stored / retrieved by masking the badge itself. However, this introduces a scalability problem, especially since we cannot have more than 255 resource types or resource spaces. Eventually, we should replace the badge value with some unique ID that can be used to find a corresponding data structure. For example, the badge value could be the ID for a hash table maintained by the corresponding resource server (or root task), and the value is a stucture containing the cap type, permissions, space ID, client ID, and object ID with large-enough fields for scalability.

## Garbage Accumulation
We have tried to eliminate garbage accumulation for long term use of the system, but there are a small number of known sources of garbage.

### ASID Pools
On aarch64, an [ASID pool](target_glossary_asid_pool) contains enough space for up to 512 VSpaces. If we run out of space in the default ASID Pool due to a large number of address spaces in the system, we can create up to 128 (for aarch64) ASID pools, each of them taking a 4K page of memory. If the address spaces are being destroyed as well, some of these pools may become unused. We would need to introduce some reference tracking to identify when an ASID Pool can be destroyed. Note that this source of garbage will not actually occur in the system currently, since the [badge scalability](target_limitations_badge_scalability) issue will already prevent us from creating more than 0xFE = 254 address spaces.
    - As a side note, we learned that destroying a VSpace does free its assigned ASID. However, destroying all the VSpaces assigned to an ASID pool will not automatically destroy the pool.

### Revoked Slots
When we revoke a resource from a PD, we do not free the slot in its CSpace. This is so that the slot will not get filled with some other resource, potentially causing the PD to use the new resource unknowingly while it tries to use the old resource. If the system has a lot of revoked resources, these empty revoked slots could eventually fill up a CSpace. The alternative would be to have a handler in each PD to be notified when resources are revoked.

## Model State Extraction

### Partial State
The system is currently only intended to extract the full system's model state, and not just a subgraph centered on a particular PD.
When a PD requests a model extraction, the root task iterates over all PDs in the system and extracts their state. Alternatively, we might want the ability to extract the model state of only one PD. This process could proceed as follows:
- The root task iterates over the PD's resource directory entries
    - Each entry is added to the model state
- The root task iterates over the PD's held resources
    - If the resource is a core resource, then the root task can add all relevant information to the model state
    - If the resource is not a core resource, the root task reaches out to the corresponding resource server for a subgraph
        - If the subgraph includes resources from other resource servers, the root task will need to recursively reach out to *those* resource servers as well
    - *If the resource is a PD*: This is still an open question, do we recursively dump the PD as well?

(target_limitations_runtime_metrics)=
### Runtime Metrics
The system does not currently support calculating the model metrics (RSI & FR) at runtime. It would be possible to do so if we modify the model extraction utility to store the graph in a traversible data structure and implement the calculation algorithms.

## Resource / PD Cleanup

### Fault Handler Dependencies
The implementation does not explicitly track a "fault edge" between a PD and its fault handler, so it is unable to clean up a PD if its fault handler crashes. We suspect that this would be a non-configurable option to recursively follow fault edges and clean up all PDs along the path.

## PD Creation

### Shared ADS Configuration Options
For scenarios with partially-shared address spaces, the configuration options allow for particular regions to be shared (same physical pages) or disjoint (separate physical pages). If a region is shared, it will be shared *at the moment the second ADS is created*. If one of the address spaces later modifies the region (eg. by replacing one or more physical pages), the second address space will not be updated to match. We are unsure whether or not we will add the option to update the shared regions in this way.