# Preventing Deadlocks in CellulOS

PDs frequently make requests to the root task via `seL4_Call`. The root task also needs to send occasional messages to PDs in the following scenarios:
- Request a subgraph of the model state from a resource manager
- Inform a resource manager PD that some instance of one of its resources is freed
    - eg. if a PD crashed while holding a file resource, we let the file server know
- Inform a resource manager PD that one of its resource spaces is destroyed
    - This can happen due to a cleanup policy

With a single-threaded root task, we could easily reach a deadlock if we do not design carefully. For example, consider the following scenario:

```{image} figures/model_extraction_deadlock.png
  :width: 700px
```

1. A client requests something from a resource server
2. Another client requests a model extraction, and in the process of extracting the model state, the root task makes a blocking call to request a subgraph from the resource server
3. In order to finish its current operation, the resource server needs to request something from the root task
4. Deadlock

## Investigation

### Potential Solutions
We considered the following potential solutions:
1. **Multi-threading**: The root task is multi threaded, so it can have some number of blocked threads waiting on other PDs to reply, while maintaining an active thread to serve requests.
    - Advantage: Requires little change in the way that the root task communicates with other PDs.
    - Disadvantage: Has the potential to introduce many concurrency issues, and we would prefer to avoid it as much as possible.
2. **Async**: All requests that the root task makes to other PDs are asynchronous, so the root task does not wait for a reply. Since it will not block, it will be available to serve requests from PDs.
    - Advantage: Still allows the root task to communicate with other PDs, while avoiding the dangers of multithreading.
    - Disadvantage: Requires handling asynchronous logic and replies.
3. **Avoidance**: Prevent the root task from ever making requests to other PDs. Thus it will be able to serve requests from PDs.
    - Advantage: Completely eliminates this potential cause of deadlock.
    - Disadvantage: Does not seem feasible, as we believe we need some information flow from the root task to resource manager PDs.

### Existing Systems
We investigated similar systems for design inspiration, as we expect this deadlock scenario to be common in microkernels.

#### FUSE (File System in Userspace)
FUSE is a kernel module and userspace library that facilitate running a file system in userspace on top of a Linux kernel. Applications can request regular file system operations on the mounted FUSE file system. These requests first go to the kernel, then the kernel forwards the requests to the userspace filesystem. This was of interest since, like our setup, it involves a privileged PD making requests of a less-privileged PD.

```{image} images/fuse_diagram.png
  :width: 600
```
- Image from [Vangoor et al.][2]

**Kernel -> FS communication**
The kernel sends requests to the FUSE filesystem through message queues. The kernel module and FUSE fs maintain the queues by reading/writing the '/dev/fuse' file. There are several queues with different priorities, and the filesystem handles them accordingly. When requests are complete, the filesystem writes replies to another queue. The kernel module will read the replies and unblock any waiting application. The format of the requests is pretty straightforward: all requests have a header structure including an opcode, followed by an opcode-specific data struct. For more details, see the [FUSE manpage][3].

This design aligns with Option 2, as the message queues are an async communication method.

#### QNX
QNX has similar IPC primitives to seL4, and the [QNX Manual][1] recommends arranging entities in a tree, where blocking IPC only flows in one direction.
> The Send/Receive/Reply IPC primitives allow the construction of deadlock-free systems with the observation of only a couple simple rules:
> 1. Never have two threads send to each other.
> 2. Always arrange your threads in a hierarchy, with sends going up the tree.
> ```{image} images/qnx_ipc_tree.png
> :width: 250
> ```

