# Using Webot

## Configuration

in `myconfig.py`, set :

```yaml
DONKEY_WEBOT = True
SIM_HOST = "<Webot IP address>"
```

## Implementation

Protocol is TCP + stupid message encapsulation
If connection breaks, part will try to reconnect after 3 secs
Part source code is `donkeycar/parts/webot.py`