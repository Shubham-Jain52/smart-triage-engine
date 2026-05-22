"""Tests for Jira text extraction."""

from src.integrations.jira.text_utils import adf_to_text, jira_description_to_text, strip_html


def test_strip_html():
    assert "hello world" in strip_html("<p>hello <b>world</b></p>")


def test_adf_to_text():
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "VPN fails after login"}],
            }
        ],
    }
    assert "VPN fails after login" in adf_to_text(adf)


def test_jira_description_string():
    assert jira_description_to_text("Plain description") == "Plain description"
