(target_system_tests)=
# System Tests

```{attention}
WIP
```

There are various tests which can be run to both demonstrate a certain functionality of the system and to ensure that core functionalities have not been broken by an update. Each test listed here is described by three dimensions:
1. Coverage level [low, med, high]: how much of the system the test invokes. If a non-trivial update has been implemented, and the tests run without issue:
    - low = the most common system features still function as expected, but it is likely that bugs exist in more complex code paths
    - med = A few of the uncommon code paths within major system components are triggered, but not enough to provide confidence that the non-trivial update hasn't broken other major components
    - high = there is more confidence that the non-trivial code update is robust, as this test uses a large set of the system's features. Remaining bugs are likely subtle and obscure 
2. Tested system components: the specific components which the test uses
3. Actions: description of what the test does

(target_system_test_types)=
## Test Types

The project supports running tests in two ways:
1. The plain sel4test environment with no CellulOS functionality, and the test process is a regular sel4utils process.
2. The OSmosis environment, where the test process is created as a CellulOS PD, and the root task runs the GPI Server.

Plain sel4tests are defined using the `DEFINE_TEST` macro, and CellulOS tests are defined using the `DEFINE_TEST_OSM` macro. When run, the corresponding type of test process will be created. If you are running any CellulOS tests, then the [GPI Server](target_glossary_gpi_server) must be enabled through the `GPIServerEnabled` [ccmake option](target_configuration_options). If you are only running sel4test-style tests, then you can disable the GPI Server.

## GPIPD00X - Simple process-PDs
### Coverage Level
Low

### Tested System Components
- PD configuration: process spawning
- Tracked Endpoints
- Sending resources between PDs
- Simple PD cleanup

### Actions
Spawns a very simple `hello` process-PD with a communication channel to the test PD. `hello` starts up, waits to be given an MO from the test PD, and then attaches it to a VMR.

## GPITH00X - Thread-PDs
### Coverage Level
Medium

### Tested System Components
- PD configuration: process spawning, thread creation with local stacks, thread creation with isolated stacks
- Cleanup of [linked PDs](target_pd_config_linked_pds)
- PD exit from non-main threads
- synchronization (not mutual exclusion) between different processes and threads within the same process

### Actions
#### GPITH001
Creates a no-op `sel4utils` thread from the test-PD

#### GPITH002
Creates a no-op CellulOS thread-PD from the test-PD

#### GPITH003
Spawns a `hello` process-PD that creates a secondary thread with an isolated stack, tests whether the isolated stack can write to the main-thread's stack, and synchronizes with the test PD for exiting and cleanup

## GPIKV00X - KVStore Server and Client
### Coverage Level
High

### Tested System Components
- PD configuration: process spawning, thread creation, HighJMP creation
- Tracked Endpoints
- Resource Server Spawning and Operation: File system, Ramdisk
- Cleanup of resource server PDs, resource spaces, client PDs
- KVStore Server in a separate thread, separate ADS within same PD, separate process
- FS namespaces
- Multiple File Systems
- PD Cleanup policy following a crash

### Actions
#### GPIKV001 (Same Process)
- Spawns a KVstore client process with a KVstore server in the same ADS, as a static library. 
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

#### GPIKV002 (Separate Processes)
- Spawns a KVstore client process, and a KVstore server in another process. 
- An FS and a Ramdisk resource server are spawned
- The KVStore client and server processes share the same FS namespace

#### GPIKV003 (Separate FS Namespace)
Same setup as GPIKV002, except KVStore client and server use different FS namespaces

#### GPIKV004 (Separate FS)
- Spawns a KVstore client process, and a KVstore server in another process. 
- Two FSess and one Ramdisk resource server are spawned - the FSes share the same Ramdisk
- The KVStore client and server processes use different FSes

#### GPIKV005 (HighJMP)
- Spawns a KVstore client process with the KVStore server as a static library
- KVStore client creates a new ADS for executing KVStore server code, and swaps ADSes every time the KVStore server library is invoked
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

#### GPIKV006 (Separate threads)
- Spawns a KVstore client process with the KVStore server as a static library
- KVStore client main thread creates a separate thread to act as the KVStore server
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

```{attention}
TODO Linh: explain the terrible thread hack used
```

#### GPIKV007 (Two Sets)
The same setup as GPIKV002, however with two sets of KVStore client and server processes, all using the same FS.

#### GPIKV008 (Crash Test)
The same setup as GPIKV003, however the Ramdisk crashes.
