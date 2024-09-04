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

## GPIADS00X - Address Space Management
### Coverage Level
Low

### Tested System Components
- MO allocation and ADS Attach (ADS001)
- VMR Removal/Unmap (ADS002)
- ADS Creation and Destruction (ADS003) 

### Actions
These are very basic ADS management tests to ensure core VMR allocation and removal functionalities aren't broken.

## GPIBM00X - Benchmarking 
### Coverage Level
High

### Tested System Components
Although most benchmarks are quite basic, they run the most important functionalities for the system to operate properly, and so they do end up covering a large portion of the system.

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
These tests demonstrate the system's ability to run a Key-Value store built on top of SQLite. 

(target_test_kv001)=
#### GPIKV001 (Same Process)
- Spawns a KVstore client process with a KVstore server in the same ADS, as a static library. 
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

(target_test_kv002)=
#### GPIKV002 (Separate Processes)
- Spawns a KVstore client process, and a KVstore server in another process. 
- An FS and a Ramdisk resource server are spawned
- The KVStore client and server processes share the same FS namespace

(target_test_kv003)=
#### GPIKV003 (Separate FS Namespace)
Same setup as GPIKV002, except KVStore client and server use different FS namespaces

(target_test_kv004)=
#### GPIKV004 (Separate FS)
- Spawns a KVstore client process, and a KVstore server in another process. 
- Two FSess and one Ramdisk resource server are spawned - the FSes share the same Ramdisk
- The KVStore client and server processes use different FSes

(target_test_kv005)=
#### GPIKV005 (HighJMP)
- Spawns a KVstore client process with the KVStore server as a static library
- KVStore client creates a new ADS for executing KVStore server code, and swaps ADSes every time the KVStore server library is invoked
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

(target_test_kv006)=
#### GPIKV006 (Separate threads)
- Spawns a KVstore client process with the KVStore server as a static library
- KVStore client main thread creates a separate thread to act as the KVStore server
- An FS and a Ramdisk resource server are spawned for the KVStore library to operate.

```{attention}
There is a terrible hack employed for using the file system client across thread-PDs. As described in [](target_known_limits_thread_cspace), accesses to CSlots in threads need to be done with care, as CSpaces are not synchronized between threads within the same process. The FS client is global for an entire process, and stores a MO as a shared message
buffer for RPCs. Due to lack of time, this has not been refactored to allow for storing the CSlots of the MO for all threads that may be accessing the FS client. To allow GPIKV006 to run, the FS client is simple cleared and re-initialized when switching between different threads, to ensure the shared message MO slot is still valid.
```

#### GPIKV007 (Two Sets)
The same setup as GPIKV002, however with two sets of KVStore client and server processes, all using the same FS.

#### GPIKV008 (Crash Test)
The same setup as GPIKV003, however the Ramdisk crashes.

## GPICL00X - System Cleanup
### Coverage Level
Medium

### Tested System Components
- Configurable Resource Cleanup Policies
- Resource Server and Client Communication
- Resource Server Resource Management 

### Actions
1. Creates a toy resource server, which interacts with a `hello` client PD
2. Manually cause a crash by terminating the toy server
3. Extract model state after the crash
4. Clean up all resources depending on the configured [Resource Space Cleanup Policy Depth](target_configuration_cleanup_policy).

## GPIVM00X - Virtual Machines
### Coverage Level
Medium

### Tested System Components
- Flexible PD Creation based on Configuration
- PD Fault and interrupt handling
- Cap slot synchronization between multiple thread-PDs
- Running a guest OS as a PD

### Actions
1. Initializes the test PD as a VMM
2. Creates a thread to handle guest-PD faults
3. Starts a new guest from a specified kernel image

#### GPIVM001
Starts a baby-VM using the **sel4test** VMM implementation

#### GPIVM002
Starts a Linux VM using the **sel4test** VMM implementation

#### GPIVM003
Starts a baby-VM using the **OSmosis** VMM implementation

#### GPIVM004
Starts a Linux VM using the **OSmosis** VMM implementation

## GPIMS00X - Model State Extraction
### Coverage Level
Very Low

### Tested System Components
- Graph-based model extraction functionalities

### Actions
Attempts to add nodes and edges to a model state structure that is eventually converted into CSV strings

```{attention}
The GPIFS00X, GPIRD00X, GPISQ00X tests are essentially elements of the GPIKV00X tests, broken into smaller, specific tests.
```

## GPIFS00X - File System
### Coverage Level
Medium

### Tested System Components
- File System Client and Server
- File System Namespaces
- Ramdisk Functionality
- Resource Server and Client Communication

### Actions
1. Starts up Ramdisk and File System servers as PDs  
2. Initializes the test PD as a file system client
3. Performs various FS related syscalls (`open`, `write`, `close`, etc.)

## GPIRD00X - Ram Disk
### Coverage Level
Medium

### Tested System Components 
- Ramdisk Functionality
- Resource Server and Client Communication

### Actions
1. Starts up a Ramdisk resource server PD
2. Test PD allocates blocks and attempts to write and read them

## GPISQ00X - SQLite
### Coverage Level
Medium

### Tested System Components 
- Ramdisk Functionality (indirectly)
- File System Client and Server (indirectly)

### Actions
1. Starts up Ramdisk and File System servers as PDs  
2. Creates SQLite DBs
3. Creates tables in DBs
4. Insert, update, and delete table rows
5. Shut down SQLite, the FS and Ramdisk servers, and clean up all test resources
