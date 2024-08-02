(target_spawning_pds)=
# Spawning PDs

```{attention}
WIP
```

To do anything useful in CellulOS, we need to create and run PDs. This is primarily done by specifying various configuration options to the `pd_creation` module, which, in OSmosis-terminology, installs the necessary nodes and edges for running a new PD.


## Pre-requisites for PD Creation
CellulOS currently does not provide a single "spawning" server which creates PDs and runs them. In order to spawn PDs, a "creator" PD must exist with RDEs to the PD, MO, ADS, CPU, and EP servers. 
With our current `sel4test` infrastructure, each test PD ran by the test driver has been given RDEs to all servers in the system, allowing it to act as the creator PD.

### Reference for Creation
The `pd_creation` module creates PDs in reference from the creator PD. The effect of this is that the created PD can only access a subset of the resources and RDEs which are held by the creator PD.

## Spawning a Process-like PD

