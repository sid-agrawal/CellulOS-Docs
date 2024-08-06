(target_resource_server_communication)=
# Communications

## Serving Client Requests
The resource server listens on the endpoint that it provided to the root task when it [created its resource space](target_resource_server_creating_space). Any PD with an RDE for that space will have a badged version of the same endpoint, and thus can send requests to the resource server. The resource server will know that the request came from an RDE because the badge will include a placeholder `BADGE_OBJ_ID_NULL` value for the object ID. Usually, a request from an RDE is to create and/or allocate a resource.

### Creating a Resource
```{image} ../figures/resource_server_create_resource.png
  :width: 600
```

When a resource server wants to create a resource, it notifies the root task through its resource space capability. This does nothing but track metadata. A resource server may want to create resources *before* a client requests them; for example, in the case of a ramdisk server, all of the block resources exist at the beginning of execution. Alternatively, for a file server starting with an empty file system, file resources only begin to exist when clients request them.

To send a resource to another PD, the resource server again makes a request of the root task. The root task has the resource server's endpoint, so it badges the endpoint directly into the CSpace of the recipient PD. The root task returns the slot number in the recipient's CSpace to the resource server, and the resource server passes the slot number to the client PD when it responds to the request.

#### Aside: Sending vs Giving Resources
If PD1 wants to send a resource to PD2, it must have the PD2 capability to do so. This prevents PDs from sending resources to PDs that they should not be allowed to.
In contrast, if a resource server PD3 wants to give a resource from one of its resource spaces to PD2, it only needs PD2's ID. This is for a few reasons:
- Resource servers usually do not have the PD capability for their clients, but they do know the client's ID because it is part of the badge of the client's RDE endpoint.
- We consider resource servers to be trusted entities in the system, so we assume they will not maliciously send resources to PDs that have not requested them.
- During the `give_resource` call, the root task verifies that the caller is truly the manager of the resource space from which it intends to give a resource. If a PD is not a resource server, then it should not have the `RESSPC` RDE, so it will not be able to create a resource space and its calls to `give_resource` will fail.

### Requests on a Resource
Since the root task creates resources as badged versions of the resource server's endpoint, it will also receive invocations / requests for a particular resource. The badge will include the object ID, so the resource server can identify which resource is being invoked. You will most likely want to define a message protocol for your resource server, which uses the IPC buffer to identify the operation and parameters. If using `resource_server_utils`, then you must define the message protocol using NanoPB. 

## Handling Work Requests
The root task may occasionally need to notify a resource server of an event, or request some information from the resource server. All such communications are referred to as "work requests". Currently, the work request types are as follows:
1. Model extraction: Request a subgraph of the model state from a resource server. The request will refer to a particular resource, or an entire resource space. 
    - In the first case, the resource server is expected to prepare a subgraph including the specified resource and any map relations it has. 
    - In the second case, the request also specifies a client PD ID, and the resource server is expected to provide a subgraph including any resources the client PD has access to, plus any map relations they have.
    - A resource server only has to implement *one* of the above cases, and can send an empty response for the other. This allows flexibility for implicit resources; for example, for a file server, a PD may be able to access a number of files if it wishes to open them, but it doesn't have the resource capabilities until it actually opens the files. The file system implements the second case, so it can walk the file system and provide the subgraph that shows a client PD holding every file that it *could* open, not only the files it currently has open. In comparison, a ramdisk server could implement only the first case, since it expects a PD to hold a block resource for every block it has access to.
2. Resource free: Informs a resource server that some instance of one of its resources is freed. For example, if a PD crashed while holding a file resource, we let the file server know. The resource server can implement some policy to decide whether it wants to destroy the resource, return it to a pool, or perform no operation.
3. Resource space destroy: Informs a resource sesrver that one of its resource spaces is destroyed. This can happen due to a cleanup policy. The resource server is expected to clean up any resources or metadata associated with the resource space. For example, if the file server is notified that its file resource space is destroyed, then it should release all of the blocks that the file system was using.

