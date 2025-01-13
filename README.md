# kseniaWebsocketLibrary

Library for connecting to Ksenia webserver .

- Supported components: outputs, zones, partitions, scenarios, powerlines. For other components, open  a new issue
- This library may lower the security of your alarm system. Please be aware of it!
- To establish communication it's necessary to provide an access PIN, DO NOT USE THE ADMINISTRATOR PIN, create an ad hoc user + dedicated pin.
- The unit allows two modes of communication to the webserver: unencrypted transmission and via SSL. Depending on the version of the unit, SSL communication may not work due to outdated protocols on the unit, which python websocket library can no longer communicate with. Adjust the conf.py as needed.
- The Lares SSL certificate is self signed. For this reason, SSL Certificate authentication is disabled, this is vulnerable to man in the middle attacks (The same is true when accessing your Lares Ksenia 4.0 central from your PC/Browser!).

  
[![PyPI](https://img.shields.io/pypi/v/kseniaWebsocketUtil.svg)](https://pypi.org/project/kseniaWebsocketLibrary/)
## Requirements

- Python 3.6+
- `websockets` library
- `asyncio` library

## Installation

To install the required libraries, run:

```sh
pip install websockets asyncio
```

## Configuration

Create a `kwsConf.py` file in your project directory with the following content:

```python
lares_ip = "xxx.xxx.xxx.xxx"        #ip of the lares unit
pin = "xxxxxx"                      #pin to access the unit. DO NOT USE THE ADMIN PIN
ssl = True                          #true or false, based on the net settings of the unit. It allows SSL communication
```
## Usage

### WebSocketManager

The `WebSocketManager` class is used to manage the WebSocket connection to the Ksenia system.
It provides the following methods:

- `connect()`: Establishes a connection to the websocket.
- `connectSecure()`: Establishes a secure SSL connection to the websocket.
- `stop()`: Closes the websocket connection.
- `getLights()`: Retrieves the list of lights from the system.
- `getDom()`: Retrieves the list of domus components from the system.
- `getSwitches()`: Retrieves the list of switches from the system.
- `getSensor(sensor_name)`: Retrieves the list of sensors based on the provided sensor name.
- `getScenarios()`: Retrieves the list of scenarios from the system.
- `turnOnOutput(output_id)`: Turns on the output with the specified ID.
- `turnOffOutput(output_id)`: Turns off the output with the specified ID.
- `executeScenario(scenario_id)`: Executes the scenario with the specified ID.

### Example

```python
import asyncio
import logging
from kseniaWebsocketUtil.websocketmanager import WebSocketManager
import kseniaWebsocketUtil.conf as conf

# Configure logging
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create WebSocketManager instance
ws = WebSocketManager(conf.lares_ip, conf.pin, logger)

async def main():
    if conf.ssl:
        await ws.connectSecure()
    else:
        await ws.connect()
    
    # Example functions
    lights = await ws.getLights()
    print(lights)
    
    await ws.stop()

# Run the example
asyncio.run(main())
```

## Testing

 
In order to test the library, you will need a test module and a plugin for async calls as **pytest** and **pytest-asyncio** 

To run the tests, use the following command:

```sh
pytest tests/test_websocketmanager.py
```

## License

This project is licensed under the MIT license. See the LICENSE file for details.

## Support



If you find this project useful, consider making a donation to support its development:

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?hosted_button_id=XXMMY7ZYEHWW4)

thx to https://github.com/gvisconti1983/lares-hass for helpful insights

