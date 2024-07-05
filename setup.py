from setuptools import setup, find_packages

setup(
    name="fast",
    version="2.0.0",
    description="Flag Acquisition and Submission Tool ─ Easily manage your exploits in A/D competitions",
    author="Dušan Lazić",
    author_email="lazicdusan@protonmail.com",
    url="https://lazicdusan.com/fast",
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
    ],
    packages=["client", "server", "shared"],
    package_data={"web": ["dist/*", "dist/assets/*"]},
    py_modules=[
        "cli",
        "client",
        "database",
        "dsl",
        "handler",
        "models",
        "runner",
        "server",
    ],
    entry_points={
        "console_scripts": [
            "av_server=server.main:main",
            "av_persister=server.workers.persister:main",
            "av_submitter=server.workers.submitter:main",
            "av_client=client.main:main",
        ]
    },
)
