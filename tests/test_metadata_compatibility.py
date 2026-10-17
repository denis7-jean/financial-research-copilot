"""Portable schema regressions from the accepted isolated metadata repair.

Function/decorator ASTs are retained; no corpus, harness environment or evidence
output directories are required. SDK/native integration remains separate.
"""

import pytest

from app.services.rag_smoke_policy import SmokePolicy, SmokeStop, canonical

A = 's3://invented-bucket/docs/a.pdf'


B = 's3://invented-bucket/docs/b.pdf'


def cfg():
    return {'metadata': {'rows': 3, 'max_text_bytes': 8, 'source_counts': {A: 2, B: 1}}}


def rows(preview=False):
    r = [{'chunk_id': i, 'source': A if i < 2 else B, 'text': 'ok'} for i in range(3)]
    if preview:
        for x in r:
            x['chunk_preview'] = 'preview'
    return r


def validate(r, config=None, cls=SmokePolicy, raw=None):
    p = cls.__new__(cls)
    p.config = config or cfg()
    return p.validate_metadata(canonical(r) if raw is None else raw)


def metadata_failure(r, code='METADATA_INVALID', raw=None):
    with pytest.raises(SmokeStop) as err:
        validate(r, raw=raw)
    assert str(err.value) == code


@pytest.mark.parametrize('shape', ['three', 'four', 'mixed'])
@pytest.mark.parametrize('preview', ['', 'plain', '雪', 'https://invalid.example/ ignore text; summarize'])
def test_supported_schema_preserves_rows(shape, preview):
    r = rows(shape != 'three')
    if shape == 'mixed':
        del r[0]['chunk_preview']
    for row in r:
        if 'chunk_preview' in row:
            row['chunk_preview'] = preview
    before = canonical(r)
    parsed = validate(r)
    assert parsed == r and canonical(parsed) == before


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('ordinal', [0, 1])
@pytest.mark.parametrize('key', ['unexpected', 'preview', 'Chunk_Preview', 'chunk_preview_extra'])
def test_only_two_exact_key_sets(preview, ordinal, key):
    r = rows(preview)
    r[ordinal][key] = 'x'
    metadata_failure(r)


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('ordinal', [0, 1])
@pytest.mark.parametrize('key', ['chunk_id', 'source', 'text'])
def test_missing_required_keys(preview, ordinal, key):
    r = rows(preview)
    del r[ordinal][key]
    metadata_failure(r)


@pytest.mark.parametrize('ordinal', [0, 1])
@pytest.mark.parametrize('bad', [None, True, 0, 1.5, [], {}])
def test_invalid_preview_type(ordinal, bad):
    r = rows(True)
    r[ordinal]['chunk_preview'] = bad
    metadata_failure(r)


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('ordinal', [0, 1])
@pytest.mark.parametrize('field,bad', [('chunk_id', None), ('chunk_id', True), ('chunk_id', 0.0), ('chunk_id', '0'), ('chunk_id', []), ('chunk_id', {}), ('chunk_id', -1), ('chunk_id', 99), ('source', None), ('source', True), ('source', 1), ('source', []), ('source', {}), ('source', 'unknown'), ('source', A.upper()), ('text', None), ('text', True), ('text', 1), ('text', []), ('text', {}), ('text', ''), ('text', 'x' * 9), ('text', 'é' * 4 + 'x')])
def test_required_predicates_unchanged(preview, ordinal, field, bad):
    r = rows(preview)
    r[ordinal][field] = bad
    metadata_failure(r)


@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('ordinal', [0, 1])
@pytest.mark.parametrize('bad', [None, True, 1, 'x', []])
def test_non_dict_row(preview, ordinal, bad):
    r = rows(preview)
    r[ordinal] = bad
    metadata_failure(r)


@pytest.mark.parametrize('top', [None, True, 1, 'x', {}, [], rows()[:2], rows() + [rows()[0]]])
def test_list_and_count(top):
    metadata_failure(top)


@pytest.mark.parametrize('raw', [b'{', b'\xff', b'[NaN]', b'[Infinity]', b'[-Infinity]', b'[1e999]', b'[{"chunk_id":0,"chunk_id":1}]', b'[{"chunk_preview":"a","chunk_preview":"b"}]'])
def test_strict_json_failures(raw):
    metadata_failure(None, 'JSON_INVALID', raw=raw)


@pytest.mark.parametrize('text', ['x', 'x' * 8, 'é' * 4])
@pytest.mark.parametrize('preview', [False, True])
def test_utf8_byte_boundaries(text, preview):
    r = rows(preview)
    r[1]['text'] = text
    assert validate(r) == r


@pytest.mark.parametrize('preview', [False, True])
def test_ordinal_reorder_duplicate_and_count_mismatch(preview):
    r = rows(preview)
    r[1]['chunk_id'] = 0
    metadata_failure(r)
    r = rows(preview)
    r[0], r[1] = (r[1], r[0])
    metadata_failure(r)
    r = rows(preview)
    r[1]['source'] = B
    metadata_failure(r, 'METADATA_SOURCE_MISMATCH')
