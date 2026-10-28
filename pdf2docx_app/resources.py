from pathlib import Path


def asset_path(*parts):
    """Resources resolve identically in source and the PyInstaller onedir bundle."""
    return Path(__file__).resolve().parent.joinpath('assets', *parts)
