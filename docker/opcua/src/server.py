# Copyright (C) 2021 scalers.ai

import asyncio
from asyncua import Server

async def start_opcua_server():
    """Start OPCUA server using the python package asyncua:
    https://github.com/FreeOpcUa/FreeOpcUa.github.io
    """
    url = "opc.tcp://0.0.0.0:4840"

    server = Server()
    await server.init()

    server.set_endpoint(url)
    server.set_server_name("Safety OPCUA Server")

    # register namespace
    name = "OPCUA_SIMULATION_SERVER"
    addspace = await server.register_namespace(name)

    node = await server.nodes.objects.add_object(addspace, 'Parameters')

    # add parameters to the namespaces
    safety_violation = await node.add_variable(addspace, "safety_violation", 0)
    safety_fps = await node.add_variable(addspace, "safety_fps", 0.0)

    defect_detection = await node.add_variable(addspace, "defect_detection", 1)
    defect_accuracy =  await node.add_variable(addspace, "defect_accuracy", 1.1)

    # set parameters to writable
    await safety_violation.set_writable()
    await safety_fps.set_writable()
    await defect_detection.set_writable()
    await defect_accuracy.set_writable()

    print("Server started at {}".format(url))
    async with server:
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    # start the opcua server
    asyncio.run(start_opcua_server())