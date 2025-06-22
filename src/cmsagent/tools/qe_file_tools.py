from ase.io.espresso import write_espresso_in, read_espresso_out

def check_scf_convergence(lines: list[str]) -> tuple[bool, int]:
    converged = False
    n_iter = 0
    for line in lines:
        if "convergence has been achieved" in line or "Convergence has been achieved" in line:
            converged = True
        if "iteration #" in line:
            n_iter += 1
    return converged, n_iter

def parse_pw_output(filename: str) -> tuple[bool, int]:
    with open(filename, 'r') as f:
        result_list = []
        text = f.read(10000)
        lines = f.readlines()
        for atoms in read_espresso_out(f):
            calc_info_dict = {}
            calculator = atoms.calc

            try:
                calc_info_dict['energy'] = calculator.results['energy']
            except KeyError:
                calc_info_dict['energy'] = None
            try:
                calc_info_dict['free_energy'] = calculator.results['free_energy']
            except KeyError:
                calc_info_dict['free_energy'] = None
            try:
                calc_info_dict['forces'] = calculator.results['forces']
            except KeyError:
                calc_info_dict['forces'] = None
            try:
                calc_info_dict['fermi energy'] = calculator.efermi
            except AttributeError:
                calc_info_dict['fermi energy'] = None
            try:
                calc_info_dict['dipole'] = calculator.dipole
            except AttributeError:
                calc_info_dict['dipole'] = None
            try:
                calc_info_dict['magmoms'] = calculator.magmoms
            except AttributeError:
                calc_info_dict['magmoms'] = None

            result_list.append(calc_info_dict)
    if len(result_list) == 0:
        print(f"Warning: No complete results found in {filename}.")
        return {
            'success': False,
            'file content': text
        }
    else:
        return {
            'success': True,
            'results': result_list,
            'is_coverged': check_scf_convergence(lines)
        }