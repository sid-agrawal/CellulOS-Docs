# Creation
A resource server is started like any other PD, but it will usually need some particular RDEs (`MO`, `VMR`, `RESSPC`, and potentially others), an endpoint to listen on, and a resource space so it can begin serving resources. The below diagram is not the *only* way that a resource server could start, but it is the way that our resource servers currently start.

```{image} figures/resource_server_startup.png
  :width: 600
```

(target_resource_server_creating_space)=
## Creating a Resource Space
As shown in the sequence diagram above, when a resource server starts, it will need to create a *resource space* so that it can start providing resources. It makes a request to the root task, including a string name for the resource type that the space will contain, the endpoint that the resource server will listen on, and the ID of the PD that started the resource server.
- The resource type name is something like "BLOCK" or "FILE", which should uniquely identify the resource type, but it is not necessary to be unique among all resource servers in the system. If the root task has never seen this resource type before, it will assign a new capability type (a number) to it, which can be used as the capability type in badges. If the root task *has* seen this resource type name before, then it will return the previously-assigned capability type.
- The endpoint that the resource server will listen on is provided so that the root task can badge it to create RDEs and resources for the resource space.
- The resource server must provide the ID of the PD that started it, so that the root task can add the first request edge from the parent PD to the resource server's new space. Thus, the parent PD becomes the first client. This is how a new RDE is added to the system, and the parent PD may then choose to share the RDE with other PDs.

## Utility Libraries
Any PD that satisfies the [resource server expectations](target_resource_server_requirements) can be a resource server, but we have created a simple framework to facilitate creation/operation of resource servers.
- `resource_server_clientapi.h` provides functions to start a resource server PD from an executable.
- `resource_server_utils.h` provides some common functionality for resource servers.
  - The resource server calls `resource_server_start` to initialize the server. The utility creates a default resource space, notifies the parent PD that the server has started, and enters the message-handling loop.
  - The resource server handles requests through callback functions provided to `resource_server_start`.
    - The `request_handler` callback is called when client PDs make requests through the resource server's endpoint, and passed the message contents.
    - The `work_handler` callback is called when the root task returns work for the resource server PD to complete. The utility function's main loop handles checking for a work notification from the root task, fetching work if there is a notification, and then passes the response message to the `work_handler`.
  - The utility requires that an nanopb RPC protocol is defined for the resource server.