from pathlib import Path

def root():
    return Path(__file__).parent.parent

def package_data():
    return root() / "slac_db" / "package_data"

def yaml():
    return root() / "slac_db" / "yaml"
