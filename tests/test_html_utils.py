from components.html_utils import escape_html


def test_escape_html_quotes_and_tags():
    assert escape_html('<img src=x onerror="alert(1)">') == (
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    )


def test_escape_html_handles_none():
    assert escape_html(None) == ""
