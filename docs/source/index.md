# Welcome to CellulOS's Wiki!

Welcome to the Wiki for the CellulOS (pronounced: Cellulose). 
CellulOS adheres to the OSmosis model, which makes it easy to extract 
the OSmosis model state at runtime.

## What is OSmosis?

The OSmosis model is a DAG that permits us to reason
about isolation and sharing. The DAG has three types of
nodes: 
- protection domains, which are the entities running on a
system (e.g., threads, processes, containers, kernel, hypervisor)
- resources, which can be virtual or physical (e.g., an
application’s virtual memory, its files, the OS state it can
query, the processors on which it is allowed to run, and the
DRAM pages it can use)
- resource spaces, which provide context for resources (e.g., virtual address space and mount
namespaces).

The edges of the DAG precisely describe how nodes interact; e.g. 
how a protection domain’s resources interact with
each other and with resources external to the protection
domain.

Edges can be of four different types: 
- a *subset-edge* from a resource to a resource space (e.g., a code region is a subset
of the virtual address space) 
- a *map-edge* from one resource to another (e.g., a virtual page mapping to a physical page) or
one from one resource space to another 
- a *request-edge* that indicates that a PD can request resources from another PD (e.g., a process
asks the kernel for more virtual memory)
- a *hold-edge* that indicates a PD has direct access to a resource

### What can OSmosis help us with?
The long term goal of the OSmosis project is to answer questions such as:

* Given an isolation mechanism, what is the Trusted Computing Base implementing that mechanism?
* Is there a way to compare different similar yet distinct isolation mechanisms (e.g., Intel's MPK, ARM's MTE, CHERI)?
* Is there a way to compare different VMM architectures (e.g., Xen, KVM)?
* Is it possible to build a single framework to explore the entire design space of isolation mechanisms?

More details of the OSmosis model are available at in the following 
[write-up](https://sid-agrawal.ca/agrawal_osmosis_2024.pdf).

## What is CellulOS?
CellulOS is an OS personality built on the [seL4 microkernel](https://sel4.systems/).
In other words, it is a user-space server that
implements the OSmosis framework. 
```{image} ./figures/CellulOS_Arch.png
    :width: 700px
```

We used seL4 as the basis for the CellulOS prototype for two main reasons. 
seL4’s capabilities are a natural fit to delegate and track resources
across different PDs. 
As a microkernel, seL4 provides only low-level abstractions (page table manipulations), allowing
us to design higher-level abstractions (e.g., process or VM creation). 

CellulOS is one realization of OSmosis, but it is not the only possible one. 
We show what extraction of the OSmosis model state can look like from [Linux's `/proc`](target_proc_model_state).


### What can you do with CellulOS?
CellulOS is `RESEARCHWARE`; i.e. meant to demonstrate the ideas proposed by the OSmosis model.
That said, we can do many things that an OS can do, and some that a regular OS cannot. 

* Create process, threads, namespaces (some), and virtual machines.
All the different types of isolation mechanisms are created using 
[CellulOS' Generic API to create Protection Domains](target_flexible_pd).
* The VMM implementations in *CellulOS*, is ported from seL4's Microkit[](target_virtual_machine_monitor).
* [Extract the OSmosis model state](target_model_state) (at runtime) and import into Neo4j (offline).
* Specify [flexible cleanup policies](target_configuration_cleanup_policy), stating which PDs should be cleaned up when a given 
PD terminates based on their dependencies (OSmosis edges).

We have ported SQLite and bare-bones `libc` to work with CellulOS.
There is no interactive shell, so all the functionality is wrapped inside the [testing framework](target_system_tests).
The testing framework is a heavily modified version of the [sel4test](https://docs.sel4.systems/projects/sel4test/). 

An exhaustive list of what all is ported to CellulOS is available [here](target_system_tests).


```{toctree}
:maxdepth: 1
:caption: User Guide
:hidden:
user/getting_started
user/executing_code
user/user_configuration_options
user/cellulos_tests
user/model_state
user/running_benchmarks
```

```{toctree}
:maxdepth: 1
:caption: Development
:hidden:
development/resource_servers
development/resources
development/implementation_glossary
development/virtual_machine_monitor
development/troubleshooting
development/endpoint_component
```

```{toctree}
:maxdepth: 1
:caption: Design
:hidden:
design/design_overview
design/design_apps
design/design_decisions
design/design_quirks
design/design_known_limitations
```

# Contributors
The CellulOS is built at the [University of British Columbia's Systopia Lab](https://systopia.cs.ubc.ca/)
under the larger OSmosis project.

The development of the CellulOS prototype is mainly done by:
* Arya Stevinson (Jan-Aug 2024)
* Linh Pham  (Jan-Aug 2024)
* [Sid Agrawal](https://sid-agrawal.ca) (Jan 2021 - present)

The development of the OSmosis model is mainly driven by Sid Agrawal with inputs from:
* Students: Arya Stevinson | Linh Pham | [Shaurya Patel](https://shauryapatel1995.github.io/)
* Faculty: [Prof. Margo Seltzer](https://seltzer.com/margo) | [Prof. Reto Achermann](https://retoachermann.ch/) | [Prof. Aastha Mehta](https://aasthakm.github.io/)