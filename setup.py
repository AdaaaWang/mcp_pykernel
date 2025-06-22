from setuptools import setup
setup(
    name='CMS-agent',
    version='0.1.0',
    description='Computational Materials Science Agent',
    install_requires=['mcp',
                      'ase>=3.22.0',
                      'pymatgen',
                      'numpy>=1.7',
                      'matplotlib',
                      'importlib_resources'
                      ],
)
