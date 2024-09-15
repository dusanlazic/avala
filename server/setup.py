from setuptools import find_packages, setup

setup(
    name="avala-server",
    version="0.1.0",
    description="Avala Server",
    author="Dušan Lazić",
    author_email="lazicdusan@protonmail.com",
    url="https://lazicdusan.com/avala",
    install_requires=[
        "requests",
        "loguru",
        "pyyaml",
        "sqlalchemy",
        "psycopg2-binary",
        "pyparsing",
        "fastapi",
        "uvicorn",
        "APScheduler==3.10.1",
        "pika",
        "aio_pika",
        "click",
        "broadcaster",
        "asyncpg",
        "uvloop",
        "httptools",
        "pydantic-settings",
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "avl=avala.cli:cli",
        ]
    },
)
