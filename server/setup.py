from setuptools import setup

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
        "jsonschema",
        "fastapi",
        "uvicorn",
        "APScheduler==3.10.1",
        "addict",
        "pika",
        "aio_pika",
        "click",
        "broadcaster",
    ],
    packages=["avala"],
    entry_points={
        "console_scripts": [
            "avl=avala.cli:cli",
        ]
    },
)
