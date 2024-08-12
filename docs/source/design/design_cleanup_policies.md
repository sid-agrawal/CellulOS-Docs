# Cleanup Policy Design

The cleanup policy refers to the steps taken to restore the system after a PD crashes or is terminated, and the implemented options are detailed [here](target_configuration_cleanup_policy). The options in CellulOS went through a few iterations, which will be documented here. 

## Metric-Based Cleanup
In writing, we initially discussed a cleanup policy where we iterate through all active PDs and compare each one with the crashed PD via the RSI / FR metrics. If the values are above some threshold, we would also clean up the active PD. CellulOS [does not currently calculate the metrics at runtime](target_limitations_runtime_metrics), so we have not explored this route in implementation, but we were able to explore some depth-based cleanup policies as an initial step.

## Resource Deletion Policy
Initially, we approached this issue from the perspective of resource deletion. When a PD crashes, we must be able to handle its held resources and any resource spaces it manages, so that the model state remains legal (no orphaned resources, etc.). We defined the following requirements:
- A resource server must hold every resource in the resource spaces it manages. As a result, if another PD crashes while holding a resource from the space, the resource will not be orphaned.
- The root task needs to notify resource servers when this occurs, so they may decide to delete the resource if no other PD was holding it.

For a crashed PD that was managing a resource space containing a set of resources **R**, we considered two cleanup options:
- Revoke: we revoke the resources in **R** from all other PDs that hold them. Additionally, revoke any resources that have map edges to the resources in **R**, recursively.
- Kill: we destroy any PDs that depend on resources in **R** (again through hold or map edges).

These options were further refined to 4 policies, where each corresponds to cleaning up a resource space RS containing a set of resources **R**:
- Policy 1a (direct resource deletion): Removes any hold edges to resources in **R**, remove any request edges for RS. Delete RS and **R**.
- Policy 1b (recursive resource deletion): Similar to 1a, but also recursively delete any resources that map to resources in **R**.
- Policy 2a (direct PD deletion): Destroys any PDs that have a hold edge to a resource in **R** or a request edge for RS.
- Policy 2b (recursive PD deletion): Similar to 2a, but also recursively deletes any PDs that depend on any additional resource spaces managed by other deleted PDs.

As a further adjustment, we decided to replace *resource* deletion with *resource space* deletion. A resource space could map to more than one resource space, so in theory, a space could have some resources deleted as part of a resource deletion policy, and continue to function. However, we decided that if some resources in a space should be deleted, then all should be deleted, since it is impossible to predict the impact on the resource space. Then we update policy 1a/1b:
- Policy 1a (direct resource space deletion): Removes any hold edges to resources in **R**, remove any request edges for RS. Delete RS and **R**.
- Policy 1b (recursive resource space deletion): Similar to 1a, but also recursively delete any resource *spaces* that map to RS.

## Depth-based Resource Space Cleanup Policy
While implementing the 4 policies described above, it became natural to extend the policies to arbitrary depths. Rather than a binary option of either depth 1 or depth infinity, we can support variable and independent resource space deletion depth and PD deletion depth. Their effects are described in [configuration options](target_configuration_cleanup_policy).

The depths are more general than the concrete policies, as the policies can be described in terms of depths:
| Policy | PD Deletion Depth | Resource Space Deletion Depth |
|---|---|---|
| 1a (direct resource space deletion) | 0 | 0 |
| 1b (recursive resource space deletion) | 0 | inf |
| 2a (direct PD deletion) | 1 | 0 |
| 2b (recursive PD deletion) | inf | 0 |