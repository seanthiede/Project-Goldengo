from setuptools import setup, find_packages

setup(
    name="project_goldengo",
    version="0.1.0",
    description="Project Goldengo Trading Tools and Strategies",
    packages=find_packages(),
    install_requires=[
        "backtesting",
        "pandas",
        "numpy"
    ],
    python_requires='>=3.7',
)