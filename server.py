
from mcp.server.fastmcp import FastMCP
from data import MEDS, SUPPLIES

#iniciar el server
mcp = FastMCP("Farmacia")

@mcp.tool()
def list_products(type: str = "todos"):
    """Lista de productos disponibles. 'type' puede ser: medicamentos, insumos o todos"""
    if type == "medicamentos":
        return MEDS
    elif type == "insumos":
        return SUPPLIES
    else:
        return MEDS + SUPPLIES

@mcp.tool()
def get_stock(nombre: str ):
    """Busca el stock y precio de un producto por su nombre"""
    products = MEDS+SUPPLIES
    for p in products:
        if nombre.lower() in p["nombre"].lower():
            return {"nombre": p["nombre"], "stock": p["stock"], "precio": p["precio"]}
    return "Producto no encontrado"

@mcp.tool()
def get_order(nombre: str, cantidad: int):
    """ Calcula el total de la compra"""
    products = MEDS+SUPPLIES
    for p in products:
        if nombre.lower() in p["nombre"].lower():
            return {
            "nombre": p["nombre"], 
            "cantidad": cantidad, 
            "total": p["precio"] * cantidad}
    return "Producto no encontrado"

if __name__ == "__main__":
    mcp.run()