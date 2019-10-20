# Tests

There is a limited test suite to ensure that the your changes to the code
don't break something unintended.

## Run all the tests

Look into the `.travis.yml` for a more detailed commands used for tests.

```bash
python -m unittest
```

## Code Organization

The test code is in `tests` foders in the same folder as the code. This is to
help keep the test code linked to the code its self. If you change the code,
change the tests. :)

> TODO: Skip tests that require specific hardware.
