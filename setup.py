from setuptools import setup, find_packages

setup(
    name='mapbots',  # Replace with your own package name
    version='0.1.0',  # The initial release version
    author='Eric Manley',
    author_email='eric.manley@drake.edu',
    description='tools for making softbots that operate on maps',
    long_description=open('README.md').read(),  # This could be your README file
    long_description_content_type='text/markdown',  # This is important if your README is in Markdown
    url='https://github.com/ericmanley/ai_map_environments',  # Project home page or repository URL
    packages=find_packages(),  # Finds packages in your project and makes them installable
    install_requires=[
        "networkx",
        "osmnx",
        "matplotlib",
        "copy",
        "mapclassify"
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  # Minimum version requirement of Python
    # Add any additional package configuration here
)