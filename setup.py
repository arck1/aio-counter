import setuptools
from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

version = '0.1'

setup(
    name='aio-counter',
    version=version,

    author='arck1',
    author_email='a.v.rakhimov@gmail.com',

    description="Async counter with decrement after timeout (ttl)",
    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/arck1/aio-counter',
    download_url='https://github.com/arck1/aio-counter/archive/v{}.zip'.format(
        version
    ),
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    zip_safe=False,
    python_requires='>=3.7',
    packages=find_packages(exclude=["examples"]),
    keywords='aio asyncio counter inc dec increment decrement ttl'
)
