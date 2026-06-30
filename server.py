from fastmcp import FastMCP

from tools.transport import register_transport_tools
from tools.project import register_project_tools
from tools.utility import register_utility_tools
from tools.session import register_session_tools
from tools.tracks import register_track_tools
from tools.bounce import register_bounce_tools
from tools.pipeline import register_pipeline_tools
from tools.library import register_library_tools

mcp = FastMCP("logic-pro")

register_transport_tools(mcp)
register_project_tools(mcp)
register_utility_tools(mcp)
register_session_tools(mcp)
register_track_tools(mcp)
register_bounce_tools(mcp)
register_pipeline_tools(mcp)
register_library_tools(mcp)

if __name__ == "__main__":
    mcp.run()
