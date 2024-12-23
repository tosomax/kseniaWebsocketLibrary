from kseniaWebsocketLibrary.websocketmanager import WebSocketManager
import tests.kwsConf as kwsConf
import logging, pytest

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
ws = WebSocketManager(kwsConf.lares_ip, kwsConf.pin,logger)

@pytest.mark.asyncio
async def test_connection():

    if kwsConf.ssl:
        await ws.connectSecure()
    else:
        await ws.connect()
    await ws.stop()
    assert ws._loginId>0

@pytest.mark.asyncio
async def test_realtime():
    if kwsConf.ssl:
        await ws.connectSecure()
    else:
        await ws.connect()
    await ws.stop()
    assert ws._realtimeInitialData is not None
    
@pytest.mark.asyncio
async def test_read():
    if kwsConf.ssl:
        await ws.connectSecure()
    else:
        await ws.connect()
    await ws.stop()
    assert ws._readData is not None

@pytest.mark.asyncio
async def test_getFunctions():
    if kwsConf.ssl:
        await ws.connectSecure()
    else:
        await ws.connect()
        
    lights = await ws.getLights()
    scenarios = await ws.getScenarios()
    domus = await ws.getDom()
    switch = await ws.getSwitches()
    zones = await ws.getSensor("ZONES")
    partitions = await ws.getSensor("PARTITIONS")

    assert isinstance(lights, list), "Expected lights to be a list"
    assert isinstance(scenarios, list), "Expected scenarios to be a list"
    assert isinstance(domus, list), "Expected domus to be a list"
    assert isinstance(switch, list), "Expected switch to be a list"
    assert isinstance(zones, list), "Expected zones to be a list"
    assert isinstance(partitions, list), "Expected partitions to be a list"
    
    await ws.stop()