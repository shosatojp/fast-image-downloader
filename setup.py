import setuptools

with open('README.md', 'rt', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='dlimg',
    version='0.1.4',
    author='shosatojp',
    author_email='me@shosato.jp',
    description='Fast image downloader',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/shosatojp/fast-image-downloader',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    scripts=['dlimg'],
    install_requires=[
        'aiohttp',
        'requests',
        'bs4',
        'aiofiles',
        'selenium',
    ],
)
