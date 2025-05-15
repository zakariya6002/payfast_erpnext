from setuptools import setup, find_packages

setup(
    name='payfast_integration',
    version='0.0.1',
    description='PayFast Integration for Frappe',
    author='Zakariya',
    author_email='zhassan6002@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
