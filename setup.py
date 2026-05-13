from setuptools import find_packages, setup

setup(
    name='netbox-dhcp',
    version='0.1',
    description='Managed DHCP leases from Netbox',
    install_requires=[],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
