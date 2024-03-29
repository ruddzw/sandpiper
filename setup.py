from setuptools import setup

setup(
    name='sandpiper',
    version='0.1a',
    description='A mini framework for web applications with Mako and MongoDB',
    author='Rudd Zwolinski',
    author_email='rudd@ruddzw.com',
    url='https://github.com/ruddzw/sandpiper/',
    install_requires=[
        "Mako>=0.6.2",
        "pymongo>=2.1.1"
    ],
    packages=['sandpiper']
)
