# PD Runtime Setup

```{attention}
WIP
```

There are currently three different setup methods which the `pd_creation` module employs based on what the ADS and CPU configurations imply. 

1. If both the ELF code and data segments between the creator and created PD are disjoint, the entire C runtime must be initialized.
2. If both the ELF code and data segments are shared, it's inferred that the C runtime must have already been initialized in the data segment of the creator PD, and thus only the TLS needs to be set up. 
3. If the CPU has been elevated, it's assumed that the PD is a guest OS and nothing is set up. 

## Passing Arguments to the PD

