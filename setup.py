from setuptools import setup, find_packages

setup(
    name='sans_app',
    version='0.1',
    packages=['sans_app', 'sans_app.support'],
    include_package_data=True,
    package_data={
        "sans_app": [
            "example_data/example_SANS_files/**/*",
            "example_data/example_SANS_configurations/**/*",
            "example_data/example_SANS_models/**/*",
        ]
    },
    url='',
    license='MIT open source',
    author='Frank Heinrich',
    author_email='fheinrich@cmu.edu',
    description='SANS data visualization and analysis'
)
