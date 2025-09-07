## Avala Documentation

Avala uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) for documentation.

### Running the docs locally

1. Install dependencies:
   ```console
   $ pip install mkdocs-material
    ````

2. Start the local dev server:

   ```console
   $ mkdocs serve
   ```

3. Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000) to view the docs.
   Changes will auto-reload on save.

### Building the docs

To build a static site (output in the `site/` directory):

```console
$ mkdocs build
```

### Deploying

To deploy docs to GitHub Pages:

```console
$ mkdocs gh-deploy
```
