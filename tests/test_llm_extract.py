import json
import subprocess
import types

import requests

import app.llm_extract as llm_extract


def test_run_llm_extract_falls_back_to_curl_for_gemini_ssl_eof(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.exceptions.SSLError(
            "HTTPSConnectionPool(host='generativelanguage.googleapis.com', port=443): "
            "Max retries exceeded with url: /v1beta/openai/chat/completions "
            "(Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] "
            "EOF occurred in violation of protocol (_ssl.c:1006)')))"
        )

    def fake_run(cmd, capture_output, text, timeout, check):
        assert cmd[0] == "curl"
        body = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"invoice_no":"INV-001"}',
                        }
                    }
                ]
            }
        )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=f"{body}\n__HTTP_STATUS__:200",
            stderr="",
        )

    monkeypatch.setattr(llm_extract.requests, "post", fake_post)
    monkeypatch.setattr(
        llm_extract,
        "subprocess",
        types.SimpleNamespace(run=fake_run),
        raising=False,
    )

    result = llm_extract.run_llm_extract(
        text="Invoice No: INV-001",
        user_prompt="提取 invoice_no",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        model="gemini-2.0-flash",
        api_key="test-key",
    )

    assert result["detected"] == {"invoice_no": "INV-001"}
