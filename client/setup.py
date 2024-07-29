from setuptools import setup

setup(
    name="avala-client",
    version="0.1.0",
    description="Avala Client",
    author="Dušan Lazić",
    author_email="lazicdusan@protonmail.com",
    url="https://lazicdusan.com/avala",
    install_requires=[
        "requests",
        "loguru",
        "pyyaml",
        "sqlalchemy",
        "psycopg2-binary",
        "jsonschema",
        "APScheduler==3.10.1",
        "addict",
    ],
    packages=["avala"],
)
