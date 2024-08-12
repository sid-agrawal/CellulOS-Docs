# Implementation Glossary

Some terms are specific to the implementation, or differ from the terms used in writing about OSmosis. These terms are listed here.

## General seL4 Terms
- **TCB** (Thread Control Block): The TCB is the schedulable entity, which has an associated VSpace, CSpace, and register state. From the [sel4 13.0.0 manual](https://sel4.systems/Info/Docs/seL4-manual-13.0.0.pdf):
> seL4 provides threads to represent an execution context.
> [...]
>  Without MCS, processor time is also represented by the thread abstraction. A thread is represented in seL4 by its thread control block object (TCB).
    - Note that  CellulOS uses the non-MCS version of the kernel, so the second sentence applies.
(target_glossary_asid_pool)=
- **ASID Pool**: ASID Pools are repositories for address space identifiers, where a number of pools may exist in the system, and each is a subset of a virtual ASID space. From the [seL4 spec](https://sel4.systems/Info/Docs/seL4-spec.pdf):
> ASIDs are associated with page directories (PDs) and define the virtual address space of a thread. [...] Since ARM hardware supports only 255 different ASIDs, seL4 on ARM supports the concept of virtual ASIDs that are mapped to hardware ASIDs managed in a two-level structure. The user manages only the second level of this structure: the asid pool. An asid pool can be seen as a set of virtual ASIDs that can be connected to and disconnected from page directories.
(target_glossary_reply_cap)=
- **Reply Cap**: When a PD calls `seL4_Call` on an endpoint and the message is delivered to the receiver, the kernel creates a temporary "reply endpoint" and places the capability in the receiver's TCB (since CellulOS uses the non-MCS version of the kernel). The sender waits on the temporary endpoint, so the receiver can reply using the reply capability to finish the call.

## General CellulOS Terms
<mark><-- May be here or somewhere we need to add diagram of the system that shows seL4, i
tRT and the different components in it </mark>

- **Root Task**: The trusted PD that runs above the seL4 microkernel. In the sel4test project, the root task includes the *test driver* thread, which sets up tests and listens for any messages / interrupts / test results. When CellulOS functionality is enabled, the root task has a second thread which is the *GPI Server*.
(target_glossary_gpi_server)=
- **GPI Server** (General Purpose Isolation Server): GPI is an older name for CellulOS, and the GPI Server is the orchestration point for all CellulOS functionality. When we talk about PDs calling the root task, it is the GPI Server's endpoint that they communicate with.
(target_glossary_rde)=
- **RDE** (Resource Directory Entry): This is the implementation analogue to a request edge. The **resource directory** is the data structure that maintains a PD's request edges, and a **resource directory entry** contains the badged endpoint for a resource server. An RDE is for a particular resource type and resource space. Conceptually, invoking the badged endpoint is making a request along a request edge.
(target_glossary_shared_data)=
- **PD's Shared Data Page**: Every PD has a single page shared with the root task, which contains the `osm_pd_shared_data_t` struct. This page mostly consists of the initialization data, like the resource directory data structure.

## Capability Types
- **Capability Type**: In CellulOS we refer to "capability types", the analogue of "resource types", which are actually enum values that can be set in the badge of a badged endpoint capability. They are not types of capabilities in the raw seL4 sense, but the root task treats them as resource types. The core capability types are detailed in the entries below. The core capability types are handled by their respective components in the root task. Other capability types can be created dynamically during system operation, and are handled by resource servers.
- **ADS** (Address Space): The ADS capability grants the ability to manage an address space; reserve virtual memory, attach physical memory, attach the address space to a TCB, or make a copy. See [design quirks](target_design_ads_capability) for more details.
- **CPU**: The CPU capability is the virtual equivalent of a physical CPU, as a virtual memory region is to a physical memory region. It represents an *execution context*, and will be mapped to a physical CPU when the context is actively being executed. In effect, the CPU capability provides access to a particular TCB. <mark><-- this description may need rewording </mark>
- **EP** (Endpoint): The EP is an "implementation-only" capability - it has no resource type in the model, because the endpoint is always the implementation of an *edge*. <mark> Add a link to a page that describes, with seq diagrams, the role of endpoints to form edges </mark>
- **MO** (Memory Object): An MO is an abstraction over physical pages, which allows us to pass around an arbitrary number of contiguous physical pages as one resource. 
- **PD** (Protection Domain): The PD is a capability type in the implementation, but not a resource type in the model. The PD capability provides the ability to set up a PD, send resources to it, share RDEs with it, and terminate. A PD also has access to its *own* PD capability, which it can use to allocate/free slots in its CSpace, get work that the root task has scheduled for it (see [resource server communications](target_resource_server_communication)), or notify the root task that it is exiting.
- **RESSPC** (Resource Space): The RESSPC is also a capability type in the implementation, bu tnot a rersource type in the model. It provides the ability to create/delete/revoke resources within the space, and destroy the entire space.
- **VMR** (Virtual Memory Region): The virtual memory region capability may be an implicit or explicit resource in the system. If a PD requests to reserve a region of virtual memory via an ADS capability, the request returns an explicit VMR capability. The VMR capability can be invoked later on to attach an MO to the reservation. If a PD instead requests that an MO be attached to an ADS directly, then it does not receive a VMR capability in return, since we have found no situation where it is needed (thus the VMR resource is implicit).
