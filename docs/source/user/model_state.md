# Model State

This section describes how to extract, view, and use the CellulOS system's model state.
See also the section on extracting a model state from Linux's `/proc` [below](target_proc_model_state).

## Setup
The scripts located at `/scripts/model_state/` will process the raw CSV, upload it to Neo4j, and calculate RSI / FR metrics.

(Assumes that `python 3.10` and `virtualenv` are already installed)

### Local environment
1. Create the virtualenv: `python -m venv venv`.
2. Activate the virtualenv: `source ./venv/bin/activate`.
3. Install requirements: `pip install -r requirements.txt`.
    - Or manually install packages: `pandas==2.2.2, neo4j==5.23.0, networkx==3.3`.

### Neo4j
1. Create a free account for [neo4j Aura](https://neo4j.com/cloud/platform/aura-graph-database/).
2. When your account is created, it should automatically create an instance. Download the connection details.
3. Fill out the `config.txt` in this directory from the connection details:
```
url = <paste NEO4J_URI>
user = <paste NEO4J_USERNAME>
pass = <paste NEO4J_PASSWORD>
```

## Extracting Model State
1. During a test, print the model state to console using the `pd_client_dump` API call.
    - When running the [system tests](target_system_tests), you can enable model state extraction with the `GPIExtractModel` [configuration option](target_configuration_options).
2. Once the test completes, copy the printed model state to a CSV file in the same directory as the scripts.
3. Ensure the CSV filename is prefixed with `raw_`.

## Processing Model State
Processing elevates the model state from implementation-level to model-level. For instance, in implementation one PD may switch between two address spaces, but in the model state this should appear as two separate PDs. The processing currently splits PDs with access to more than one ADS or CPU.
1. Run `python csv_processing.py`. This will process all files in the current directory of the form `raw_<name>.csv` to `<name>.csv`.

(target_visualize_model_state)=
## Visualizing Model State
1. Upload CSVs: Neo4j aura requires files to be hosted at a publicly-accessible url (GitHub, Google Drive, etc.)
    - If you upload to Google Drive: You will have to upload files to a folder with link-sharing enabled, or individually enable link-sharing on each CSV. Copy the link, then modify it to a direct-download link:
        1. The link should look like this: `https://drive.google.com/file/d/<file_id>/view?usp=drive_link`.
        2. Replace `file/d/` with `uc?id=`.
        3. Replace `/view?usp=drive_link` with `&export=download`.
    - Alternatively, in Google Sheets, clicking `File > Publish to the web`, and setting the link type to `CSV` will generate URL that Neo4j can access.
    - Note if using Google Drive: If you upload a file with the same name as a previous file and select 'Replace existing file', the download link should remain the same. Occasionally, if the file being replaced is several days old, the link will need to be updated.
2. Paste the public links as strings into the `public_urls` array in `import_csv.py`.
3. Import CSV to Neo4j: Run `python import_csv.py -i <idx>`, replacing `<idx>` with the index into the `public_urls` array of the CSV you want to import.
    - Adding the flag `-c` will cause different types of resources to be different types of nodes, so the graph is colour-coded and more readable. Currently, it is not possible to calculate the metrics on a graph uploaded with `-c`.
4. In Neo4j, open your instance, and enter queries in the Query panel to visualize the graph.

### Sample Queries
- Everything: Not recommended when the graph is large.
```
MATCH p=(()-[]-())
RETURN p
```
- Everything But: Show everything, excluding certain resource types and/or PDs.
```
// Specify resource types to exclude, and PD IDs to exclude
WITH  ["VMR", "BLOCK"] AS ignore_types, ["PD_0", "PD_1"] AS ignore_pds
MATCH p=((a)-[]-(b))
WHERE ((a:PD AND NOT a.ID IN ignore_pds) OR ((a:RESOURCE OR a:RESOURCE_SPACE) AND NOT a.DATA IN ignore_types)) 
  AND ((b:PD AND NOT b.ID IN ignore_pds) OR ((b:RESOURCE OR b:RESOURCE_SPACE) AND NOT b.DATA IN ignore_types))
RETURN p
```
- PDs only: Shows PD nodes and the relationships between them.
```
MATCH pdpaths=((:PD)-[]->(:PD))
RETURN pdpaths
```
- PDs and resource spaces: Shows PD nodes, resource space nodes, and the relationships between them.
```
// Get PD & Resource Space relations
MATCH pd_pd_paths=((:PD)-[]->(:PD))
RETURN pd_pd_paths AS paths
UNION DISTINCT
MATCH pd_rs_paths=((:PD)-[]->(:RESOURCE_SPACE))
RETURN pd_rs_paths AS paths
UNION DISTINCT
MATCH rs_rs_paths=((:RESOURCE_SPACE)-[]->(:RESOURCE_SPACE))
RETURN rs_rs_paths AS paths
```
- Files Overview: Shows PDs, resource spaces, files, and relations to files.
```
// Get PD & Resource Space relations
MATCH pd_pd_paths=((:PD)-[]->(:PD))
RETURN pd_pd_paths AS paths
UNION DISTINCT
MATCH pd_rs_paths=((:PD)-[]->(:RESOURCE_SPACE))
RETURN pd_rs_paths AS paths
UNION DISTINCT
MATCH rs_rs_paths=((:RESOURCE_SPACE)-[]->(:RESOURCE_SPACE))
RETURN rs_rs_paths AS paths
UNION DISTINCT

// Get 1 edge incoming to files
MATCH p1=(()-[]->(:RESOURCE {DATA: 'FILE'}))
RETURN p1 AS paths
UNION DISTINCT

// Get 2 edges outgoing from files
MATCH p2=((:RESOURCE {DATA: 'FILE'})-[*0..2]->())
RETURN p2 AS paths
UNION DISTINCT

// Get 1 edge incoming to nodes 1 edge outgoing from files
MATCH p3=((:RESOURCE {DATA: 'FILE'})-[*0..1]->()<-[]-())
RETURN p3 AS paths
```
- Visualize RSI: Shows resources of a particular type shared between two PDs, at any depth.
```
WITH "PD_3.0" as pd1, "PD_4.0" as pd2, "FILE" as type

// Find all accessible resources of the type
MATCH p1=((:PD {ID: pd1})-[:HOLD|MAP*1..4]->(r1:RESOURCE {DATA:type}))
WITH pd2, p1, r1, type
MATCH p2=((:PD {ID: pd2})-[:HOLD|MAP*1..4]->(r1))

RETURN p1, p2
```

## Calculating Metrics
1. Identify the IDs of the PDs you wish to compare.
2. Add an entry to the `configurations` array in `metrics.py`:
```
{'file': '<processed_csv_filename>.csv', 'pd1': '<first PD ID>', 'pd2': '<second PD ID>'}
```
3. Run `python metrics.py <idx>`, replacing `<idx>` with the index of the desired configuration in the `configurations` array.
    - The metrics script does connect to Neo4j, so it is essential that the corresponding file is also imported in your Neo4j instance.
4. The script will output the RSI and FR values for the chosen PDS, something like this:
```
Calculating metrics for 'kvstore_007.csv' (PD_6.0,PD_7.0)
RSI VMR: 0.0
RSI MO: 0.0
RSI VCPU: 0.0
RSI PCPU: 1.0
RSI FILE: 1.0
RSI BLOCK: 1.0
FR: 1
```

(target_proc_model_state)=
# Proc Model State

To demonstrate the extraction of model state from an entirely different system, we can build a model state from the contents of Linux's `/proc` virtual filesystem. We run some sample programs, and fetch the corresponding information from `/proc`. Currently, this extracts the following information:
- Virtual memory regions, their permissions, and their purpose (heap, stack, file, etc.).
- Physical memory regions and their mappings from virtual.
- Devices which the physical memory regions originate from.

## Setup
1. Create the virtualenv: `python -m venv venv`.
2. Activate the virtualenv: `source ./venv/bin/activate`.
3. Install requirements: `pip install -r requirements.txt`.
    - Or manually install packages: `pybind11`, `networkx`.
4. Build the `pfs` module: `pfs` is a c++ library, so we use a `pybind` wrapper to generate a Python module from it.
    - Enter the `pfs` directory: `cd pfs`.
    - Build: `cmake . & make`.
    - This should generate a python module: `/pfs/lib/pypfs.[...].so`.

## Run
1. In `proc_model.py`, choose the configuration of programs to run.
    - You can choose an existing configuration by setting `to_run = run_configs[<idx>]` with the index of the chosen configuration.
    - To add a new configuration and/or programs, ensure that the programs are built by the makefile, and add them to the `program_names` and `run_configs` variables.
2. Activate the virtualenv: `source ./venv/bin/activate`.
3. Run `sudo -E env PATH=./venv/bin python proc_model.py`.
4. The resulting model state is saved to the `proc_model.csv` file, which can be imported into neo4j for visualization following the steps [above](target_visualize_model_state).