import asyncio
import json
import ollama
from mcp_clientee_ollama import MCPClient

async def main():
    # Parámetros para ejecutar el servidor, basados en cliente.py
    server_command = "uv"
    server_args = ["run", "--with", "mcp", "mcp", "run", "server.py"]
    
    # Modelo a utilizar. Asegúrate de tener "llama3.2" u otro modelo compatible con tools localmente (e.g. qwen2.5)
    model = "llama3" 

    print("Iniciando MCP Client y conectando al servidor...")
    async with MCPClient(server_command, server_args) as client:
        # Obtener herramientas ya formateadas para Ollama
        tools = await client.get_ollama_tools()
        
        print("\n=== Herramientas del Servidor Cargadas ===")
        for t in tools:
            print(f"- {t['function']['name']}: {t['function']['description']}")
        print("==========================================\n")
        
        messages = [
            {"role": "user", "content": "Hola. ¿Puedes decirme el stock del Paracetamol y calcular el total si llevo 2? Solo usa las herramientas del servidor para obtener la información."}
        ]
        
        print(f"Enviando consulta a Ollama ({model})...")
        print(f"Usuario: {messages[0]['content']}\n")
        
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                tools=tools
            )
        except Exception as e:
            print(f"Error al conectar con Ollama: {e}\nAsegúrate de tener Ollama corriendo y el modelo '{model}' descargado.")
            return
            
        # Extraer el mensaje dependiendo de la versión de la librería (dict o pydantic)
        message = response.get("message") if isinstance(response, dict) else response.message
        
        # Guardar en el historial
        messages.append(message)
        
        # Verificar tool calls
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else getattr(message, "tool_calls", None)

        if tool_calls:
            print("Ollama ha decidido usar herramientas del servidor:")
            for tool_call in tool_calls:
                # Extraer info (manejar compatibilidad dict/objeto)
                func_dict = tool_call.get("function") if isinstance(tool_call, dict) else tool_call.function
                tool_name = func_dict.get("name") if isinstance(func_dict, dict) else func_dict.name
                tool_args = func_dict.get("arguments") if isinstance(func_dict, dict) else func_dict.arguments
                
                print(f" -> Ejecutando: {tool_name}({json.dumps(tool_args)})")
                
                # Ejecutar la tool a través de MCP
                try:
                    result = await client.execute_tool(tool_name, tool_args)
                    
                    # Convertir el resultado de MCP a un string (result.content es una lista de TextContent)
                    result_text = str(result)
                    if hasattr(result, "content") and isinstance(result.content, list):
                        parts = []
                        for c in result.content:
                            if hasattr(c, "text"):
                                parts.append(c.text)
                        if parts:
                            result_text = "\n".join(parts)
                            
                    print(f" <- Resultado: {result_text}")
                    
                    # Añadir el resultado a los mensajes para la respuesta final
                    messages.append({
                        "role": "tool",
                        "content": result_text,
                        "name": tool_name
                    })
                except Exception as e:
                    print(f" [!] Error al ejecutar herramienta: {e}")
                    messages.append({
                        "role": "tool",
                        "content": f"Error: {e}",
                        "name": tool_name
                    })
            
            # Segunda llamada a Ollama para respuesta final
            print("\nGenerando respuesta final de Ollama con los datos obtenidos...")
            final_response = ollama.chat(
                model=model,
                messages=messages
            )
            final_message = final_response.get("message") if isinstance(final_response, dict) else final_response.message
            content = final_message.get("content") if isinstance(final_message, dict) else final_message.content
            print("\nRespuesta Final de Ollama:")
            print(content)
            
        else:
            content = message.get("content") if isinstance(message, dict) else message.content
            print("\nRespuesta Directa de Ollama (No usó herramientas):")
            print(content)

if __name__ == "__main__":
    asyncio.run(main())
