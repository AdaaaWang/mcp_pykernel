import os
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import logging
from typing import Literal

from cmsagent.tools.ssh_tools import ssh_info_init, run_ssh_command, run_scp_transfer
import cmsagent.tools.slurm_manager as slrumtool
import cmsagent.tools.qe_generator as qetool

from emmet.core.symmetry import CrystalSystem

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

@mcp.resource("ssh://{init}")
async def start(init: str) -> list:
    """
    Please call this function once the session starts.
    You are a materials scientist specializing in using HPC resources for computational materials science.
    You might be asked to work with the remote server.
    When you need to write files to the remote server, please do that in the local directory first, 
    and then use the SCP tool to transfer files to the remote server.
    When you need to read a very large file (for example, the output file of scientific computation software), 
    please use the SCP tool to download the file to the local directory first.
    """
    return 0

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

@mcp.tool()
def check_dims(mat_id: str) -> str:
    """ 
    Take input material id, return the dimension of the system

    Parameters
    ----------
    mat_id : str
        material id from the material project database.

    Return
    ------
    dimensionality : str
        Return the predicted dimension of the material. 0 = nanoparticle,
        1 = nanowire, etc.

    Notes
    -----
    This function calls analyze_dimensionality from ASE library in the background.
    The output dimensionality will be based on the largest chunk. This might not
    be accurate, please use this with caution.
    """
    return qetool.check_dims(**locals())

@mcp.tool()
def search_material(
        chemsys: str | None = None,
        crystal_system: CrystalSystem | None = None,
        density_min: float | None = None,
        density_max: float | None = None,
        elements: str | None = None,
        exclude_elements: str | None = None,
        formula: str | None = None,
        num_elements_min: int | None = None,
        num_elements_max: int | None = None,
        num_sites_min: int | None = None,
        num_sites_max: int | None = None,
        spacegroup_symbol: str | None = None,
        volume_min: float | None = None,
        volume_max: float | None = None,
        dimension: int | None = None) -> str:
    """ Search through material project database using input parameters
    and return the material ids from the material project database that
    match the criteria.

    Parameters
    ----------
    chemsys : str, optional
        Chemical system, for example "Si-O" for system with both Si and O
    crystal_system : CrystalSystem or None
        CrystalSystem object. Run GetCrystalSystem or directly call
        emmet.core.symmetry to get this
    density_min : float, optional
        Minimum density (g/cm^3). Must provide both min and max density
    density_max : float, optional
        Maximum density (g/cm^3). Must provide both min and max density
    elements : str, optional
        A list of element as a long string with each value separated by a comma.
        For example "Si,O" to search for system with either "S", "O" or both.
    exclude_elements : str, optional
        A list of element as a long string with each value separated by a comma.
        This will exclude these elements from the search
    formula : str, optional
        Search for crystal that reduces to that formula. For multiple formula
        put them in a list. Wildcard is allowed for example "Si*"
    num_elements_min : int
        Minimum number of elements
    num_element_max : int
        Maximum number of elements
    num_sites_min : int
        Minimum number of atoms in the unit cell
    num_sites_max : int
        Maximum number of atoms in the unit cell
    spacegroup_symbol : str, optional
        Spacegroup symbol in international short symbol notation
    volume_min : float
        Minimum volume in angstrom^3
    volume_max : float
        Maximum volume in angstrom^3
    dimension : {0,1,2,3}
        Interger in {0,1,2,3} corresponding to the dimensionality of the structure.
        For example, 0 = nanoparticle, 1 = nanowire etc.

    Return
    ------
    mat_ids : str
        Return a comma-separated value (in string) containing all material
        ids that match the description.
    """ 
    return qetool.search_material(**locals())


