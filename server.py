from fastmcp import FastMCP

from tools.transport import register_transport_tools
from tools.project import register_project_tools
from tools.utility import register_utility_tools
from tools.session import register_session_tools

mcp = FastMCP("logic-pro")

register_transport_tools(mcp)
register_project_tools(mcp)
register_utility_tools(mcp)
register_session_tools(mcp)

if __name__ == "__main__":
    mcp.run()
