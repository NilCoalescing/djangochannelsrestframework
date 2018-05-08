from setuptools import find_packages, setup

setup(
    name='djangochannelsrestframework',
    version="0.0.2",
    url='https://github.com/hishnash/djangochannelsrestframework',
    author='Matthaus Woolard',
    author_email='matthaus.woolard@gmail.com',
    description="RESTful API for WebSockets using django channels.",
    long_description=open('README.rst').read(),
    license='MIT',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'Django>=1.11',
        'channels>=2.1.1',
        'djangorestframework>=3.0'
    ],
    extras_require={
        'tests': [
            'pytest~=3.3',
            "pytest-django~=3.1",
            "pytest-asyncio~=0.8",
            'coverage~=4.4',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
