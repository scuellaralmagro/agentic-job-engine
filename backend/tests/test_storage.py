from aje.extraction.storage import compute_hash, save_upload


def test_hash_is_stable():
    assert compute_hash(b"abc") == compute_hash(b"abc")
    assert compute_hash(b"abc") != compute_hash(b"xyz")


def test_save_upload_writes_file_and_is_idempotent():
    path1, h1 = save_upload(b"hello", "cv.pdf")
    assert path1.exists()
    assert path1.read_bytes() == b"hello"
    assert path1.suffix == ".pdf"
    path2, h2 = save_upload(b"hello", "cv.pdf")
    assert path1 == path2 and h1 == h2
