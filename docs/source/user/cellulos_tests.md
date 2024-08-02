(target_system_tests)=
# System Tests

```{attention}
WIP, to be added:
- description of tests which demonstrate a certain functionality of the system
```

(target_system_test_types)=
## Test Types

The project supports running tests in two ways:
1. The plain sel4test environment with no CellulOS functionality, and the test process is a regular sel4utils process.
2. The OSmosis environment, where the test process is created as a CellulOS PD, and the root task runs the GPI Server.

Plain sel4tests are defined using the `DEFINE_TEST` macro, and CellulOS tests are defined using the `DEFINE_TEST_OSM` macro. When run, the corresponding type of test process will be created. If you are running any CellulOS tests, then the [GPI Server](target_glossary_gpi_server) must be enabled through the `GPIServerEnabled` [ccmake option](target_configuration_options). If you are only running sel4test-style tests, then you can disable the GPI Server.