### Receiving Work Requests
```{image} ../figures/deadlock_avoidance_1.png
  :width: 800
```

Every resource server has a notification *bound* to its TCB, meaning that signals to the bound notification will be received on the resource server's regular endpoint. When this happens, the sender badge has the special `NOTIF_BADGE` value. This means that the root task has queued some work for the resource server and signalled the notification (shown by the `seL4_Signal` call in the sequence diagram above). The resource server must actually retrieve the work will the `get_work` call, which returns a NanoPB message with the work type and corresponding parameters. As an optimization, the message may include several sets of parameters, corresponding to several work requests of the same type.

If you are using `resource_server_utils`, the utility's main loop will take care of checking the notification and fetching the work, and will pass the work message to the resource server's `work_handler` callback.

### Responding to Work Requests
Currently, the root task expects a response to all types of work requests. For *resource free* or *resource space destroy* tasks, it just expects an acknowledgement that the resource server is done processing, which the resource server sends via the `finish_work` RPC call. For *model extraction* tasks, it expects the resource server to send a subraph of the model state, sent via the `send_subgraph` RPC call.

#### Preparing a Model State
Resource servers need to prepare a portable model state subgraph for `send_subgraph` calls. The steps to do so are as follows:
1. Calculate the number of pages needed for the model state: This can be done by calculating the number of nodes and edges, multiplying it by `sizeof(gpi_model_state_component_t)`, and adding `sizeof(model_state_t)`.
2. Allocate an MO of the necessary size, attach it to the current address space, and initialize a model state at the start of the memory region. We use the functions in `model_exporting.h` to manage the model state. The model state can be initialized such that the nodes/edges will be stored in the MO's space following the model state struct. The utility function `resource_server_extraction_setup` will handle this step.
3. Add nodes and edges to the subgraph using initialized model state and the functions from `model_exporting.h`.
    - You can add edges in two ways. The first way is to create two nodes, and add an edge between them with `add_edge`. Alternatively, you can avoid adding both nodes using `get_resource_id`, `get_pd_id`, etc. and the `add_edge_by_id` function. This adds edges without any endpoint node, which makes the subgraph incomplete, but it is ok if you expect the node to be added elsewhere. For example, the file server may include a map edge to a block resource node, expecting that the block resource node will already be added to the model state by the root task.
4. Use the function `clean_model_state` to clean any local memory used for the model state, send the MO to the root task with `send_subgraph`, unnattach the MO from the local address space, and deallocate the MO. The utility function `resource_server_extraction_finish` will handle this step.

(target_resource_server_storing_reply)=
## Storing Reply Capabilities

If a resource server crashes while it is in the process of serving a client request, then the client will remain blocked on the resource server's endpoint indefinitely. To handle this issue, resource servers should store the [reply cap](target_glossary_reply_cap) immediately after receiving a request from a client. They should use `sel4gpi_store_reply_cap`, which moves the reply cap from the resource server's TCB to its CSpace, and stores a reference to it in the PD's [shared data page](target_glossary_shared_data). If you are using the `resource_server_utils`, the main loop will take care of this for you.

Once the server has completed the request, it clears the reply capability from the shared data page using `sel4gpi_clear_reply_cap`. Thus if the resource server crashes while serving a request, the root task is able to use the reply capability to reply with an error message to the waiting client.

```{image} ../figures/storing_reply_cap.png
:width: 500px
```

```{note}
For resource servers to call `sel4gpi_store_reply_cap`, they need access to their own CSpace, and thus they need their own CSpace root capability. The GPI Server does not currently differentiate between resource server and app PDs, so all PDs get access to their CSpace, although apps do not use it. Eventually, apps should not have access to their CSpace at all. Two potential solutions:
- The {doc}`PD Configuration interface </user/flexible_pd_config>` includes an option to specify whether a PD is a resource server or not, and only explicit resource server PD get access to their CSpace.
- Resource servers get a special CNode to store their reply cap, and only get access to this CNode, but not their entire CSpace.
```