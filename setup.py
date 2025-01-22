from setuptools import setup, find_packages

setup(
    name="app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "supabase",
        "python-dotenv",
        "pydantic"
    ],
) 