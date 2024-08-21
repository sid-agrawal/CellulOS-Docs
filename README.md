# CellulOS Documentation

View the docs here: https://cellulosdocs.readthedocs.io/en/cellulos/

## Building Locally

### Ubuntu
1. Install sphinx: `pip install sphinx`
2. Navigate to `./docs` and install requirements: `pip install -r requirements.txt`
3. Build the html files: `make html`
4. Launch `./build/html/index.html` to view the site locally
    - To easily launch from command line, you can add the following to `/bashrc`:
    ```
    export BROWSER="explorer.exe"
    alias start="explorer.exe"
    ```
    - Navigate to `./build/html/` and run `start index.html`

### MacOS
1. Setup venv:
```bash
cd docs
python3 -m venv .
source ./bin/activate
python3 -m pip install -r requirements.txt
````

2. Build the html files: `make html`
3. Launch: `open ./build/html/index.html`
