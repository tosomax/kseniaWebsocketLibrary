import asyncio
import websockets
import time, json
from .crc import addCRC


#types of ksenia information required

read_types ='["OUTPUTS","BUS_HAS","SCENARIOS","POWER_LINES","PARTITIONS","ZONES"]'
realtime_types='["STATUS_OUTPUTS","STATUS_BUS_HA_SENSORS","STATUS_POWER_LINES","STATUS_PARTITIONS","STATUS_ZONES"]'


cmd_id = 1

#ws login call
async def ws_login(websocket, pin, _LOGGER):
    global cmd_id
    json_cmd = addCRC('{"SENDER":"Homeassistant", "RECEIVER":"", "CMD":"LOGIN", "ID": "1", "PAYLOAD_TYPE":"UNKNOWN", "PAYLOAD":{"PIN":"' + pin + '"}, "TIMESTAMP":"' + str(int(time.time())) + '", "CRC_16":"0x0000"}')
    
    try:
        await websocket.send(json_cmd)
        json_resp = await websocket.recv()
    except Exception as e:
        _LOGGER.error(f"Error during connection: {e}")
    response = json.loads(json_resp)
    login_id = -1
    if(response["PAYLOAD"]["RESULT"] == "OK"):
        login_id = int(response["PAYLOAD"]["ID_LOGIN"])
    return login_id


#realtime monitoring for component configuration
async def realtime(websocket,login_id,_LOGGER):
    _LOGGER.info("sending realtime first message")
    global cmd_id
    cmd_id += 1
    json_cmd = addCRC(
        '{"SENDER":"Homeassistant", "RECEIVER":"", "CMD":"REALTIME", "ID":"'
        + str(cmd_id)
        + '", "PAYLOAD_TYPE":"REGISTER", "PAYLOAD":{"ID_LOGIN":"'
        + str(login_id)
        + '","TYPES":'+str(realtime_types)+'},"TIMESTAMP":"'
        + str(int(time.time()))
        + '","CRC_16":"0x0000"}'
        )
    try:
        await websocket.send(json_cmd)
        _LOGGER.info("started realtime monitoring - returning intial data")
        json_resp_states = await websocket.recv()
        response_realtime = json.loads(json_resp_states)
    except Exception as e:
        _LOGGER.error(f"Realtime call failed: {e}")
        _LOGGER.error(response_realtime)
    return response_realtime

#data extraction for component configuration
async def readData(websocket,login_id,_LOGGER):
    _LOGGER.info("extracting data")
    global cmd_id
    cmd_id += 1
    json_cmd = addCRC(
            '{"SENDER":"Homeassistant","RECEIVER":"","CMD":"READ","ID":"'
            + str(cmd_id)
            + '","PAYLOAD_TYPE":"MULTI_TYPES","PAYLOAD":{"ID_LOGIN":"'
            + str(login_id)
            + '","ID_READ":"1","TYPES":'+str(read_types)+'},"TIMESTAMP":"'
            + str(int(time.time()))
            + '","CRC_16":"0x0000"}'
        )
    try:
        await websocket.send(json_cmd)
        json_resp_states = await websocket.recv()
        response_read = json.loads(json_resp_states)
    except Exception as e:
        _LOGGER.error(f"readData call failed: {e}")
        _LOGGER.error(response_read)
    return response_read["PAYLOAD"]
   


# this function receive a status (on/off) and send it to the relative output
async def setOutput(websocket, login_id, pin, output_id, status, logger):
    global cmd_id
    cmd_id = cmd_id + 1
    json_cmd = addCRC(
        '{"SENDER":"Homeassistant", "RECEIVER":"", "CMD":"CMD_USR", "ID": "'
        + str(cmd_id)
        + '", "PAYLOAD_TYPE":"CMD_SET_OUTPUT", "PAYLOAD":{"ID_LOGIN":"'
        + str(login_id)
        + '","PIN":"'
        + pin
        + '","OUTPUT":{"ID":"'
        + str(output_id)
        + '","STA":"'
        + status
        + '"}}, "TIMESTAMP":"'
        + str(int(time.time()))
        + '", "CRC_16":"0x0000"}'
    )
    cmd_ok = False
    try:
        await websocket.send(json_cmd)
        json_resp_states = await websocket.recv()
        response = json.loads(json_resp_states)
        logger.debug(f"WSCALL - response: {response}")
        if response["PAYLOAD"]["RESULT"] == "OK":
            cmd_ok = True
    except Exception as e:
        logger.error(f"WSCALL -  setOutput call failed: {e}")
        logger.error(response)

    return cmd_ok


#this function execute the relative scenario
async def exeScenario(websocket, login_id, pin, scenario_id, logger):
    logger.info("WSCALL - trying executing scenario")
    global cmd_id
    cmd_id = cmd_id + 1
    json_cmd = addCRC(
        '{"SENDER":"Homeassistant", "RECEIVER":"", "CMD":"CMD_USR", "ID": "'
        + str(cmd_id)
        + '", "PAYLOAD_TYPE":"CMD_EXE_SCENARIO", "PAYLOAD":{"ID_LOGIN":"'
        + str(login_id)
        + '","PIN":"'
        + pin
        + '","SCENARIO":{"ID":"'
        + str(scenario_id)
        + '"}}, "TIMESTAMP":"'
        + str(int(time.time()))
        + '", "CRC_16":"0x0000"}'
    )
    await websocket.send(json_cmd)
    json_resp = await websocket.recv()
    response = json.loads(json_resp)
    logger.info(f"WSCALL - executed scenario {response} ")
    cmd_ok = False
    if response["PAYLOAD"]["RESULT"] == "OK":
        cmd_ok = True
    return cmd_ok


