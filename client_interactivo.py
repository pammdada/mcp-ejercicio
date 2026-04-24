import asyncio
import json
import ollama
import sys
from mcp_clientee_ollama import MCPClient

async def main():
    # Parámetros para ejecutar el servidor
    server_command = "uv"
    server_args = ["run", "--with", "mcp", "mcp", "run", "server.py"]
    
    # Modelo a utilizar
    model = "llama3.2" 

    print("Conectando al servidor de la farmacia...")
    try:
        async with MCPClient(server_command, server_args) as client:
            tools = await client.get_ollama_tools()
            print("=========================================================")
            print(" ¡Bienvenido al Asistente de Farmacia (Vía MCP + Ollama)!")
            print("=========================================================")
            print("Herramientas cargadas:")
            for t in tools:
                print(f" - {t['function']['name']}: {t['function']['description']}")
            print("\nEscribe 'salir' para terminar el chat.\n")
            
            # Historial base del chat
            messages = [
                {"role": "system", "content": "Eres un asistente de farmacia. Usa herramientas para responder. NUNCA inventes o traduzcas nombres de funciones. Las funciones válidas son: list_products, get_stock, get_order."}
            ]
            
            while True:
                # 1. Obtener pregunta del usuario
                try:
                    user_input = input("\nUsuario: ")
                except (EOFError, KeyboardInterrupt):
                    break
                    
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("¡Hasta luego!")
                    break
                    
                if not user_input.strip():
                    continue

                messages.append({"role": "user", "content": user_input})
                
                # 2. Enviar a Ollama
                print("\nEscribiendo...")
                response = ollama.chat(model=model, messages=messages, tools=tools)
                message = response.get("message") if isinstance(response, dict) else response.message
                messages.append(message)
                
                # 3. Revisar tool_calls (formato oficial) o detección manual de JSON (fallback simple)
                tool_calls = message.get("tool_calls") if isinstance(message, dict) else getattr(message, "tool_calls", None)
                
                # Fallback simple: si el modelo respondió con un JSON en el texto en vez de usar tool_calls
                if not tool_calls and message.content.strip().startswith("{"):
                    try:
                        data = json.loads(message.content)
                        if "name" in data:
                            print("estoy usando un fallback")
                            # Convertimos el JSON manual al formato que espera el resto del script
                            tool_calls = [{"function": {"name": data["name"], "arguments": data.get("parameters", data.get("arguments", {}))}}]
                    except: pass

                if tool_calls:
                    for tool_call in tool_calls:
                        f = tool_call.get("function") if isinstance(tool_call, dict) else tool_call.function
                        t_name = f.get("name") if isinstance(f, dict) else f.name
                        # Mapeo simple por si el modelo traduce el nombre
                        if "lista" in t_name.lower(): t_name = "list_products"
                        t_args = f.get("arguments") if isinstance(f, dict) else f.arguments
                        
                        print(f" [Consultando sistema: {t_name}]")
                        try:
                            #el mcp envia la orden al server y espera la respuesta
                            result = await client.execute_tool(t_name, t_args)
                            #guardala respuesta en el historial con rol tool
                            messages.append({"role": "tool", "content": str(result), "name": t_name})
                        except Exception as e:
                            messages.append({"role": "tool", "content": f"Error: {e}", "name": t_name})
                    
                    # Respuesta final con datos
                    final_res = ollama.chat(model=model, messages=messages)
                    m = final_res.get("message") if isinstance(final_res, dict) else final_res.message
                    messages.append(m)
                    print(f"\nAsistente: {m.content if hasattr(m, 'content') else m.get('content', '')}")
                else:
                    print(f"\nAsistente: {message.content}")


    except Exception as e:
        print(f"\nOcurrió un error fatal: {e}")

if __name__ == "__main__":
    # Silenciar logs debug para no ensuciar el chat
    import logging
    logging.getLogger("mcp_clientee_ollama").setLevel(logging.WARNING)
    
    asyncio.run(main())
