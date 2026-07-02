from setuptools import setup, find_packages

setup(
    name="bridge-bot-dashboard",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "discord.py>=2.0.0",
        "python-dotenv>=0.19.0",
        "pandas>=1.3.0",
        "openpyxl>=3.0.0",
        "flask>=2.0.0",
        "requests>=2.26.0",
        "gunicorn>=20.0.0",
    ],
)
