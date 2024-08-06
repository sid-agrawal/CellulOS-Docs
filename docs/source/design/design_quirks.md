# Design Quirks

This captures some quirks of the design that my be unintuitive.

(target_design_ads_capability)=
## ADS Capability

## App PD Heaps
The Root Task and test PDs all use static-sized and statically allocated heaps, embedded in ELF data. Apps and non-root-task server PDs all have static-sized and *dynamically* allocated heaps, all of which start at the address defined by the `PD_HEAP_LOC` macro. The chosen address is an arbitrary one, known to be free. The motive for this is convenience in isolating the heap for the HighJMP PD's ADSes.

