from setuptools import setup

setup(
    name="avala",
    version="0.1.0",
    description="Avala ─ A/D attack tool used by ECSC Team Serbia.",
    author="Dušan Lazić",
    author_email="lazicdusan@protonmail.com",
    url="https://lazicdusan.com/avala",
    install_requires=[
        "requests",
        "loguru",
        "pyyaml",
        "peewee",
        "psycopg2-binary",
        "pyparsing",
        "jsonschema",
        "fastapi",
        "python-socketio",
        "uvicorn",
        "APScheduler==3.10.1",
        "addict",
        "pika",
        "aio_pika",
        "click",
    ],
    packages=["server", "client", "shared"],
    entry_points={
        "console_scripts": [
            "av=shared.cli:cli",
        ]
    },
)
