import os
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, BlobResourceContents
import logging
import base64
import subprocess
import datetime

from tools.ssh_tools import ssh_info_init, run_ssh_command

ssh_config = {
    'host': None,
    'username': None, 
    'key_path': None
}
WORK_DIR = "/global/cfs/cdirs/m4480/MCP_example"

# Set up logging (this just prints messages to your terminal for debugging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP()

@mcp.resource()
async def list_resources() -> list:
    """
    List available resources for the MCP server.
    """
    return {
        'SSH Configuration': ssh_config, 
        'Remote Work Directory': WORK_DIR,
        }

@mcp.tool()
async def ssh_info_init_tool(
    host: str,
    username: str, 
    key_path: str
) -> str:
    """
    Initialize SSH connection configuration.
    
    Args:
        host: Host address(e.g. perlmutter.nersc.gov)
        username: SSH username
        key_path: SSH private key path (default ~/.ssh/nersc)
    
    Returns:
        Connection status message
    """
    return ssh_info_init(ssh_config, host, username, key_path)

@mcp.tool()
async def run_ssh_command_tool(command: str, timeout: int = 30) -> dict:
    """
    Run a command on the remote server via SSH.
    Please optimize the command to make the number of calls to this tool as few as possible.
    If the system returns an error, please check the command and try again.
    Do not try for more than 5 times, as this will cause the system to become unresponsive.

    Args:
        command: bash command to execute on the remote server, in a string.
        timeout: timeout (seconds), default is 30 seconds
    Returns:
        A dictionary containing the execution result, including success status, exit code, stdout, stderr, and command.
    Raises:
        asyncio.TimeoutError: If the command execution exceeds the specified timeout.
        Exception: For any other errors during command execution.
    """
    return await run_ssh_command(ssh_config, command, timeout)


# This is the main entry point for your server
if __name__ == "__main__":
    logger.info('Starting CMS Main Server...')
    mcp.run('stdio')