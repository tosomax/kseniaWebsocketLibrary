import asyncio
import websockets
import time, json
from .crc import addCRC


#types of ksenia information required

read_types ='["OUTPUTS","BUS_HAS","SCENARIOS","POWER_LINES","PARTITIONS","ZONES","STATUS_SYSTEM"]'
realtime_types='["STATUS_OUTPUTS","STATUS_BUS_HA_SENSORS","STATUS_POWER_LINES","STATUS_PARTITIONS","STATUS_ZONES","STATUS_SYSTEM"]'


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
async def setOutput(websocket, login_id, pin, command_data, queue, logger):
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
        + str(command_data["output_id"])
        + '","STA":"'
        + str(command_data["command"])
        + '"}}, "TIMESTAMP":"'
        + str(int(time.time()))
        + '", "CRC_16":"0x0000"}'
    )
    try:
        command_data["command_id"]=cmd_id
        queue[str(cmd_id)]= command_data
        await websocket.send(json_cmd)

        #delete item if future not satisfied
        asyncio.create_task(wait_for_future(command_data["future"], cmd_id, queue, logger))

    except Exception as e:
        logger.error(f"WSCALL -  setOutput call failed: {e}")
        queue.pop(str(cmd_id), None)



#this function execute the relative scenario
async def exeScenario(websocket, login_id, pin, command_data, queue, logger):
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
        + str(command_data["output_id"])
        + '"}}, "TIMESTAMP":"'
        + str(int(time.time()))
        + '", "CRC_16":"0x0000"}'
    )
    try:
        command_data["command_id"]=cmd_id
        queue[str(cmd_id)]= command_data
        await websocket.send(json_cmd)

        #delete item if future not satisfied
        asyncio.create_task(wait_for_future(command_data["future"], cmd_id, queue, logger))

    except Exception as e:
        logger.error(f"WSCALL -  executeScenario call failed: {e}")
        queue.pop(str(cmd_id), None)



async def wait_for_future(future, cmd_id, queue, logger):
    try:
        logger.debug(f"timeout task created")
        await asyncio.wait_for(future, 60) 
    except asyncio.TimeoutError:
        logger.error(f"Command {cmd_id} timed out - deleting from pending queue")
        queue.pop(str(cmd_id), None)
    except Exception as e:
        logger.error(f"Error in wait_for_future for command {cmd_id}: {e}")