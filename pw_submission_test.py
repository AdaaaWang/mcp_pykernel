import os
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, BlobResourceContents
import logging
import base64
import subprocess
import datetime

# Set up logging (this just prints messages to your terminal for debugging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the MCP server object
mcp = FastMCP()

# Here's where you define your tools (functions the AI can use)
@mcp.tool()
def submit_quantum_espresso_job(job_name: str) -> str:
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
        "ymshi@perlmutter.nersc.gov",              # User + HostName
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
def main():
    logger.info('Starting your-new-server')
    mcp.run('stdio')
    # submit_quantum_espresso_job("Si")

if __name__ == "__main__":
    main()
