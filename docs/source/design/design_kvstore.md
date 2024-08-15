# The KVStore Server
The KVStore server uses [SQLite](https://www.sqlite.org/) to create a database of key-value stores, where each store is a table of 64-bit keys and values.

## Behaviour
**Set**: Adds a row to the corresponding kvstore table containing the specified key and value. The simple kvstore keeps only one value per key, and setting the same key twice will overwrite the previous value.

**Get**: Returns the value corresponding to the given key. If the key does not exist in the table, the kvstore returns an error.

## Interaction with File Server
The KVStore server interacts with the file system indirectly through SQLite, which makes libc calls, which are then [routed to the file server](target_file_system_libc). The kvstore server creates one SQLite database, which in turn creates one file. SQLite also creates a journal file at the beginning of each transaction, and then deletes it once the transaction is completes.

## KVStore Server Modes
The KVStore server can run in one of several modes.
- IPC modes: The KVStore server runs as a usual resource server. It listens on an endpoint for RPC requests. Clients can allocate a new kvstore, which creates a new table in the SQLite database and a new kvstore resource. Clients can use a kvstore resource to set/get values in the kvstore.
    - Process: The KVStore can run in IPC mode as a process by loading the `kvstore_server` executable.
    - Thread: The KVStore can run in IPC mode as a thread started by another executable that includes the `kvstore_server_lib` library, using the `kvstore_server_main_thread` function as the thread entry point.
    - In both cases, the KVStore server takes a temporary parent endpoint as an argument, like a usual resource server. Once it has finished initializing, it will notify the parent, and the parent can find the kvstore server endpoint through its kvstore RDE.
- Local modes: The KVStore server is called directly through function calls. Clients can allocate a new kvstore, which returns a kvstore ID. Clients can refer to a kvstore by ID to get/set values.
    - Same PD: The `kvstore_client` functions call the server functions directly, without a context switch.
    - Separate ADS: The `kvstore_client` functions switch to a different, server address space before calling the server functions. Then they switch back to the app address space before returning. Note that this operation is not secure - the app could choose to switch to the server address space at other times if it chose to.

| IPC / Local | Mode | System Tests |
|---|---|---|
|Local|Same PD|[GPIKV001](target_test_kv001)|
|Local|Separate ADS|[GPIKV005](target_test_kv005)|
|IPC|Process|[GPIKV002](target_test_kv002), [GPIKV003](target_test_kv003), [GPIKV004](target_test_kv004)|
|IPC|Thread|[GPIKV006](target_test_kv006)|