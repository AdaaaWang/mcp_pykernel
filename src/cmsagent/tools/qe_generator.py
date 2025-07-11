import os
from mcp.server.fastmcp import FastMCP
from typing import Dict, TypeAlias

import os
import io
import base64
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.bandstructure import HighSymmKpath
from ase.geometry.dimensionality import analyze_dimensionality
from ase.io.espresso import write_espresso_in
from mp_api.client import MPRester
from mcp.types import TextContent, ImageContent
from emmet.core.symmetry import CrystalSystem

from cmsagent.tools.qe_file_tools import parse_pw_output

import matplotlib.pyplot as plt
from ase.visualize.plot import plot_atoms

# Create the MCP server object
mcp = FastMCP()

api_key = "LsBfDY9s56tOWOUSmzZR7bboB8S5XvPN"
mpr = MPRester(api_key=api_key) 

@mcp.tool()
def GetCrystalSystem(cs: str) -> CrystalSystem:
    """
    Take input string crystal system and return the corresponding
    CrystalSystem object

    Parameters
    ----------
    cs : {'triclinic, monoclinic, orthorhombic, tetragonal, trigonal,
          hexagonal, cubic'}
        crystal system

    Return
    ------
    cs_object : CrystalSystem object
        crystal system object corresponding to the input cs
    """

    crystal_system_map = {
        "triclinic": CrystalSystem.tri,
        "monoclinic": CrystalSystem.mono,
        "orthorhombic": CrystalSystem.ortho,
        "tetragonal": CrystalSystem.tet,
        "trigonal": CrystalSystem.trig,
        "hexagonal": CrystalSystem.hex_,
        "cubic": CrystalSystem.cubic,
    }

    if cs in crystal_system_map:
        return crystal_system_map[cs]
    else:
        raise ValueError("{} is not a valid crystal system.".format(cs))
    
def _list_str_2_csv(list_str):
    return ",".join(list_str)

def _csv_2_list_str(csv):
    return csv.split(",")

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

    # Clean up input
    if density_min is not None and density_max is not None:
        density = [density_min, density_max]
    else:
        density = None

    if elements is not None:
        elements = _csv_2_list_str(elements)
    if exclude_elements is not None:
        exclude_elements = _csv_2_list_str(exclude_elements)

    if num_elements_min is not None and num_elements_max is not None:
        num_elements = [num_elements_min, num_elements_max]
    else:
        num_elements = None
    if num_sites_min is not None and num_sites_max is not None:
        num_sites = [num_sites_min, num_sites_max]
    else:
        num_sites = None

    if volume_min is not None and volume_max is not None:
        volume = [volume_min, volume_max]
    else:
        volume = None

    materials = mpr.materials.search(chemsys=chemsys,
                                     crystal_system=crystal_system,
                                     density=density,
                                     elements=elements,
                                     exclude_elements=exclude_elements,
                                     formula=formula,
                                     num_elements=num_elements,
                                     num_sites=num_sites,
                                     spacegroup_symbol=spacegroup_symbol,
                                     volume=volume)

    # Check the dimensionality
    if dimension is not None:
        mat_dim = []
        for mat in materials:
            if check_dims(mat.material_id.string) == str(dimension):
                mat_dim += [mat.material_id.string]

        
        if len(mat_dim) == 0:
            return TextContent(type="text", text="Material not found")
        else:
            return TextContent(type="text", text=_list_str_2_csv(mat_dim))

    if len(materials) == 0:
        return TextContent(type="text", text="Material not found")
    else:
        #return [TextContent(type="text", text=mat.material_id.string) for mat in materials]
        return TextContent(
                type="text", text=_list_str_2_csv(
                    [mat.material_id.string for mat in materials]))

@mcp.tool()
def check_dims(mat_id: str) -> str:
    """ Take input material id, return the dimension of the system

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

    # Convert the given material to the dimension of the material
    mat = mpr.materials.search(mat_id)[0]
    atoms = AseAtomsAdaptor.get_atoms(mat.structure)
    dim = analyze_dimensionality(atoms)


    return dim[0].dimtype

PWInputTypes: TypeAlias = str | float | int | bool

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
    
    # Construct kpoint
    #if calculation == "vc-relax" or calculation == "relax":
    mat = mpr.materials.search(mat_id)[0]
    atoms = AseAtomsAdaptor.get_atoms(mat.structure)
    try:
        psep_dict = get_pseudopotential(mat.elements)
    except KeyError as e:
        # The 'except' block catches the specific error and prints the helpful message.
        error_message = f"Error: Could not prepare job. {e}"
        return TextContent(type="text", text=error_message)
    
    # Get the dictionary of local variables
    local_vars = locals()

    # Filter out items where the value is None
    filtered_locals = {key: value for key, value in local_vars.items() if (value is not None) and (key is not "atoms")}
    
    if calculation == "bands":
        write_espresso_in(
            fname,
            atoms,
            **filtered_locals,
            pseudopotentials=psep_dict,
            kpts=HighSymmKpath(mat.structure).kpath,
            crystal_coordinates=True,
        )
    else:
        write_espresso_in(
            fname,
            atoms,
            **filtered_locals,
            pseudopotentials=psep_dict,
            kpts=kpt_sampling,
            crystal_coordinates=True,
        )
    return TextContent(type="text", text=os.path.join(os.getcwd(), fname))

pseudopotentials: Dict[str, str] = {}
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
    
    for filename in files:
        if filename.lower().endswith(".upf"):
            element = filename.split('_')[0]
            if not (element in pseudopotentials.keys()): # temp: load the first one.
                pseudopotentials[element] = filename
                count += 1
    
    success_msg = f"Successfully loaded {count} pseudopotentials from the directory."
    return TextContent(type="text", text=success_msg)

def get_pseudopotential(elements: list) -> Dict:
    jobpseudopotential: Dict[str, str] = {}
    for ele in elements:
        elename = ele.name
        jobpseudopotential[elename] = elename + "_ONCV_PBE-1.2.upf"
    return jobpseudopotential

@mcp.tool()
async def parse_pw_output_tool(filename: str) -> str:
    """
    Parse the Quantum ESPRESSO output file.
    Args:
        filename (str): Path to the Quantum ESPRESSO output file.
    Returns:
        tuple: A dictionary containing the success status, results, and convergence information.
    If no results are found, it returns a warning message with the file content.
    If results are found, it returns a dictionary with the results and convergence status.
    """
    result = parse_pw_output(filename)
    return result

@mcp.tool()
def plot_struct(mat_id: str, dir: int):
    """
    Plot the structure along direction

    Parameters
    ----------
    mat_id : str
        material id from the material project database.
    dir : int
        direction of camera 0 = x, 1 = y, 2 = z, 3 = rotate at (45,45,45)
    """

    mat = mpr.materials.search(mat_id)[0]
    atoms = AseAtomsAdaptor.get_atoms(mat.structure)

    if dir == 0:
        rotation = "90x,0y,0z"
    if dir == 1:
        rotation = "0x,90y,0z"
    if dir == 2:
        rotation = "0x,0y,90z"
    else:
        rotation = "45x,45y,45z"

    buf = io.BytesIO()
    fig, ax = plt.subplots()
    plot_atoms(atoms, ax=ax, rotation=rotation)
    ax.set_axis_off()
    
    plt.savefig(buf, format='png')
    img_bytes = buf.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    return ImageContent(type="image", data=img_base64, mimeType="image/png")


def main():
    mcp.run('stdio')

if __name__ == "__main__":
    main()
    print("Ready")
