def test_package_importable_and_versioned():
    import aje

    assert isinstance(aje.__version__, str)
    assert aje.__version__
