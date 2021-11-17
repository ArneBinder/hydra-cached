from setuptools import find_packages, setup

# PEP0440 compatible formatted version, see:
# https://www.python.org/dev/peps/pep-0440/
#
# release markers:
#   X.Y
#   X.Y.Z   # For bugfix releases
#
# pre-release markers:
#   X.YaN   # Alpha release
#   X.YbN   # Beta release
#   X.YrcN  # Release Candidate
#   X.Y     # Final release

# version.py defines the VERSION and VERSION_SHORT variables.
# We use exec here so we don't import allennlp whilst setting up.
VERSION = {}  # type: ignore
with open("allennlp/version.py", "r") as version_file:
    exec(version_file.read(), VERSION)

setup(
    name="hydra-cached",
    version="0.0a1",
    description="Hydra instantiate, but cached!",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Science/Research",
        "Development Status :: 3 - Alpha",
        #"License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        #"Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="allennlp NLP deep learning machine reading",
    url="https://github.com/allenai/allennlp",
    author="Allen Institute for Artificial Intelligence",
    author_email="allennlp@allenai.org",
    license="Apache",
    packages=find_packages(
        exclude=[
            "*.tests",
            "*.tests.*",
            "tests.*",
            "tests",
            "test_fixtures",
            "test_fixtures.*",
        ]
    ),
    install_requires=[
        # TODO: read from requirements.txt
        "hydra-core",
        "joblib",
    ],
    entry_points={"console_scripts": ["instantiate=hydra_cached.main:main"]},
    #include_package_data=True,
    #python_requires=">=3.7.1",
    #zip_safe=False,
)
