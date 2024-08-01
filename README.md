# CellulOS Documentation

View the docs here: https://cellulosdocs.readthedocs.io/en/latest/

## Building Locally

### Ubuntu
1. Setup venv:
```bash
cd docs
python3 -m venv .
source ./bin/activate
python3 -m pip install -r requirements.txt
````
2. Build the html files: `make html`
3. Launch `./build/html/index.html` to view the site locally
    - To easily launch from command line, you can add the following to `.bashrc`:
    ```bash
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

## Using Sphinx

We are using [MyST](https://myst-parser.readthedocs.io/en/latest/index.html) to parse markdown instead of reStructuredText, so the directives are slightly different from regular [Sphinx](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html). 

Often, if there is a restructured text directive that look like this:

    .. directive_name:: arg0 arg1
        :option_name: option_value

Then we can use the same directive in markdown like this:

    ```{directive_name} arg0 arg1
        :option_name: option_value
    ```

## Troubleshooting

### Missing pages in sidebar
Have you recently added a new page, and it appears in the sidebar on the homepage, but mysteriously disappears from the sidebar when you navigate to some other pages?
Try a `make clean` and then `make html` again, and the issue should disappear.