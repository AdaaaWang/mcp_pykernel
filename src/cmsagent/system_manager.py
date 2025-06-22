import os
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import logging
from typing import Literal

from cmsagent.tools.ssh_tools import ssh_info_init, run_ssh_command, run_scp_transfer
import cmsagent.tools.slurm_manager as slrumtool

SSH_CONFIG = {
    'host': None,
    'username': None, 
    'key_path': None
}
WORK_DIR_REMOTE = "/global/cfs/cdirs/m4480/MCP_example"
WORK_DIR_LOCAL = "/Users/adawang/Documents/Physics/mcp/mcp_pykernel/workdir"

# Set up logging (this just prints messages to your terminal for debugging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP()

@mcp.resource("ssh://{config}")
async def list_ssh_resources(config: str) -> list:
    """
    List available resources for the MCP server.
    """
    return {
        "uri": "config",
        "SSH Configuration": SSH_CONFIG, 
        "Remote Work Directory": WORK_DIR_REMOTE,
        "Local Work Directory": WORK_DIR_LOCAL
        }

@mcp.tool()
async def ssh_info_init_tool(host: str, username: str, key_path: str) -> str:
    """
    Initialize SSH connection configuration.
    
    Args:
        host: Host address
        username: SSH username
        key_path: SSH private key path
    
    Returns:
        Connection status message.
    """
    return ssh_info_init(SSH_CONFIG, host, username, key_path)

@mcp.tool()
async def change_remote_working_directory_tool(directory: str) -> str:
    """
    Change the working directory on the remote server.
    
    Args:
        directory: The new working directory path.
    
    Returns:
        A message indicating success or failure.
    """
    if not os.path.isabs(directory):
        return "Error: The directory must be an absolute path."
    
    global WORK_DIR_REMOTE
    WORK_DIR_REMOTE = directory
    return f"Working directory changed to {WORK_DIR_REMOTE}."

@mcp.tool()
async def change_local_working_directory_tool(directory: str) -> str:
    """
    Change the working directory on the local machine.
    
    Args:
        directory: The new working directory path.
    
    Returns:
        A message indicating success or failure.
    """
    if not os.path.isabs(directory):
        return "Error: The directory must be an absolute path."
    
    global WORK_DIR_LOCAL
    WORK_DIR_LOCAL = directory
    return f"Local working directory changed to {WORK_DIR_LOCAL}."

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
    return await run_ssh_command(SSH_CONFIG, command, timeout)

@mcp.tool()
async def run_scp_transfer_tool(
    local_path: str,
    remote_path: str,
    direction: Literal["upload", "download"] = "upload",
    recursive: bool = False,
    timeout: int = 30
) -> dict:
    """
    Transfer files between local and remote servers using SCP.
    
    Args:
        local_path: The path to the local file or directory.
        remote_path: The path to the remote file or directory.
        direction: 'upload' to send files to the remote server, 'download' to retrieve files from the remote server.
        recursive: Whether to transfer directories recursively (default is False).
        timeout: Timeout for the SCP command, in seconds (default is 30 seconds).
    
    Returns:
        A dictionary containing the transfer result, including success status, exit code, stdout, stderr, and command.
    
    Raises:
        asyncio.TimeoutError: If the transfer exceeds the specified timeout.
        Exception: For any other errors during file transfer.
    """
    return await run_scp_transfer(SSH_CONFIG, local_path, remote_path, direction, recursive, timeout)

@mcp.tool()
async def set_slurm_defaults(
    account: str,
    **kwargs
) -> TextContent:
    """
    Sets default Slurm configuration using key-value pairs.
    'account' is required. Any other Slurm options can be passed as keyword arguments.
    Example: set_slurm_defaults(account="m1234", queue="regular", constraint="gpu")

    Args:
        account: The Slurm account to charge (e.g., m1234).
        **kwargs: Arbitrary key-value pairs for other Slurm defaults.

    Returns:
        A confirmation message summarizing all defaults set.
    """
    return slrumtool.set_slurm_defaults(account,**kwargs)

@mcp.tool()
async def add_slurm_defaults(
    **kwargs
) -> TextContent:
    """
    Adds or updates key-value pairs in the current Slurm configuration.
    Does not clear existing settings.

    Args:
        **kwargs: One or more key-value pairs to add or update.
                  For example: project_dir="/path/to/project", partition="gpu"

    Returns:
        A confirmation message summarizing the full, updated configuration.
    """
    return slrumtool.add_slurm_defaults(**kwargs)

@mcp.tool()
async def prepare_sbatch_script_perlmutter(
    job_script_path: str,
    modules: str,
    nodes: int,
    time_limit: str,
) -> TextContent:
    """
    Prepares a sbatch script for user verification before submission.
    If you want to create a slurm job file, use this funciton. Do not try to do it yourself.
    This tool DOES NOT submit the job.

    Args:
        job_script_path: The full path to the job script you want to run (e.g., /path/to/my_job.sh).
            Is user asks for a  (Quantum Espresso)  QE job: srun pw.x $flags -input scf.in >& scf.out.$SLURM_JOB_ID with correct srun command.
        modules: The modules to load for the job.
            If QE job use:
                module load espresso/7.0-libxc-5.2.2-cpu
                export SLURM_CPU_BIND="cores"
                export OMP_PROC_BIND=spread
                export OMP_PLACES=threads
                export OMP_NUM_THREADS=8
                export HDF5_USE_FILE_LOCKING=FALSE
        nodes: The number of nodes to request.
        time_limit: The time limit for the job in HH:MM:SS format (e.g., "01:30:00").
        

    Returns:
        A verification message and the full sbatch script content for the user to review.
    """
    return slrumtool.prepare_sbatch_script(job_script_path, modules, nodes, time_limit)

# This is the main entry point for your server
if __name__ == "__main__":
    logger.info('Starting CMS Main Server...')
    mcp.run('stdio')