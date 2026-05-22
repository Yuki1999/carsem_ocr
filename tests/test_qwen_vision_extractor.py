import json

import pytest

import app.qwen_vision_extractor as qwen_mod


def test_parse_qwen_vision_response_accepts_plain_json():
    parsed = qwen_mod.parse_qwen_vision_response('{"发票号":"INV-001"}')

    assert parsed == {"发票号": "INV-001"}


def test_parse_qwen_vision_response_accepts_fenced_json():
    parsed = qwen_mod.parse_qwen_vision_response('```json\n{"发票号":"INV-001"}\n```')

    assert parsed == {"发票号": "INV-001"}


def test_parse_qwen_vision_response_extracts_embedded_json_object():
    parsed = qwen_mod.parse_qwen_vision_response('以下是结果：{"发票号":"INV-001","币种":"USD"}')

    assert parsed == {"发票号": "INV-001", "币种": "USD"}


def test_parse_qwen_vision_response_raises_on_non_json_output():
    with pytest.raises(RuntimeError, match="JSON"):
        qwen_mod.parse_qwen_vision_response("not json")


def test_build_qwen_vision_messages_includes_prompt_and_images():
    messages = qwen_mod.build_qwen_vision_messages(
        vendor="ASE",
        doc_type="invoice",
        llm_prompt="提取发票号",
        image_inputs=[
            {
                "name": "page-1.png",
                "mime_type": "image/png",
                "data_url": "data:image/png;base64,ZmFrZQ==",
                "content": b"fake",
            }
        ],
    )

    assert messages[0]["role"] == "system"
    content = messages[1]["content"]
    assert any(item["type"] == "text" and "提取发票号" in item["text"] for item in content)
    assert any(item["type"] == "image_url" and item["image_url"]["url"].startswith("data:image/png;base64,") for item in content)


def test_run_qwen_vision_extract_builds_history_assets(monkeypatch):
    monkeypatch.setattr(
        qwen_mod,
        "render_qwen_input_images",
        lambda **kwargs: [
            {
                "name": "page-1.png",
                "mime_type": "image/png",
                "data_url": "data:image/png;base64,ZmFrZQ==",
                "content": b"fake-image",
            }
        ],
    )
    monkeypatch.setattr(
        qwen_mod,
        "_post_qwen_chat_completion",
        lambda **kwargs: (
            {"choices": [{"message": {"content": '{"发票号":"INV-001"}'}}]},
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        ),
    )

    result = qwen_mod.run_qwen_vision_extract(
        file_name="invoice.pdf",
        file_bytes=b"%PDF-1.4 fake",
        vendor="ASE",
        doc_type="invoice",
        llm_prompt="提取发票号",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.5-plus",
        api_key="secret",
    )

    assert result["detected"] == {"发票号": "INV-001"}
    assert result["model"] == "qwen3.5-plus"
    assert result["preview"].startswith("{")
    assert any(item["path"] == "qwen_vision/raw-response.json" for item in result["history_assets"])
    assert any(item["path"] == "qwen_vision/preview.md" for item in result["history_assets"])
    assert any(item["path"] == "qwen_vision/pages/page-1.png" for item in result["history_assets"])
    raw_asset = next(item for item in result["history_assets"] if item["path"] == "qwen_vision/raw-response.json")
    assert json.loads(raw_asset["content"].decode("utf-8"))["choices"][0]["message"]["content"] == '{"发票号":"INV-001"}'
