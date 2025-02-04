import asyncio
from typing import OrderedDict
import websockets
import json, time
import ssl
from kseniaWebsocketLibrary.wscall import ws_login,realtime, readData, exeScenario, setOutput

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2) 
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.options |= 0x4



class WebSocketManager:
    def __init__(self,ip,pin,logger):
        self._ip = ip
        self._pin = pin
        self._ws = None
        self.listeners = {"lights": [], "domus": [], "switches" :[], "powerlines": [], "partitions": [],"zones":[]}
        self._logger = logger
        self._running = False       #this flag is used to keep process alives
        self._loginId = None
        self._realtimeInitialData = None  #realtime data 
        self._readData = None     #read data 

        self._ws_lock = asyncio.Lock() #take care of sync between ws calls



        self._command_queue = asyncio.Queue()  # this one queue all the commands that will be sent to lares

        self._pending_commands = {}

        #connection retry parameters
        self._max_retries = 5  
        self._retry_delay = 1 


    #Connect to ws with unsecure connection!!!!!
    async def connect(self):
        retries = 0
        while retries < self._max_retries:
            try:
                uri=f"ws://{self._ip}/KseniaWsock"         #using unsecure connection!!!!!!
                self._logger.info("Connecting to WebSocket...")
                self._ws = await websockets.connect(uri, subprotocols=['KS_WSOCK'])      
                self._loginId = await ws_login(self._ws, self._pin, self._logger)
                if self._loginId < 0:
                    self._logger.error("WebSocket login error")
                    raise Exception("Login failed")
                self._logger.info(f"Connected to websocket - ID {self._loginId}")
                async with self._ws_lock:
                    self._logger.info("extracting inital data")
                    self._readData = await readData(self._ws,self._loginId,self._logger)
                    #self._logger.debug(self._readData)
                async with self._ws_lock:
                    self._logger.info("realtime connection started")
                    self._realtimeInitialData = await realtime(self._ws,self._loginId,self._logger)
                    #self._logger.debug(self._realtimeInitialData)
                self._logger.debug("initial data acquired")
                self._loginId


                #starting listener and queue process
                self._running = True  
                asyncio.create_task(self.listener())
                asyncio.create_task(self.process_command_queue())

                return  

            except (websockets.exceptions.WebSocketException, OSError) as e:
                self._logger.error(f"WebSocket connection failed: {e}. Retrying in {self._retry_delay} seconds...")
                await asyncio.sleep(self._retry_delay)
                retries += 1
                self._retry_delay *= 2 

        self._logger.critical("Maximum retries reached. WebSocket connection failed.")

    #Connect to ws with secureConnection  -> ksenia has selfsigned certificates and old ssl version, it may not work
    async def connectSecure(self):
        retries = 0
        while retries < self._max_retries:
            try:
                uri=f"wss://{self._ip}/KseniaWsock" 
                self._logger.info(f"Connecting to WebSocket...{uri}")
                self._ws = await websockets.connect(uri,ssl=ssl_context, subprotocols=['KS_WSOCK'])       #secure connection
                self._loginId = await ws_login(self._ws, self._pin, self._logger)
                if self._loginId < 0:
                    self._logger.error("WebSocket login error")
                    raise Exception("Login failed")
                self._logger.info(f"Connected to websocket - ID {self._loginId}")
                async with self._ws_lock:
                    self._logger.info("extracting inital data")
                    self._readData = await readData(self._ws,self._loginId,self._logger)
                    #self._logger.debug(self._readData)
                async with self._ws_lock:
                    self._logger.info("realtime connection started")
                    self._realtimeInitialData = await realtime(self._ws,self._loginId,self._logger)
                    #self._logger.debug(self._realtimeInitialData)
                self._logger.info("initial data acquired")


                #starting listener and queue process
                self._running = True  
                asyncio.create_task(self.listener())
                asyncio.create_task(self.process_command_queue())

                return

            except (websockets.exceptions.WebSocketException, OSError) as e:
                self._logger.error(f"WebSocket connection failed: {e}. Retrying in {self._retry_delay} seconds...")
                await asyncio.sleep(self._retry_delay)
                retries += 1
                self._retry_delay *= 2 

        self._logger.critical("Maximum retries reached. WebSocket connection failed.")

        

    async def listener(self):
        self._logger.info("starting listener")


        while self._running:
            try:
                message = None
                async with self._ws_lock:
                    try:
                        message = await asyncio.wait_for(self._ws.recv(), timeout=3) #fix timeout if needed
                    except asyncio.TimeoutError:
                        continue  # keep the listening going 

                if message:         #if a message is received, handle it
                    message = json.loads(message)
                    await self.handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                self._logger.error("WebSocket close. trying reconnection")
                self.running = False
                #await self.connect()


    async def handle_message(self, message):

        #extract the message
        payload = message.get("PAYLOAD", {})
        data = payload.get('Homeassistant', {})

        self._logger.debug(f"message: {message}")
        self._logger.debug(f"commands: {self._pending_commands}")

        # sort received message for the right callback
        if message["CMD"] == "CMD_USR_RES":
            if self._pending_commands:
                command_data = self._pending_commands[int(message["ID"])]
                self._logger.debug(f"Received result for command {command_data['command']} (Output ID: {command_data['output_id']})")
                command_data["future"].set_result(True)  # Segna il comando come eseguito con successo
                self._logger.debug(f"commands: {command_data}, future: {command_data['future'].done()}")
                self._pending_commands.pop({message["ID"]})
                self._logger.debug(f"commands: {self._pending_commands}")
            else:
                self._logger.warning("Received CMD_USR_RES but no commands were pending")

        elif message["CMD"] == "REALTIME":
            if "STATUS_OUTPUTS" in data:
                for callback in self.listeners["lights"]:
                    await callback(data["STATUS_OUTPUTS"])
                for callback in self.listeners["switches"]:
                    await callback(data["STATUS_OUTPUTS"])
            if "STATUS_BUS_HA_SENSORS" in data:
                #self._logger.debug(f"Updating state for domus {data['STATUS_BUS_HA_SENSORS']}")
                for callback in self.listeners["domus"]:
                    await callback(data["STATUS_BUS_HA_SENSORS"])
            if "STATUS_POWER_LINES" in data:
                #BUG in Ksenia ws. Powerline updated every x seconds even if value does not change.
                #self._logger.debug(f"Updating state for power lines {data["STATUS_POWER_LINES"]}")
                for callback in self.listeners["powerlines"]:
                    await callback(data["STATUS_POWER_LINES"])
            if "STATUS_PARTITIONS" in data:
                self._logger.debug(f"Updating state for partitions {data['STATUS_PARTITIONS']}")
                for callback in self.listeners["partitions"]:
                    await callback(data["STATUS_PARTITIONS"])
            if "STATUS_ZONES" in data:
                self._logger.debug(f"Updating state for zones {data['STATUS_ZONES']}")
                for callback in self.listeners["zones"]:
                    await callback(data["STATUS_ZONES"])
        else:
            self._logger.warning("the if do not work")


    #this function is used to register a new entity to the listener
    def register_listener(self, entity_type,callback):
        #self._logger.info(f"new listener registered: {entity_type}")
        if entity_type in self.listeners:
            self.listeners[entity_type].append(callback)



    #this function process the command queue
    async def process_command_queue(self):
        self._logger.debug(f"command queue started")
        while self._running:
            
            command_data = await self._command_queue.get()

            output_id, command = command_data["output_id"], command_data["command"]

            try:
                async with self._ws_lock:
                    #3 types of command -> turing on/off output, dimmer or executing scenarios
                    if command == "SCENARIO":
                        self._logger.debug(f"COMMAND QUEUE - executing scenario n {output_id}")
                        await exeScenario(
                            self._ws,
                            self._loginId,
                            self._pin,
                            output_id,
                            self._logger
                        )
                    elif command in ("ON", "OFF"):
                        self._logger.debug(f"COMMAND QUEUE - Sending command {command} to {output_id}")
                        await setOutput(
                            self._ws,
                            self._loginId,
                            self._pin,
                            command_data,
                            self._pending_commands,
                            self._logger
                        )
                        
                    elif isinstance(command, int):      #dimmer
                        self._logger.debug(f"COMMAND QUEUE - Sending command for dimmer {str(command)} to {output_id}")
                        await setOutput(
                            self._ws,
                            self._loginId,
                            self._pin,
                            command_data,
                            self._pending_commands,
                            self._logger
                        )

                    # retry could be implemented
            except Exception as e:
                self._logger.error(f"COMMAND QUEUE -  Error during command elaboration: {str(command)} for {output_id}: {e}")


    #this function send the command to the queue
    async def send_command(self, output_id, command):

        future = asyncio.Future()

        command_data = {
            "output_id": output_id,
            "command": command.upper() if isinstance(command, str) else command,  #uppercase for ksenia websocket message
            "future": future,
            "command_id": 0  # Aggiunge l'ID univoco
        }

        await self._command_queue.put(command_data)

        self._logger.debug(f"send_command -  command add to queue  {str(command)} for {output_id}")

        try:
            # Aspetta la conferma dal WebSocket
            success = await asyncio.wait_for(future, timeout=10)

            if not success:
                self._logger.warning(f"Command {command} for {output_id} timed out")
                return False
        except asyncio.TimeoutError:
            self._logger.warning(f"send_command - Timeout waiting for confirmation of command {command} for {output_id}")
            return False
        
        return True


    #this function close the websocket connection
    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
                
   
   #Turn on output
    async def turnOnOutput(self, output_id, brightness=None):
        try:
            
            if(brightness):
                success = await self.send_command(output_id, brightness) #send command to turn "ON" an output with brightness
            else:
                success = await self.send_command(output_id, "ON")  #send command to turn "ON" an output
            if not success:
                self._logger.warning(f"Failed to turn off output {output_id}.")
                return False
            return True
        except Exception as e:
            self._logger.error(f"turnOnOutput - Error while sending command to queue with id {output_id}: {e}")
            return False

    #Turn off output
    async def turnOffOutput(self, output_id):
        try:
            success = await self.send_command(output_id, "OFF")
            if not success:
                self._logger.warning(f"Failed to turn off output {output_id}.")
                return False
            return True
        except Exception as e:
            self._logger.error(f"turnOffOutput - Error while sending command to queue {output_id}: {e}")
            return False
    


    async def executeScenario(self, scenario_id):
        try:
            future = asyncio.Future()
            await self.send_command(scenario_id, "SCENARIO") #send command execute "SCENARIO"
            return await future
        except Exception as e:
            self._logger.error(f"Error while sending scenario to queue  {scenario_id}: {e}")
            return False
        
    


    #this function get the list of lights output from the data acquired from ws
    async def getLights(self):
        lares_realtime = self._realtimeInitialData["PAYLOAD"]["STATUS_OUTPUTS"]
        lights = [output for output in self._readData["OUTPUTS"] if output["CAT"] == "LIGHT"]
        # combine static information with current status
        lights_with_states = []
        for light in lights:
            light_id = light["ID"]
            state_data = next(
                (state for state in lares_realtime if state["ID"] == light_id), None
            )
            
            if state_data:
                state_data["STA"]=state_data["STA"].lower()
                state_data["POS"] = int(state_data.get("POS", 255))
                lights_with_states.append({**light, **state_data})

        #self._logger.info("LIGHTS - Combined lights with states: %s", lights_with_states)
        return lights_with_states

    #this function get the list of switch output from the data acquired from ws
    async def getSwitches(self):
        lares_realtime = self._realtimeInitialData["PAYLOAD"]["STATUS_OUTPUTS"]
        switches = [output for output in self._readData["OUTPUTS"] if output["CAT"] != "LIGHT"]
        # combine static information with current status
        switches_with_states = []
        for switch in switches:
            switch_id = switch["ID"]
            state_data = next(
                (state for state in lares_realtime if state["ID"] == switch_id), None
            )
            if state_data:
                switches_with_states.append({**switch, **state_data})

        #self._logger.info("SWITCHES - Combined switches with states: %s", switches_with_states)
        return switches_with_states
        
    #this function get the list of domus from the data acquired from ws
    async def getDom(self):
        domus = [output for output in self._readData["BUS_HAS"] if output["TYP"] == "DOMUS"]
        lares_realtime = self._realtimeInitialData["PAYLOAD"]["STATUS_BUS_HA_SENSORS"]
        
        # combine static information with current status
        domus_with_states = []
        for sensor in domus:
            sensor_id = sensor["ID"]
            state_data = next(
                (state for state in lares_realtime if state["ID"] == sensor_id), None
            )
            if state_data:
                domus_with_states.append({**sensor, **state_data})

        #self._logger.info("DOMUS - Combined domus with states: %s", domus_with_states)
        return domus_with_states
     
    #get list of scenarios from ws
    async def getScenarios(self):
        scenarios = self._readData["SCENARIOS"]
        return scenarios 

    #this function get the list of a generic sensor from the data acquired from ws
    async def getSensor(self,sName):
        sensorList = self._readData[sName]
        lares_realtime = self._realtimeInitialData["PAYLOAD"]["STATUS_"+sName]

        # combine static information with current status
        sensor_with_states = []
        for sensor in sensorList:
            sensor_id = sensor["ID"]
            state_data = next(
                (state for state in lares_realtime if state["ID"] == sensor_id), None
            )
            if state_data:
                sensor_with_states.append({**sensor, **state_data})

        #self._logger.info(f"{sName} - Combined  with states: %s", sensor_with_states)
        return sensor_with_states


    #TEST CONNECTION
    async def testConnect(self):
        try:
            self._logger.info("TEST - trying WebSocket connection")
            self._ws = await websockets.connect(self._uri, subprotocols=['KS_WSOCK'])
            self._loginId = await ws_login(self._ws, self._pin, self._logger)
            if self._loginId < 0:
                self._logger.error("TEST - login error for WebSocket")
                raise Exception("Login failed")
            self._logger.info("TEST - success")
        except Exception as e:
            self._logger.error(f"Error with WebSocket connection: {e}")

    async def testSecureConnect(self):
        try:
            self._logger.info("TEST - trying WebSocket secure connection")
            uri=f"wss://{self._ip}/KseniaWsock"
            self._ws = await websockets.connect(uri,ssl=ssl_context, subprotocols=['KS_WSOCK'])       #secure connection
            self._loginId = await ws_login(self._ws, self._pin, self._logger)
            if self._loginId < 0:
                self._logger.error("TEST - login error for WebSocket")
                raise Exception("Login failed")
            self._logger.info("TEST - success")
        except Exception as e:
            self._logger.error(f"Error with WebSocket connection: {e}")

