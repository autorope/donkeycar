# Tests

There is a limited test suite to ensure that the your changes to the code
don't break something unintended.

## Run all the tests

Look into the `.travis.yml` for a more detailed commands used for tests:

* `install` section is used to install required packages and setting up environment.
* `script` section is actually used to run test suite
* `jobs` section may contain another tasks related to other  things like tests
 or deployments.

Notice: in `.travis.yml` env var named `TRAVIS_PYTHON_VERSION` is populated from `python` section, such as `TRAVIS_PYTHON_VERSION=3.6`.

Please refer to the [travis documentation](https://docs.travis-ci.com/) for more details.

## Code Organization

The test code is in `tests` foders in the same folder as the code. This is to
help keep the test code linked to the code its self. If you change the code,
change the tests. :)

> TODO: Skip tests that require specific hardware.
