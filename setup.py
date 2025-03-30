from setuptools import setup, find_packages

setup(
    name="readthedocs-mcp",
    version="0.1.0",
    description="MCP server for Read the Docs documentation",
    author="hulkworks",
    author_email="hulkworks@protonmail.com",
    py_modules=["readthedocs"],  # This tells setuptools to include readthedocs.py
    install_requires=[
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
        "mcp[cli]>=1.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=24.0.0",
            "isort>=5.12.0",
        ],
    },
    python_requires=">=3.10",
) 