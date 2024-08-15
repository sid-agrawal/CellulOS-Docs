# Resources in CellulOS

```{attention}
This may not be the right place for this page, it may be moved later.
```

## Resource Directory Entries
A PD's resource directory consists of the [resource directory entries](target_glossary_rde) in its [shared data page](target_glossary_shared_data). Some entries will be filled out when the PD is created, but the contents may change over a PDs lifetime. There are some principles that define how the system handles resource directories:
1. Every RDE is a badged version of a resource server's endpoint. The root task keeps an un-badged copy of each, so that it may re-badge it for new clients.
    - The badge includes the capability type, space ID, permissions (unused), and client ID. The client ID is included in this unforgeable badge so that resource servers will be able to tell what client is connecting to them. The object ID of the badge is set to `BADGE_OBJ_ID_NULL`.
2. A PD can share with another PD an RDE that is already in its own resource directory. The root task will re-badge the original copy of the resource server endpoint for the new client.
    - This requires that the sending PD has the recipient PD's resource capability.
    - When the endpoint is re-badged, the only value that changes is the client ID.
3. A PD can choose to remove one of its RDEs through an API call to the root task. This could be useful if a PD wants to remove association from a resource server so it will not be cleaned up by a [cleanup policy](target_configuration_cleanup_policy) if a resource server crashes.
4. When a PD creates a new resource space, it must specify an initial client PD, which will receive the first RDE for the space.
    - Typically, when a PD spawns a resource server, it includes its own PD ID as an argument so that it will receive the RDE for the server's first resource space.
    - When a resource server creates additional resource spaces, such as namespaces, it should be at the request of some other PD which will be the recipient of the first RDE for the space.

### Getting RDEs
PDs can access their own resource directory using the functions in `pd_utils`:
- `sel4gpi_get_rde(int type)`: Gets the first endpoint for the given type from the current PD's resource directory.
    - But how does a PD know the type code? For core capability types, the codes are statically defined in the `gpi_cap_t` enum. For other types, the root task includes the type's "friendly name" in the shared data frame, so PDs can use `sel4gpi_get_resource_type_code` to find a resource type code for any RDE they have. 
    - For example, the file system creates the resource type "FILE", so PDs can find the RDE for files with `sel4gpi_get_rde(sel4gpi_get_resource_type_code("FILE"))`
- `sel4gpi_get_rde_by_space_id(gpi_space_id_t space_id, gpi_cap_t type)`: Gets the endpoint for the given type and space ID from the current PD's resource directory.
    - A PD would use this if it has RDEs for multiple spaces of the same resource type. For example, if it has access to two file namespaces. 
    - A resource server is responsible for returning the space ID to the PD when the PD requests a new resource space.
    - Alternatively, if a PD is sharing RDEs with other PDs, then the sender is responsible to provide arguments or send a message to indicate the space IDs if necessary.

## Tracking Held Resources

(target_hold_registry)=
### Hold Registry

The root task maintains the metadata that tracks which resources each PD holds. This is stored in the *hold registry*, a property of the *pd_t* structure, and uses the [registry util](target_registry_library). The key of the hash table is the 64 bit "compact resource ID" that uniquely identifies a resource in the system; in other words, the key is a badge value created with `gpi_new_badge(type, 0, 0, space_id, object_id)`. The hold registry is updated every time a PD has a resource added or removed.

It is possible for a PD to have more than one copy of a resource. For example, a PD might open the same file to two different file descriptors, or two other PDs might send it the same MO. When this happens, the root task reuses the same resource capability in the PD's CSpace for all references to the resource. To track this, entries of the hold registry maintain their own reference count, tracking the number of copies of this resource that *this PD* holds. Entries of the hold registry will correspond to entries of the corresponding component or server's resource registry, as shown in the diagram below. The resource's component will track the *global* reference count.

```{image} ../figures/resource_registries.png
    :width: 700px
```

In this example, PD 2 has opened the same file to two different file descriptors. The file system client maintains a mapping from the file descriptors to the CSpace slot containing the file capability, and in this case, both file descriptors would map to the same CSpace slot. If PD 2 closes one of the file descriptors, it still needs to keep the file capability. However, when it closes both file descriptors, then the root task revokes the capability.

### Removing Resources
When a PD removes a resource (by closing a file descriptor, for instance), the reference count of the node in the hold registry is reduced. If the reference count of the hold node reaches zero, then hold node is deleted, and the root task revokes the resource capability from the PD. The PD will no longer be able to invoke it, and the slot that contained the capability will remain empty (see [revoked slots](target_limitations_revoke_slots) for more details).

For core resources, the root task decrements the reference count of the resource in the corresponding *component registry* whenever a hold node in a PD's *hold registry* is deleted. Deleting a hold node does not directly delete a resource, but if the reference count of the entry in the component registry entry reaches zero, then the resource will be deleted. 

For non-core resources, we expect resource servers to handle the deletion of their own resources. Resource servers should include "free" and/or "delete" functions in their APIs, and notify the root task of these operations:
- `resspc_client_delete_resource`: Delete a resource from a resource space and all PDs that hold it. For example, the file server would use this when a file is unlinked and deleted from the file system.
- `resspc_client_revoke_resource`: Remove a particular client PD's reference to a resource. This reduces the reference count of the corresponding hold node in the PD's hold registry. For example, the file server would use this when a PD closes a file.

```{attention}
The name of the function `resspc_client_revoke_resource` may be confusing and should be renamed to better reflect its meaning.
```


