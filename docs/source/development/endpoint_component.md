# Endpoint Component
The endpoint component in the Root Task (RT) exists for allocating and managing seL4 endpoints in the same way that CellulOS resources are managed. This is required due to multiple PDs holding references to the same endpoints, which needs to be tracked by the RT to handle cleanup of the endpoint.

It can be a bit confusing to work with due to it comprising of two different seL4 endpoints.

To prevent confusion, **badged endpoint** refers to the endpoint that a resource server listens on. **Raw endpoint** refers to the underlying endpoint that a PD has allocated.

The endpoint "resource" violates some of the principles that all other CellulOS resources follow:
1. Non-resource-server PDs refer to a resource by a badged endpoint that the resource server listens on
2. Only the resource server may access the raw resource which the badged endpoint represents.
3. Operations performed on the resource are done by the resource server.

Endpoints differ in (2) and (3), where non-resource-server PDs can access the raw underlying resource (the raw endpoint), and thus can perform operations which the endpoint component will not be aware of.

## Allocating Endpoints
This is done through the typical [ep_client_component_connect()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L45) call, which typically returns the raw endpoint to the PD as well.

## Sending Endpoints to Other PDs
When sending an endpoint using `pd_client_send_cap()`, one should pass in the badged endpoint, which will get unwrapped by the Root Task's endpoint component. Only the badged endpoint will be copied to the CSpace of the receiving PD.

You could theoretically send the raw endpoint, but this will be untracked and cause problems when the endpoint needs to be freed.

## Retrieving the Raw Endpoint
A PD which has only the badged endpoint can retrieve the raw one in its own CSpace using the [ep_client_get_raw_endpoint()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L66) API call.

A PD can also retrieve the slot of the raw endpoint in a different PD's CSpace using [ep_client_get_raw_endpoint_in_PD()](https://github.com/sid-agrawal/sel4-gpi/blob/cellulos/libsel4gpi/include/sel4gpi/endpoint_clientapi.h#L55).

## Resource Server Listening Endpoints
Resource servers allocate the endpoints which they listen on via this endpoint component. However, when they register with the RT, they send the raw endpoint, not the badged endpoint. This is because the endpoint that gets registered with the RT will be badged and used as references to resources, so it no longer represents a regular endpoint. 

The raw listening endpoint will get freed when resource servers are cleaned up (if no other non-RT PD holds the badged endpoint), performs `seL4_CNode_Revoke()`, which deletes all the badged versions of the endpoint (representing resources). Any PDs still referencing the resource representation of the endpoint will be met with an `Invalid capability` error.

## Quirk about Fault Endpoints
When a fault endpoint is allocated and configured in the CPU of a new PD, it exists in three different capability containers:
1. The CSpace of the PD which allocated it
2. The CSpace of the PD for which the faults will be handled
3. The TCB of the PD for which faults will be handled

However, the third reference to the endpoint is not tracked as a reference by the RT. The reason for this is that the `cpu_client_config()` API call requires three unwrapped caps (the maximum that seL4 supports) for the `seL4_TCB_Configure()` syscall: the ADS to bind with the TCB, the PD which contains the CSpace to bind, the MO for the IPC buffer. 
To increase the refcount to the fault endpoint, we would need to send another unwrapped cap. This could be worked around by breaking the `cpu_client_config()` call into multiple IPCs, but not counting the reference from the TCB is fine for a few reasons:

1. Freeing an endpoint involves revoking the endpoint, so the reference to the fault endpoint in the TCB will get deleted by this revocation
2. A fault endpoint is typically freed if no PDs hold it. In this case, the listener of the endpoint has decided to explicitly free it, or it has exited. If there still exists any PD which depends on the listener PD for fault handling (causing a reference to the endpoint from this PD's TCB), the fault endpoint will have no receiver regardless of whether the endpoint has been freed or not. Thus, it is not necessary to keep the fault endpoint around if a TCB is still referring to it.
