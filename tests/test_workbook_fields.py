"""Workbook field names: one module, used to write a workbook and to read it back."""

from ddtools.workbook_fields import field_key, section_of


def test_a_field_key_is_its_section_and_a_slug_of_its_label():
    assert field_key(1, "D&D Beyond link  (e.g. https://x)") == "v1.s1.d-d-beyond-link-e-g-https-x"
    assert field_key(9, "Ash") == "v1.s9.ash"


def test_a_long_label_is_cut_to_48_characters_without_a_trailing_dash():
    key = field_key(3, "What the party doesn’t know yet (secrets). Goes in your DM notes only")
    slug = key.removeprefix("v1.s3.")
    assert len(slug) <= 48 and not slug.endswith("-")


def test_section_of_reads_the_section_back():
    assert section_of(field_key(12, "Anything")) == 12
    assert section_of(field_key(4, "Deal big damage") + ".3") == 4
    assert section_of("v2.s1.name") is None
    assert section_of("f_1") is None
