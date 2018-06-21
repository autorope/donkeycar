# Stores

Stores are parts that record and replay vehicle data produced by other parts.

## Tub
This is the standard donkey data store and it is modeled after the ROSBAG.

> TODO: The structure of the Tub part is not ideal and should be changed.

> * types should not need to be specified and could be inspected and saved
on the first loop.


Example creation

```python
import donkey as dk

T = dk.parts.Tub(path, inputs, types)

```






### Accepted Types
* `float` - saved as record
* `int` - saved as record

