# Endpoint Component
The endpoint component in the Root Task (RT) exists for allocating and managing seL4 endpoints in the same way that CellulOS resources are managed. This is required due to multiple PDs holding references to the same endpoints, which needs to be tracked by the RT to handle cleanup of the endpoint.

It can be a bit confusing to work with due to it comprising of two different seL4 endpoints.

To prevent confusion, **badged endpoint** refers to the endpoint that a resource server listens on. **Raw endpoint** refers to the underlying endpoint that a PD has allocated.
**GPI endpoint** will refer to the badged endpoint (which the RT's endpoint component listens on) that represents an regular endpoint.

The endpoint "resource" violates some of the principles that all other CellulOS resources follow:
1. Non-resource-server PDs refer to a resource by a badged endpoint that the resource server listens on
2. Only the resource server may access the raw resource which the badged endpoint represents.
3. Operations performed on the resource are done by the resource server.

Endpoints differ in (2) and (3), where non-resource-server PDs can access the raw underlying resource (the raw endpoint), and thus can perform operations which the endpoint component will not be aware of.

## Allocating Endpoints
This is done through the typical [ep_client_component_connect()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L45) call, which typically returns the raw endpoint to the PD as well.

## Sending Endpoints to Other PDs
When sending an endpoint using `pd_client_send_cap()`, one should pass in the GPI endpoint, which will get unwrapped by the Root Task's endpoint component. Only the GPI endpoint will be copied to the CSpace of the receiving PD.

You could theoretically send the raw endpoint, but this will be untracked and cause problems when the endpoint needs to be freed.

## Retrieving the Raw Endpoint
A PD which has only the GPI endpoint can retrieve the raw one in its own CSpace using the [ep_client_get_raw_endpoint()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L66) API call.

A PD can also retrieve the slot of the raw endpoint in a different PD's CSpace using [ep_client_get_raw_endpoint_in_PD()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L55).

## Sequence of Allocating and Receiving Endpoints
This is the general sequence of how endpoints are allocated and sent between PDs.

```{image} ../figures/endpoint_alloc.png
    :width: 700px
```

## Badging Tracked Endpoints 
The raw endpoint represented by GPI endpoints are unbadged by default. A PD may wish to badge these endpoints, e.g. a VMM wants to badge a fault endpoint so that it can distinguish VM faults from interrupt notifications. This can be done using the `ep_client_badge()` API call, which simultaneously badges the raw endpoint into a target PD's CSpace **and** creates a copy of GPI endpoint. 

The RT currently **does not** store the badge value of the raw endpoint, as this would require complex metadata. As a consequence, if the target PD tries to retrieve the raw endpoint from the GPI endpoint, it will received the **unbadged** version of the raw endpoint.

```{image} ../figures/endpoint_component_badge.png
    :width: 700px
```

## Tracked Endpoints for Handling Faults
All fault endpoints are allocated as a tracked endpoint, and the raw endpoint is copied into a CPU's TCB *without* increasing the tracked endpoint's reference count (see [](#quirk-about-fault-endpoints) below). This is done within the PD Creation component upon configuring a new PD's fault handler.

```{image} ../figures/fault_endpoints.png
    :width: 700px
```

## Resource Server Listening Endpoints
Resource servers use tracked endpoints for the resource endpoint which they listen on. Similar to how fault endpoints are configured for created PDs, when resource servers register with the RT, they send the raw endpoint, not the GPI endpoint. This is because the endpoint that gets registered with the RT will be badged and used as references to resources, so it no longer represents a regular endpoint. 

The raw listening endpoint will get freed when resource servers are cleaned up (if no other non-RT PD holds the GPI endpoint), performs `seL4_CNode_Revoke()`, which deletes all the badged versions of the endpoint (representing resources). Any PDs still referencing the resource representation of the endpoint will be met with an `Invalid capability` error.

```{image} ../figures/resource_serv_endpoints.png
    :width: 700px
```

## Merging Fault and Resource Server Endpoint Allocation
As seen in [](#tracked-endpoints-for-handling-faults) and [](#resource-server-listening-endpoints), endpoints used for either
handling faults or as resource server endpoints do not differ very much in how they're allocated. They're
implemented differently simply due to faults currently being treated as a separate concept from an RDE. In both cases, the general sequence of events is:
1. Allocate a tracked endpoint
2. Configure something with the tracked endpoint's raw, underlying endpoint
3. Upon exiting (and if the tracked endpoint's refcount has decreased to 0), revoke all children of the tracked endpoint

The process of allocating and configuring fault endpoints can be merged with resource server registration, if the fault handler
was treated as a resource server (for faults). The fault handler can then register a raw endpoint with the Root Task, which
would need to detect that the PD is registering itself as a fault handler (perhaps with a new GPI cap type, `GPICAP_FAULT`, or similar). Once the Root Task detects that the registrant is a fault handler, it should perform `seL4_TCB_Configure()` with the raw endpoint as the fault endpoint for some target PD, rather than badge the raw endpoint as a resource endpoint.

## Quirk about Fault Endpoints
When a fault endpoint is allocated and configured in the CPU of a new PD, it exists in three different capability containers:
1. The CSpace of the PD which allocated it
2. The CSpace of the PD for which the faults will be handled
3. The TCB of the PD for which faults will be handled

However, the third reference to the endpoint is not tracked as a reference by the RT. The reason for this is that the `cpu_client_config()` API call requires three unwrapped caps (the maximum that seL4 supports) for the `seL4_TCB_Configure()` syscall: the ADS to bind with the TCB, the PD which contains the CSpace to bind, the MO for the IPC buffer. 
To increase the reference count of the fault endpoint, we would need to send another unwrapped cap. This could be worked around by breaking the `cpu_client_config()` call into multiple IPCs, but not counting the reference from the TCB is fine for a few reasons:

1. Freeing an endpoint involves revoking the endpoint, so the reference to the fault endpoint in the TCB will get deleted by this revocation
2. A fault endpoint is typically freed if no PDs hold it. If a CPU object still exists despite the PD of which it is bound to having exited or terminated, then there will neither be a listener or sender of the fault endpoint. If the CPU object is to be reused, it will need to be reconfigured regardless, so it is fine for the fault endpoint to be revoked from it. 
