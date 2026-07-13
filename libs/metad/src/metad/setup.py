from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="MetaDict",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A metadictionary development framework kit for Python 3.13+",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/metadict",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",
    install_requires=[],  # no external dependencies
)