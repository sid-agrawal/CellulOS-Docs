(target_resource_server_requirements)=
# Requirements

Resource servers are a semi-trusted entity within the system. There are some expectations of a resource server to ensure correct functioning of the system:
- We assume that resource servers do not act in an intentionally malicious way (eg. sending un-requested resources to another PD to deplete its CSpace).
- Resource servers use the root task's API to create a resource space, create resources in the space, send resources to other PDs, and delete / revoke resources. This can be enforced by preventing a resource server from performing operations on its own CSpace, so it can only perform these operations through the root task.
- Resource servers truthfully respond to requests from the resource server (see the section on [resource server communications](target_resource_server_communication)).
- For simplicity, we assume that only one PD manages a particular resource space, and a resource space is associated with only one endpoint. It would be possible to have a system where more than one PD manages a resource space (eg. multiple threads), but the implementation does not currently support this.
- Resource servers store the reply cap for a client's request as soon as they receive the request. The reason for this is explained [here](target_resource_server_storing_reply).