This is a simple and effective way to avoid deadlocks, but what if we need to send messages down the tree? The manual suggests two solutions. The first is non-blocking event messages:
> But how does a higher-level thread notify a lower-level thread that it has the results of a previously requested operation? (Assume the lower-level thread didn't want to wait for the replied results when it last sent.)
>
> QNX/Neutrino provides a very flexible architecture with the MsgDeliverEvent() kernel call to deliver non-blocking events.

The second solution is that a lower-level thread initiates a send to a higher-level thread, and the higher-level thread can reply at its own convenience.
> The lower-level thread would send in order to ``report for work,'' but the higher-level thread wouldn't reply then. It would defer the reply until the higher-level thread had work to be done, and it would reply (which is a non-blocking operation) with the data describing the work. In effect, the reply is being used to initiate work, not the send, which neatly side-steps rule #1.

The initial recommendation for deadlock-free systems sounds like Option 3, but the manual acknowledges that higher-priority threads may need to send information to lower-priority threads. It suggests a couple of ways to do so asynchronously, aligning with Option 2.

#### Hubris
Similarly to QNX's thread-hierarchy rule, Hubris has the "uphill send rule":
> When designing a collection of servers in an application, remember that it’s only safe to send messages to higher priority servers (called the "uphill send rule"). Sending messages to lower priority servers can cause starvation and deadlock.

## CellulOS Async Message Design

Both the existing work, and the advantages/disadvantes we considered for Cellulos, pointed towards Option 2 being the best approach. Next, we considered how to implement async messages. All designs would need a way for the root task to send information to PDs without blocking itself. If the root task needs some information in response, then this has to be sent in a separate `seL4_Call` initiated by the PD. 

### Async Design Options

#### Async Message Queue
- The root task will have a shared frame with each resource server. The frame will contain a send and receive queue for messages.
- The resource servers can send requests to the root task as usual. The root task will never send blocking requests, and will only queue requests to servers via the async message queue.
- The root task and resource servers will check for messages in the message queue before calling Recv on their own endpoint.
  - This makes the queue higher priority than client requests.
- When a message is sent, the root task will also need to notify the receiver with NBSend (non-blocking send) in case it is blocked on its IPC endpoint.
  - **Deadlock is still possible**:
    1. The receiver checks the queue and finds it empty.
    2. The root task writes a message, and does an NBSend.
    3. The receiver does a Recv, since it already checked the queue, and gets stuck.
  - This could be fixed with a shared mutex for the queues. It is simple to implement a shared mutex using an `seL4_Notification`.

Message-queue library:
   - We could use [libringbuffer][5] for a send/receive queue in a shared frame, and use NanoPB to define the message structure.
   - We would need to implement the message-queue API. It will consist of some initialization functions (one for the root task, which does the shared frame setup, and one for the servers, which just connect to it), and simple send/recv functions.
   - We also need to make the sender/receiver check for messages at the correct times, and ensure that a send will unblock a receiver waiting on its endpoint.

#### Uphill-only
- The root task never sends a message to a resource server PD, not even async.
- Resource server PDs have to "report for work" (as mentioned in the QNX manual) by sending a message to the root task, and the root task may reply with some "work".
- The root task internally queues the requests it needs to make to resource server PDs, and sends them when the server reports for work.
- The resource servers will have to report for work before waiting on their own endpoint.   
    - Similar to option 1, deadlock is possible here. 
    - We can fix it using the seL4 [bound notification][6] mechanism. Notifications act somewhat like semaphores, so the root task can signal the notification without blocking itself. Binding the notification to the resource server's TCB allows us to wake up a resource server waiting on its endpoint without sending an IPC message.

Maintaining State:
- For this solution, the root task needs to maintain some state for each PD's pending work, so that it can return some work when the PD reports for work.

### Chosen Design

We chose the "Uphill-only" option, since it offers several advantages:
- No need to implement / debug a message queue.
- The root task can implement any policy to decide which task to send first when a PD reports for work, eg. it may send higher-priority tasks first.
- No need to worry about queue length limits.
- Simpler to program and to reason about (arguably).

The main disadvantage of this method is it will be slower than the shared-message-queue approach, since it requires more IPC. The PD must block on a message sent to the root task to get work, as opposed to just reading from a queue in memory.

#### Implementation
- The root task will add "work" to an internal queue for each resource server PD.
- The root task signals a notification bound to the corresponding resource server PD, so the resource server will know that it has work to fetch. Using the seL4 bound notification mechanic, also causes it to unblock if it was waiting on its regular endpoint.
- Resource servers must call a "get work" RPC when they have work and they are available, then the root task will send it the next piece of work from the queue.
- As an optimization, the root task may send several pieces of work (of the same type) in the same message.
- If the work requires sending some response to the root task (like in the case of model extraction), then the resource server sends the response as a separate RPC.
- If the root task needs responses from the work, then it needs to maintain some state so that it can handle the response asynchronously.

#### Example 1
Some app requests a model state extraction while the FS is busy. The root task queues some extraction task, and notifies the FS' bound notification that there is work for it to do. Once the FS finishes the client request, it sees that it has work to do, and it calls the root task to get the work. It sends the extracted subgraph to the root task, and assuming this was the only piece of the model state that the root task was missing, now it replies to the app.

```{image} figures/deadlock_avoidance_1.png
  :width: 800
```

#### Example 2
This also works if the FS was not busy when the root task has work for it. In that case, the FS is woken when the root task signals the work notification, and then the FS may complete the work in the same way.

```{image} figures/deadlock_avoidance_2.png
  :width: 800
```

[1]: https://swd.de/Support/Documents/Manuals/Neutrino-Microkernel-System-Architecture/Chapter-2-The-QNX-Neutrino-Microkernel-Part-2/
[2]: https://www.fsl.cs.stonybrook.edu/docs/fuse/fuse-tos19-a15-vangoor.pdf
[3]: https://man7.org/linux/man-pages/man4/fuse.4.html
[4]: https://hubris.oxide.computer/reference/#uphill-send
[5]: https://github.com/seL4/projects_libs/tree/master/libringbuffer
[6]: https://docs.sel4.systems/projects/sel4/api-doc.html#bind-notification