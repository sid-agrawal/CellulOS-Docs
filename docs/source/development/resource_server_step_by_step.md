# Creating a Resource Server: Step by Step

## From Scratch
To quickly create a resource server from scratch, you can use the "sample resource server" as a starting point.

### Create the Server
1. Duplicate the folder `/projects/sel4-gpi/apps/sample-resource-server`.
2. Rename the files and variables to suit your resource server. Suppose your resource server will serve the resource type `X`:
    1. Rename the `sample_client` and `sample_server` files to `X_client` and `X_server`.
    2. Find-and-replace the word `sample` within the folder with `X`.
3. Add the server to the root task's CMake file (located at `/projects/sel4-gpi/apps/sel4test-driver/CMakeLists.txt`):
    1. Add the directory to be built: `add_subdirectory(../X-resource-server X-resource-server)`
    2. Add the executable to the CPIO archive: `list(APPEND cpio_files "$<TARGET_FILE:X_server>")`
4. Add the client library to a client's CMake file (for example, the test process, located at `/projects/sel4-gpi/apps/sel4test-tests/CMakeLists.txt`):
    1. Add `X_client` to the list in `target_link_libraries`.
5. Start the resource server:
    1. Copy the `GPIPD003` test, which starts the sample resource server.
    2. Import the client api: `#include <X_client.h>`.
    3. Replace references to `sample_server` in the test with `X_server`.
    4. Run your test - it should start your server and allocate one resource.

### Fill in the Blanks
These steps can be completed in any order.

1. Decide on the client API for interacting with your resource server, and define the API in the `X_rpc.proto` file.
    1. To add a new type of request, add a new message structure, and add it to the request message:
    ```c
    message XFooMessage {
        uint64 arg1 = 1;
        uint64 arg2 = 2;
        <...>
    };

    message SampleMessage {
        uint64 magic = 100;
        oneof msg {
            XAllocMessage alloc = 1;
            XFreeMessage free = 2;
            XFooMessage foo = 3;
        };
    };
    ```
    2. If the request does not require any information in the reply message, then you can use the basic return message, and there is no need to add a new reply message type. If the reply does carry information, then add a new reply message structure, and add it to the reply message:
    ```
    message XFooReturnMessage {
        uint64 arg1 = 1;
        <...>
    };

    message XReturnMessage {
        XError errorCode = 1; 
        oneof msg {
            XBasicReturnMessage basic = 2;
            XAllocReturnMessage alloc = 3;
            XFooReturnMessage foo = 4;
        };
    };
    ```
    3. You may also want to add new error types to the `XError` enum, which will be returned in the `errorCode` field of the `XReturnMessage`.
    4. Build the project to generate the message structures from the `.proto` file.
    - For more details on message syntax, see the [Protocol Buffers Documentation](https://protobuf.dev/programming-guides/proto3/). 
    - NanoPB provides some additional generator options (repeated field length, string length, etc.), see the [NanoPB API Reference](https://jpa.kapsi.fi/nanopb/docs/reference.html#generator-options). 
2. Add the client API functions to the `X_client.h` and `X_client.c` files:
    - The client API function should fill out the appropriate RPC request structure, and extract the results from the reply structure.
    ```c
    int X_client_foo(sample_client_context_t *conn, uint64_t arg1, uint64_t arg2, uint64_t *response)
    {
        int error;

        XMessage request = {
            .magic = SAMPLE_RPC_MAGIC,
            .which_msg = XMessage_foo_tag,
            .msg.foo = {
                .arg1 = arg1,
                .arg2 = arg2,
            }};

        XReturnMessage reply = {0};

        error = sel4gpi_rpc_call(&rpc_client, conn->ep, &request, 0, NULL, &reply);
        error |= reply.errorCode;

        if (error == 0) {
            // Extract the response if the call was successful
            *response = reply.msg.foo.arg1;
        }

        return error;
    }
    ```
3. Give the server the resources it needs:
    - The default `start_X_server_proc` function starts the server with the minimum required RDEs (`MO`, `EP`, `RESSPC`, and `VMR` for its own address space).
    - Using `start_resource_server_pd_args`, you can add up to 1 additional RDE, and an arbitrary number of command-line arguments. 
    - Sending additional RDEs or resources will require extension to the `start_resource_server_pd_args` function, see [flexible PD configuration](target_flexible_pd) for more details.
4. Fill in the `X_init` function in the server to perform any startup work for the server.
5. Fill in the `X_request_handler` function to handle the messages you defined in the client API.
    - If the message is sent via an RDE (the general endpoint, not a particular resource), then add a case to the `if (obj_id == BADGE_OBJ_ID_NULL)` path.
    - If the message is sent via a particular resource, then add a case to the `else` path for requests with an object ID.
6. Fill in the `X_work_handler` function to handle work messages from the root task.
7. Test the resource server:
    - Test the client API functions that you defined.
    - Test the server's response to root task work. Try extracting the model state, crashing a PD while it holds resources from your resource server, and triggering your resource server's space to be deleted by a cleanup policy.

## From an Existing App

```{attention}
To be filled out.
```