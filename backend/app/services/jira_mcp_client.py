import asyncio
from fastmcp import Client
import json

async def main():
    async with Client("http://127.0.0.1:8001/mcp/") as client:
        print("=" * 50)
        print("CREACIÓN DE TARJETAS JIRA VIA MCP")
        print("=" * 50)

        r = await client.call_tool(
            "crear_tarjeta_jira",
            {
                "titulo": "Nueva tarea de prueba",
                "prioridad": "alta",
                "proyecto": "Hackaton",
                "fecha_limite": "2026-05-20",
                "etiquetas": ["MCP", "Integracion", "Jira"]
            }
        )
        print("\nResultado:")
        print(json.dumps(r.data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())