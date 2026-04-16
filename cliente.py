from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


#Crear parametros

server_params = StdioServerParameters(
    command="uv",
    args=["run", "--with", "mcp", "mcp", "run", "server.py"],
    env=None,
)

async def run ():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            #lsitar tools
            tools = await session.list_tools()
            print(tools)

            
            tool_result = await session.call_tool(
                tools.tools[1].name,
                arguments={
                    "nombre": "Paracetamol",
                    "cantidad": 2
                }
            )

            print("Tool result:")
            print(tool_result)

            
if __name__ == "__main__":
    import asyncio
    asyncio.run(run())