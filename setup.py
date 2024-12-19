from setuptools import setup, find_packages

setup(
    name='empyrebase',
    version='1.0.2',
    url='https://github.com/emrothenberg/empyrebase',
    description='A simple python wrapper for the Firebase API with current deps',
    author='emrothenberg',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='Firebase, Pyrebase, Google, Empyrebase',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'requests-toolbelt>=1.0.0',
        'requests>=2.31',
        'urllib3>=1.21.1,<2',
        'google-cloud-storage>=2.18.2',
        'oauth2client>=4.1.2',
        'pyjwt>=2.8.0',
        'pycryptodome>=3.6.4'
    ]
)
