from setuptools import setup, find_packages

setup(
    name="coboarding",
    version="0.1",
    packages=find_packages(),
    install_requires=open('requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': [
            'coboarding-apply=coboarding.automation.job_applicator:main',
        ],
    },
)
