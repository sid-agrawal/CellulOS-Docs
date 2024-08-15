# Configuration Options

This section describes the CellulOS configuration options that can be specified using `ccmake .`.

(target_configuration_options)=
## Option Overview
- `GPIPDDeletionDepth`: The PD deletion depth for resource space cleanup, see [Resource Space Cleanup Policy Depth](target_configuration_cleanup_policy).
- `GPIRSDeletionDepth`: The RS deletion depth for resource space cleanup, see [Resource Space Cleanup Policy Depth](target_configuration_cleanup_policy).
- `GPIServerEnabled`: A boolean option controlling whether or not to run the [GPI server](target_glossary_gpi_server), see also [test types](target_system_test_types).
- `GPIBenchmarkIterBits`: An option controlling how many times to rerun the same benchmark test in a single boot. The number of iterations will be `2^GPIBenchmarkIterBits`. This option will be handled by the [benchmarking script](target_benchmarking).
- `GPINanobenchEnabled`: An boolean option to enable or disable nanobenchmark outputs in the GPI server. See [benchmarking](target_benchmarking) for more details.
- `GPIExtractModel`: A boolean option controlling whether or not to extract the model state during tests. To use this option, tests should call `extract_model` from `test_shared.h`. All [system tests](target_system_tests), except for the benchmarks, will print a model state if this is enabled.
- `GPIVmmImplementation`: String defining which VMM implementation to compile, only one of `sel4test-vmm` and `osm-vmm` may be compiled at a time.

(target_configuration_cleanup_policy)=
## Resource Space Cleanup Policy Depth

When a resource server crashes or is terminated, the resource space cleanup policy begins for the resource space(s) that the resource server managed. In all cases, the resource space(s) will be deleted, and its constituent resources will be removed from any PDs that hold them. The CMake options `GPIPDDeletionDepth` and `GPIRSDeletionDepth` specify how far to follow dependency relations for cleaning up PDs and resource spaces, respectively.

**PD Deletion Depth**: Given some crashed PD_0, the PD deletion depth would determine the maximum depth of dependent PDs from PD_0 to delete. Dependent PDs are those that have a request edge for a resource space that PD_0 manages, or hold any resources that subset a resource space that PD_0 manages. If a PD deleted during the cleanup policy is also a resource server, then recursively we delete other dependent PDs, up to the PD Deletion Depth.

**Resource Space Deletion Depth**: We recursively traverse reverse-map edges from PD_0's resource space(s) up to a given depth, and delete any resource spaces encountered along the way.

For example, consider the following PD setup: 

```{image} ../figures/resource_cleanup_model_state.png
  :width: 800
```

If Block Server 1 crashes, these are the effects of the potential cleanup policies:
| PD Deletion Depth | Resource Space Deletion Depth | Effect |
|---|---|---|
| 0 | 0 | Disk 1 and Block 1 are deleted. An error may occur in the FS while using File 1, and it cannot request blocks from Disk 1 anymore. |
| 0 | 1 | In addition to the effects of the previous row, File Space and File 1 are deleted. An error may occur in the DB while using Table 1, and it cannot request files from the FS anymore. |
| 0 | 2 | In addition to the effects of the previous row, Database and Table 1 are deleted. An error will occur in the App if it tries to use Table 1, and it cannot request new Tables from the DB server. |
| 1 | 0/1 | FS PD is destroyed, and as a necessary effect, Files 1/2 are deleted. An error may occur in the DB while using Table 1, and it cannot request new files from the FS. |
| 1 | 2 | The FS PD is destroyed. Additionally, we traverse resource spaces two hops (block 1 <- file 1 <- table 1) and delete Database and Table 1. An error will occur in the APP if it tries to use Table 1, and it cannot request new Tables from the DB server. |
| 2 | (any) | The FS and DB PDs are destroyed. An error will occur in the APP if it tries to use Table 1, and it cannot request new Tables from the DB server. |
| 3 | (any) | The FS, DB, and APP PDs are destroyed. |
