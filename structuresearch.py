from mcp.server.fastmcp import FastMCP

from pymatgen.io.ase import AseAtomsAdaptor
from ase.geometry.dimensionality import analyze_dimensionality
from mp_api.client import MPRester
from mcp.types import TextContent
from emmet.core.symmetry import CrystalSystem

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
        "triclinic": CrystalSystem.triclinic,
        "monoclinic": CrystalSystem.monoclinic,
        "orthorhombic": CrystalSystem.orthorhombic,
        "tetragonal": CrystalSystem.tetragonal,
        "trigonal": CrystalSystem.trigonal,
        "hexagonal": CrystalSystem.hexagonal,
        "cubic": CrystalSystem.cubic,
    }

    if cs in crystal_system_map:
        return crystal_system_map[cs]
    else:
        raise ValueError("{} is not a valid crystal system.".format(cs))
    

@mcp.tool()
def search(
        chemsys: str | list[str] | None = None,
        crystal_system: CrystalSystem | None = None,
        density: tuple[float,float] | None = None,
        elements: list[str] | None = None,
        exclude_elements: list[str] | None = None,
        formula: str | list[str] | None = None,
        num_elements: tuple[int, int] | None = None,
        num_sites: tuple[int, int] | None = None,
        spacegroup_symbol: str | None = None,
        volume: tuple[float, float] | None = None) -> str | list[str]:
    """ Search through material project database using input parameters
    and return the material ids from the material project database that
    match the criteria.

    Parameters
    ----------
    chemsys : str, list(str), optional
        Chemical system, for example "Si-O" for system with both Si and O
    crystal_system : CrystalSystem or None
        CrystalSystem object. Run GetCrystalSystem or directly call
        emmet.core.symmetry to get this
    density : tuple(float, float), optional
        Minimum and maximum density (g/cm^3) to consider.
    elements : list(str), optional
        A list of element. For example ["Si","O"] to search for system with
        either "S", "O" or both.
    exclude_elements : list(str), optional
        A list of element to exclude from the search
    formula : str, list(str), optional
        Search for crystal that reduces to that formula. For multiple formula
        put them in a list. Wildcard is allowed for example "Si*"
    num_elements: tuple(int,int), optional
        Minimum and maximum number of elements
    num_sites : tuple(int, int), optional
        Minimum and maximum number of atoms in the unit cell
    spacegroup_symbol : str, optional
        Spacegroup symbol in international short symbol notation
    volume : tuple(float, float), optional
        Minimum and Maximum volume
    dimension : {0,1,2,3}
        Dimensionality of the structure. 0 = nanoparticle, 1 = nanowire etc.

    Return
    ------
    mat_ids : list(str)
        Return a list containing all material ids that match the description.
    """ 

    materials = mpr.materials.search(chemsys,
                                     crystal_system=crystal_system,
                                     density=density,
                                     elements=elements,
                                     exclude_elements=exclude_elements,
                                     formula=formula,
                                     num_elements=num_elements,
                                     num_sites=num_sites,
                                     spacegroup_symbol=spacegroup_symbol,
                                     volume=volume)

    if len(materials) == 0:
        return "Material not found"
    else:
        return [TextContent(type="text", text=mat.material_id.string) for mat in materials]

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
    dim = analyze_dimensionality(dim)


    return dim[0].dimtype

def main():
    mcp.run('stdio')

if __name__ == "__main__":
    main()