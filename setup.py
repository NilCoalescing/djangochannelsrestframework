from setuptools import find_packages, setup

setup(
    name="djangochannelsrestframework",
    version="0.3.0",
    url="https://github.com/hishnash/djangochannelsrestframework",
    author="Matthaus Woolard",
    author_email="matthaus.woolard@gmail.com",
    description="RESTful API for WebSockets using django channels.",
    long_description=open("README.rst").read(),
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=["Django>=3.*", "channels>=3.0", "djangorestframework>=3.0"],
    extras_require={
        "tests": [
            "pytest~=5.4.0",
            "pytest-django~=3.4.1",
            "pytest-asyncio~=0.11.0",
            "coverage~=4.4",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
