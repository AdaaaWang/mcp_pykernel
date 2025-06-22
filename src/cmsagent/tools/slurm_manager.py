import os
from typing import List, Dict
import logging
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# YMS TODO: make this HPC/JOB management class instead of slurm job.

# --- Global State ---
# This dictionary will hold the Slurm default parameters for the current session.
slurm_config: Dict[str, str] = {}

# Initialize FastMCP server for Slurm tools
mcp = FastMCP("slurm_manager")

logger = logging.getLogger(__name__)

def _parse_time_to_hours(time_str: str) -> float:
    """Helper function to convert HH:MM:SS to decimal hours."""
    try:
        h, m, s = map(int, time_str.split(':'))
        return h + m / 60 + s / 3600
    except ValueError:
        # Return 0 or raise an error if the format is incorrect
        logger.warning(f"Invalid time format '{time_str}'. Could not calculate hours.")
        return 0.0


# --- THIS IS THE MODIFIED, MORE GENERAL FUNCTION ---
@mcp.tool()
async def set_slurm_defaults(
    account: str,
    **kwargs
) -> TextContent:
    """
    Sets default Slurm configuration using key-value pairs.
    'account' is required. Any other Slurm options can be passed as keyword arguments.
    Example: set_slurm_defaults(account="m1234", queue="regular", partition="gpu")

    Args:
        account: The Slurm account to charge (e.g., m1234).
        **kwargs: Arbitrary key-value pairs for other Slurm defaults.

    Returns:
        A confirmation message summarizing all defaults set.
    """
    logger.info(f"Setting Slurm defaults. Provided args: account={account}, other_args={kwargs}")

    # Clear any previous defaults before setting new ones for this session
    slurm_config.clear() 
    
    # Start with the mandatory account
    slurm_config['account'] = account
    
    # Add all other provided keyword arguments to the configuration
    slurm_config.update(kwargs)
    
    # Create a clean summary string for the confirmation message
    config_summary = ", ".join([f"'{key}'='{value}'" for key, value in slurm_config.items()])
    success_msg = f"Slurm defaults set: {config_summary}."
    
    logger.info(f"Current slurm_config state: {slurm_config}")
    
    return TextContent(type="text", text=success_msg)

# --- NEW: Function to Add/Update Defaults ---
@mcp.tool()
async def add_slurm_defaults(
    **kwargs
) -> TextContent:
    """
    Adds or updates key-value pairs in the current Slurm configuration.
    Does not clear existing settings.

    Args:
        **kwargs: One or more key-value pairs to add or update.
                  For example: project_dir="/path/to/project", constraint="gpu"

    Returns:
        A confirmation message summarizing the full, updated configuration.
    """
    if not kwargs:
        return [TextContent(type="text", text="No attributes provided to add. Please provide key-value pairs.")]

    logger.info(f"Adding/updating Slurm defaults with: {kwargs}")
    slurm_config.update(kwargs)

    config_summary = ", ".join([f"'{key}'='{value}'" for key, value in slurm_config.items()])
    success_msg = f"Slurm defaults updated. Current config is now: {config_summary}."
    
    logger.info(f"Current slurm_config state: {slurm_config}")
    return TextContent(type="text", text=success_msg)

@mcp.tool()
async def prepare_sbatch_script_perlmutter(
    job_script_path: str,
    modules: str,
    nodes: int,
    time_limit: str,
) -> TextContent:
    """
    Prepares a sbatch script for user verification before submission.
    If you want to create a slurm job file, use this funciton. Do not thry to do it yourself.
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
    logger.info(f"Preparing sbatch script for '{job_script_path}'")

    # --- Verification Step 1: Check if defaults are set ---
    if 'account' not in slurm_config or 'partition' not in slurm_config:
        error_msg = "Error: Slurm defaults (account, partition) are not set. Please run `set_slurm_defaults` first."
        return [TextContent(type="text", text=error_msg)]

    # --- Verification Step 2: Check if the job script exists ---
    if not os.path.exists(job_script_path):
        error_msg = f"Error: The job script path '{job_script_path}' does not exist. Please provide a valid path."
        return [TextContent(type="text", text=error_msg)]

    # --- Calculate Node Hours for User Verification ---
    hours = _parse_time_to_hours(time_limit)
    node_hours = nodes * hours
    
    # --- Generate the sbatch script ---
    # Using an f-string with triple quotes makes formatting clean and easy.
    sbatch_script = f"""#!/bin/bash
#SBATCH -A {slurm_config['account']}
#SBATCH -q {slurm_config['queue']}
#SBATCH -C {slurm_config.get('constraint', 'cpu')}
#SBATCH -N {nodes}
#SBATCH -t {time_limit}
#SBATCH --job-name=mcp_submitted_job

{modules}

echo "--- Job started at $(date) ---"

# Execute the user's job script
date
srun {job_script_path}
date

echo "--- Job finished at $(date) ---"
"""
    
    verification_message = (
        f"VERIFICATION REQUIRED:\n"
        f"Please review the following sbatch script. This job will use approximately {node_hours:.2f} node-hours.\n"
        f"If this looks correct, you can pass the script content to the `submit_sbatch_script` tool."
    )
    
    # Return two separate text blocks for clarity in the agent's response
    return TextContent(type="text", text=verification_message + "\n" + f"```bash\n{sbatch_script}\n```")


if __name__ == "__main__":
    logger.info("Starting Slurm manager MCP server...")
    mcp.run(transport="stdio")
