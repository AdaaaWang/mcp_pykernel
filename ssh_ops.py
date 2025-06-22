import os
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, BlobResourceContents
import logging
import base64
import subprocess
import datetime

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

# Create the MCP server object
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

# Here's where you define your tools (functions the AI can use)
@mcp.tool()
async def ssh_info_init(
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
    key_full_path = os.path.expanduser(key_path)
    if not os.path.exists(key_full_path):
        return f"Error: SSH private key {key_full_path} does not exist. Please check the path."
    
    ssh_config.update({
        'host': host,
        'username': username,
        'key_path': key_path
    })
    
    return f"SSH configuration: {username}@{host} (key: {key_path})"


@mcp.tool()
async def run_ssh_command(command: str, timeout: int = 30) -> dict:
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
    if not all([ssh_config['host'], ssh_config['username'], ssh_config['key_path']]):
        return {
            'success': False,
            'error': 'SSH connection not initialized, please first use tool ssh_connect.'
        }
    
    ssh_cmd = [
        'ssh',
        '-l', ssh_config['username'],
        '-i', os.path.expanduser(ssh_config['key_path']),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        ssh_config['host'],
        command+'; exit',
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        return {
            'success': True,
            'exit_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'command': command
        }
        
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': f'timeout:({timeout}sec)',
            'command': command
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'command': command
        }


@mcp.tool()
async def submit_quantum_espresso_job(job_name: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_job_dir = f"{job_name}_{timestamp}"
    base_dir = "/global/cfs/cdirs/m4480/MCP_example"

    script = f"""set -e
    cd {base_dir}
    echo "Creating job dir {remote_job_dir}"
    mkdir "{remote_job_dir}"
    cp scf.in sljob.sl "{remote_job_dir}/"
    cd "{remote_job_dir}"
    sbatch sljob.sl
    """
    
    env = os.environ.copy()           # keeps SSH_AUTH_SOCK and SKSESSION* vars

    ssh_cmd = [
        "ssh",
        "-i", os.path.expanduser("~/.ssh/nersc"),  # IdentityFile
        "-o", "BatchMode=yes",                     # fail fast if no key works
        "-o", "IdentitiesOnly=yes",                # ignore other keys in the agent
        "adawang@perlmutter.nersc.gov",              # User + HostName
        "bash", "-s"                               # run the script piped on stdin
    ]

    try:
        p = subprocess.run(
            ssh_cmd,
            input=script,
            text=True,
            capture_output=True,
            timeout=120,
            env=env
        )
    except subprocess.TimeoutExpired:
        return "Error: SSH connection timed out."

    if p.returncode != 0:
        return (f"SSH failed (exit {p.returncode}).\n"
                f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

    for line in p.stdout.splitlines():
        if line.startswith("Submitted batch job"):
            return line
    return f"Job submitted but job-ID not found:\n{p.stdout}"


# This is the main entry point for your server
if __name__ == "__main__":
    logger.info('Starting your-new-server')
    mcp.run('stdio')