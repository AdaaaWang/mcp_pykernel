from setuptools import find_namespace_packages, setup
setup(
    name='cmsagent',
    version='0.1.0',
    description='Computational Materials Science Agent',
    packages=find_namespace_packages(
          where='./',
          include=['cmsagent', 'cmsagent.*']
      ),
    install_requires=['mcp',
                      'ase>=3.22.0',
                      'pymatgen',
                      'numpy>=1.7',
                      'matplotlib',
                      'importlib_resources'
                      ],
)
