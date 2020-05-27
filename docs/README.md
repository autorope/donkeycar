
<!-- markdownlint-disable MD026 -->
# Donkey Docs&reg;
<!-- markdownlint-restore -->

The source of the documentation gets built in the folder `../site` and is
published to [official site](http://docs.donkeycar.com/).
Our docs use extended markdown as implemented by MkDocs.

## Building the documentation

* install MkDocs `pip install mkdocs`
* `mkdocs serve` starts a local webserver at localhost:8000
* `mkdocs build` Builds a static site in `../site` directory
* config docs with (../mkdocs.yml)

## Linting

Please use markdownlint for checking document formatting.
[markdownlint offical repo](https://github.com/DavidAnson/markdownlint)

You can execute it locally via docker:

```bash
docker run -v $PWD:/markdown:ro 06kellyjac/markdownlint-cli .
```

For linting rules see `.markdownlint`, for now this is very relaxed set.
