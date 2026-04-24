import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional, Dict, Any, Tuple, Union

# Configurar logging
logger = logging.getLogger(__name__)

class MCPClient:
    
    def __init__(self, command: str, args: list[str], env: Optional[Dict[str, str]] = None):
        """
        Inicializa un cliente MCP.
        
        Args:
            command (str): El comando para ejecutar el servidor MCP (e.j. "node", "python")
            args (list[str]): Los argumentos para el comando (e.j. ["path/to/server.js"])
            env (Optional[Dict[str, str]]): Variables de entorno para el servidor
        """
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        self.session = None
        self.read = None
        self.write = None
        self._client_ctx = None
        self._session_ctx = None

    async def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # gestor de contexto para la comunicacion por stdio, en server_parms esta la  configuracion
            self._client_ctx = stdio_client(self.server_params)
            #inicializar el recurso
            client = await self._client_ctx.__aenter__()
            #permiten enviar y recibir bytes
            self.read, self.write = client

            #
            self._session_ctx = ClientSession(self.read, self.write)
            self.session = await self._session_ctx.__aenter__()
            await self.session.initialize()
            logger.info("Conexión exitosa con servidor MCP")
            return True
        except ConnectionError as e:
            logger.error(f"Error de conexión con servidor MCP: {e}")
            await self.disconnect()
            return False
        except Exception as e:
            logger.error(f"Error desconocido al conectar con servidor MCP: {e}")
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Cierra la conexión con el servidor MCP"""
        try:
            #verifica si hay una sesion activa
            if self._session_ctx:
                #"NONE le dice que fue una salida normal y no un error"
                await self._session_ctx.__aexit__(None, None, None)
                self._session_ctx = None
                self.session = None
            
            if self._client_ctx:
                await self._client_ctx.__aexit__(None, None, None)
                self._client_ctx = None
                self.read = None
                self.write = None
            
            logger.info("Desconexión exitosa del servidor MCP")
        except Exception as e:
            logger.error(f"Error durante la desconexión: {e}")

    async def list_tools(self) -> Any:
        """
        Lista todas las herramientas disponibles en el servidor
        
        Returns:
            Any: Objeto con información sobre las herramientas disponibles
            
        Raises:
            RuntimeError: Si el cliente no está conectado
            Exception: Si ocurre un error al listar las herramientas
        """
        if not self.session:
            raise RuntimeError("Cliente no conectado. Llama a connect() primero")
        try:
            tools = await self.session.list_tools()
            logger.debug(f"Herramientas disponibles: {tools}")
            return tools
        except Exception as e:
            logger.error(f"Error al listar herramientas: {e}")
            raise

    async def get_ollama_tools(self) -> list:
        """
        Obtiene las herramientas del servidor y las formatea para ser usadas con Ollama.
        """
        mcp_tools = await self.list_tools()
        ollama_tools = []
        for tool in mcp_tools.tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema
                }
            })
        return ollama_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Ejecuta una herramienta específica con los argumentos proporcionados
        
        Args:
            tool_name (str): Nombre de la herramienta a ejecutar
            arguments (Dict[str, Any]): Argumentos para la herramienta
            
        Returns:
            Any: Resultado de la ejecución de la herramienta
            
        Raises:
            RuntimeError: Si el cliente no está conectado
            Exception: Si ocurre un error al ejecutar la herramienta
        """
        if not self.session:
            raise RuntimeError("Cliente no conectado. Llama a connect() primero")
        try:
            logger.debug(f"Ejecutando herramienta {tool_name} con argumentos: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            logger.debug(f"Resultado de la herramienta {tool_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error al ejecutar herramienta {tool_name}: {e}")
            raise
#inicia la conexion
    async def __aenter__(self) -> 'MCPClient':
        """Soporte para context manager asíncrono (async with)"""
        success = await self.connect()
        if not success:
            raise RuntimeError("Error al conectar con el servidor MCP")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Soporte para context manager asíncrono (async with)"""
        await self.disconnect()