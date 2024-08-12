(target_registry_library)=
# Registry Library

The resource registry utility is defined in `resource_registry.h`. A registry is a layer over a [UTHash](https://troydhanson.github.io/uthash/userguide.html) table for resource servers to track their resources. It includes some utility functions for adding / finding / removing entries from the registry, plus managing [reference counts](#reference-counts).

## Registry Entries
Resource servers should 'subclass' the generic resource registry entry type to create their own registry entry type.
A registry entry can be any structure, as long as it includes the `resource_registry_node_t` as the first parameter.
```c
typedef struct _my_resource_registry_node {
  resource_registry_node_t gen;
  // <... server-specific data here ...>
} my_resource_registry_node_t;
```

## Registry Keys
The registry key is a 64-bit value that uniquely identifies a resource within a registry. Usually, a registry is specific to a resource space, so a resource's object ID can be the same as its registry key.

Resource servers can insert resource registry entries with preset object IDs using `resource_registry_insert` (for example, we use the inode number as the file resource ID). 

Alternatively, you can use `resource_registry_insert_new_id` to insert a resource node and assign it the next available ID. There may be an upper limit on object IDs (see [badge scalability](target_limitations_badge_scalability)), so the `max_object_id` option (set in `resource_registry_initialize`) should be set to the maximum object ID. If nodes are deleted from the registry, their IDs will eventually be reassigned to a new node. If there are no IDs available, the operation will fail.

## Reference Counts
The `resource_registry_inc` and `resource_registry_dec` functions manage a registry entry's reference count. The count is initialized to 1 after a registry insert, and when it reaches zero, the registry entry is deleted (but entries can also be deleted forcefully with `resource_registry_delete`).

If the `on_delete` option is set in `resource_registry_initialize`, then the registry will call the `on_delete` function when an entry is about to be deleted from the registry. This way, a resource server can perform any necessary cleanup before the registry entry is freed.

## UTHash
Since the registry uses UTHash under the hood, we occasionally use the UTHash macros.

Deletion-safe iteration over all entries of a registry:
```c
resource_registry_t registry = <...>;

resource_registry_node_t *curr, *tmp;
HASH_ITER(hh, registry.head, curr, tmp)
{
    my_resource_registry_node_t *node = (my_resource_registry_node_t *)curr;
    // ...
}
```