@mcp.tool()
def write_pw_input(
        mat_id: str,
        fname: str,
        prefix: str,
        kpt_sampling: list[int] | None = None,
        calculation: str = "scf",
        verbosity: str = "low",
        restart_mode: str = "from_scratch",
        nstep: int | None = None,
        iprint: int | None = None,
        tprnfor: bool = True,
        tstress: bool = True,
        dt: float | None = None,
        outdir: str = "./tmp",
        wfcdir: str = "./tmp",
        pseudo_dir: str = "./",
        max_seconds: float | None = None,
        conv_thr: float = 1.0e-06,
        etot_conv_thr: float = 1.0e-08,
        forc_conv_thr: float = 0.0001,
        disk_io: str = "nowf",
        tefield: bool = False,
        dipfield: bool = False,
        lelfield: bool | None = None,
        nberrycyc: int | None = None,
        lorbm: bool | None = None,
        lberry: bool | None = None,
        gdir: int | None = None,
        nppstr: int | None = None,
        gate: bool | None = None,
        twochem: bool | None = None,
        lfcp: bool | None = None,
        trism: bool | None = None,
        nbnd: int | None = None,
        tot_charge: float | None = None,
        tot_magnetization: float | None = None,
        ecutrho: float = None,
        ecutwfc: float = None,
        ecutfock: float | None = None,
        nr1: int | None = None,
        nr2: int | None = None,
        nr3: int | None = None,
        nr1s: int | None = None,
        nr2s: int | None = None,
        nr3s: int | None = None,
        nosym: bool | None = None,
        nosym_evc: bool | None = None,
        noinv: bool | None = None,
        no_t_rev: bool | None = None,
        force_symmorphic: bool | None = None,
        use_all_frac: bool | None = None,
        occupations: str = "smearing",
        smearing: str = "gauss",
        degauss: float = 0.01,
        nspin: int | None = None,
        noncolin: bool | None = None,
        input_dft: str | None = None,
        ace: bool | None = None,
        exx_fraction: float | None = None,
        screening_parameter: float | None = None,
        exxdiv_treatment: str | None = None,
        x_gamma_extrapolation: bool | None = None,
        ecutvcut: float | None = None,
        mixing_beta: float | None = None,
        mixing_mode: str | None = None,
        mixing_ndim: int = 6,
        assume_isolated: str | None = None,
        diagonalization: str = "david",
        emaxpos: float | None = None,
        eopreg: float | None = None,
        edir: int | None = None,
        cell_dofree: str | None = None) -> str:
    """ Write input for for the quantum espresso pw.x

    Parameters
    ----------
    mat_id : str
        material id from the material project database.
    fname : str
        Name of the quantum espresso input file to write
    pseudofiles : dict[str, str]
        Dictionary mapping element to the psedopotential file
    kpt_sampling : list(str), optional
        Uniform kpt sampling grid. Example: [3,4,5] is
        to have 3 kpts along x, 4 along y and 5 along z.
        Default to None (Gamma only). If mode is bands
        this will be ignored.

    The rest of the input parameters are pw.x input parameters.
    Here's what they look like:

    PW.x input parameters
    ---------------------
    prefix: str,
    calculation: str = "scf",
    verbosity: str = "low",
    restart_mode: str = "from_scratch",
    nstep: int | None = None,
    iprint: int | None = None,
    tprnfor: bool = True,
    tstress: bool = True,
    dt: float | None = None,
    outdir: str = "./tmp",
    wfcdir: str = "./tmp",
    pseudo_dir: str = "./",
    max_seconds: float | None = None,
    conv_thr: float = 1.0e-06,
    etot_conv_thr: float = 1.0e-08,
    forc_conv_thr: float = 0.0001,
    disk_io: str = "nowf",
    tefield: bool = False,
    dipfield: bool = False,
    lelfield: bool | None = None,
    nberrycyc: int | None = None,
    lorbm: bool | None = None,
    lberry: bool | None = None,
    gdir: int | None = None,
    nppstr: int | None = None,
    gate: bool | None = None,
    twochem: bool | None = None,
    lfcp: bool | None = None,
    trism: bool | None = None,
    nbnd: int | None = None,
    tot_charge: float | None = None,
    tot_magnetization: float | None = None,
    ecutrho: float = None,
    ecutwfc: float = None,
    ecutfock: float | None = None,
    nr1: int | None = None,
    nr2: int | None = None,
    nr3: int | None = None,
    nr1s: int | None = None,
    nr2s: int | None = None,
    nr3s: int | None = None,
    nosym: bool | None = None,
    nosym_evc: bool | None = None,
    noinv: bool | None = None,
    no_t_rev: bool | None = None,
    force_symmorphic: bool | None = None,
    use_all_frac: bool | None = None,
    occupations: str = "smearing"
    smearing: str = "gauss"
    degauss: float = 0.01,
    nspin: int | None = None,
    noncolin: bool | None = None,
    input_dft: str | None = None,
    ace: bool | None = None,
    exx_fraction: float | None = None,
    screening_parameter: float | None = None,
    exxdiv_treatment: str | None = None,
    x_gamma_extrapolation: bool | None = None,
    ecutvcut: float | None = None,
    mixing_beta: float | None = None,
    mixing_mode: str | None = None,
    mixing_ndim: int = 6,
    assume_isolated: str | None = None,
    diagonalization: str = "david",
    emaxpos: float | None = None,
    eopreg: float | None = None,
    edir: int | None = None,
    cell_dofree: str | None = None


    Please search the pw.x documentation: https://www.quantum-espresso.org/Doc/INPUT_PW.html
    and insert input as necessary (leave them
    as None if there is no need to change). Ask user for input if there is
    something that is unclear.

    Return
    ------
    path_to_pw_input_file : str
        path to the input file for pw.x

    """
    """
    def obtain_pw_inputs_dictionary() -> Dict[str, PWInputTypes]:
        tmp = super().__dict__
        new_dict = {key: item for key, item in tmp.items() if item is not None}
        return new_dict
    """
    return qetool.write_pw_input(**locals())

@mcp.tool()
async def load_pseudopotentials_ls_results(files: str) -> TextContent:
    """
    For a given string as output of the 'ls pseudopotential_folder',
    parse the string to get the pseudopotential files.
    
    Args:
        files: Output of 'ls directory_path'.
        e.g.: 
        'Ag_ONCV_PBE-1.0.upf     Cl_ONCV_PBE-1.2.upf     Hg_ONCV_PBE-1.0.upf ...'
    """
    return qetool.load_pseudopotentials_ls_results(**locals())


# This is the main entry point for your server
if __name__ == "__main__":
    logger.info('Starting CMS Main Server...')
    mcp.run('stdio')