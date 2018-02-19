from setuptools import find_packages, setup

setup(
    name='channels_api',
    version="0.5.0",
    url='https://github.com/linuxlewis/channels-api',
    author='Sam Bolgert',
    author_email='sbolgert@gmail.com',
    description="Helps build a RESTful API on top of WebSockets using channels.",
    long_description=open('README.rst').read(),
    license='BSD',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'Django>=1.11',
        'channels>=2.0.2',
        'djangorestframework>=3.0'
    ],
    extras_require={
        'tests': [
            'pytest~=3.3',
            "pytest-django~=3.1",
            "pytest-asyncio~=0.8",
            "channels>=2.0.2",
            'coverage~=4.4',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
