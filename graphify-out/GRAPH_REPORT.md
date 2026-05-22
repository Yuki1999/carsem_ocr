# Graph Report - /home/qqr/carsem_ocr  (2026-04-10)

## Corpus Check
- 134 files · ~356,878 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 356 nodes · 580 edges · 27 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `_build_extract_payload()` - 12 edges
2. `normalizeSubmissionDraft()` - 10 edges
3. `_parse_zip_content()` - 10 edges
4. `build_submission_draft()` - 9 edges
5. `run_mineru_and_read_text()` - 8 edges
6. `_build_submission_draft_from_llm()` - 8 edges
7. `merge_submission_draft()` - 8 edges
8. `submit_to_customs_site_with_playwright()` - 8 edges
9. `save_history_record()` - 8 edges
10. `_history_root()` - 8 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Group 0"
Cohesion: 0.06
Nodes (38): _auto_rotate_pdf_with_ocrmypdf(), _auto_rotate_pdf_with_osd(), _build_customs_submission_context(), _build_customs_submission_prompt(), _build_extract_payload(), _build_history_preview_assets(), _build_rotation_candidates(), _count_detected_hits() (+30 more)

### Community 1 - "Group 1"
Cohesion: 0.03
Nodes (0):

### Community 2 - "Group 2"
Cohesion: 0.15
Nodes (27): _append_page_margins_to_markdown(), _collect_page_margin_items(), _collect_text_nodes(), _decode_text(), _dedupe_page_margin_items(), _download_and_parse_zip(), _extract_file_url(), _extract_margin_text() (+19 more)

### Community 3 - "Group 3"
Cohesion: 0.26
Nodes (19): _apply_detected_header_alias_overrides(), _build_default_detail_row(), build_empty_submission_draft(), build_submission_draft(), _build_submission_draft_from_llm(), _ensure_details(), _extract_numeric_text(), _fill_default_header_values() (+11 more)

### Community 4 - "Group 4"
Cohesion: 0.24
Nodes (20): _build_summary(), _decode_text(), delete_history_record(), _extract_zip_to_dir(), get_history_asset_path(), get_history_primary_text(), get_history_zip_path(), _has_meaningful_value() (+12 more)

### Community 5 - "Group 5"
Cohesion: 0.14
Nodes (20): _accept_dialog(), _fill_submission_form(), _first_locator(), _group_submission_payload(), _locator_count(), _raise_if_submit_feedback_indicates_failure(), 尽量等待提交后的页面反馈完成，避免立即读取结果导致误判。, 根据最近一次弹窗消息判断网站是否明确返回了失败。 (+12 more)

### Community 6 - "Group 6"
Cohesion: 0.32
Nodes (12): _build_history_assets(), _build_image_input(), build_qwen_vision_messages(), parse_qwen_vision_response(), _post_qwen_chat_completion(), _render_pdf_images(), _render_pdf_images_with_pdftoppm(), _render_pdf_images_with_pypdfium2() (+4 more)

### Community 7 - "Group 7"
Cohesion: 0.35
Nodes (10): appendDraftDetailRow(), buildDraftSummary(), createEmptyDetailRow(), createEmptySubmissionDraft(), normalizeLegacyHeader(), normalizeSubmissionDraft(), removeDraftDetailRow(), toText() (+2 more)

### Community 8 - "Group 8"
Cohesion: 0.38
Nodes (11): _default_settings(), _infer_provider(), load_llm_settings(), _normalize_customs_submit_mode(), _normalize_item(), normalize_llm_settings(), _read_json(), resolve_active_llm_config() (+3 more)

### Community 9 - "Group 9"
Cohesion: 0.32
Nodes (11): _build_chat_completions_endpoint(), _extract_assistant_content(), _extract_first_json_object(), _load_json_dict(), _normalize_content(), _parse_detected_dict(), _post_chat_completions(), _post_chat_completions_with_curl() (+3 more)

### Community 10 - "Group 10"
Cohesion: 0.42
Nodes (10): _default_templates(), load_templates(), _normalize_customs_mapping(), _normalize_template(), normalize_templates(), _read_json(), reset_templates(), save_templates() (+2 more)

### Community 11 - "Group 11"
Cohesion: 0.29
Nodes (6): buildLlmSettingsPayloadForTest(), createId(), inferLlmProvider(), loadLlmSettings(), normalizeCustomsSubmitMode(), normalizeLlmConfig()

### Community 12 - "Group 12"
Cohesion: 0.35
Nodes (10): _bbox_from_obj(), _bbox_intersects(), extract_fields_by_regions(), _page_idx_from_dict(), parse_region_rules(), RegionRule, _text_from_dict(), TextNode (+2 more)

### Community 13 - "Group 13"
Cohesion: 0.33
Nodes (6): chooseDefaultEvidenceTab(), classifyEvidenceFile(), getLowerPath(), getPath(), pickPrimaryOriginalFile(), resolveOriginalPreviewFile()

### Community 14 - "Group 14"
Cohesion: 0.28
Nodes (3): buildDocTypeOptionsForVendor(), normalizeVendorKey(), resolveDocTypeForVendor()

### Community 15 - "Group 15"
Cohesion: 0.57
Nodes (6): _clean_payload_text(), _flatten_submission_payload(), _get_next_declaration_no(), _safe_json(), submit_to_customs_site(), _to_text()

### Community 16 - "Group 16"
Cohesion: 0.29
Nodes (0):

### Community 17 - "Group 17"
Cohesion: 0.47
Nodes (3): buildExtractRequestFields(), normalizeOcrEngine(), normalizeTemplateOcrEngine()

### Community 18 - "Group 18"
Cohesion: 0.7
Nodes (4): _read_first_json(), _read_first_text(), _read_output_dir(), run_opendataloader_and_read_text()

### Community 19 - "Group 19"
Cohesion: 0.67
Nodes (2): choosePreferredMarkdownPreview(), isImageOnlyMarkdown()

### Community 20 - "Group 20"
Cohesion: 0.67
Nodes (2): buildAutoModeStatusView(), resolveStageLabel()

### Community 21 - "Group 21"
Cohesion: 0.83
Nodes (3): bootstrap(), renderBootError(), tryRecoverAndReload()

### Community 22 - "Group 22"
Cohesion: 0.67
Nodes (0):

### Community 23 - "Group 23"
Cohesion: 1.0
Nodes (1): Persistence and settings store modules.

### Community 24 - "Group 24"
Cohesion: 1.0
Nodes (0):

### Community 25 - "Group 25"
Cohesion: 1.0
Nodes (0):

### Community 26 - "Group 26"
Cohesion: 1.0
Nodes (0):

## Knowledge Gaps
- **11 isolated node(s):** `Persistence and settings store modules.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。`, `优先点击常见的保存/提交按钮，找不到时再退回到原生表单提交。`, `尽量等待提交后的页面反馈完成，避免立即读取结果导致误判。` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Group 23`** (2 nodes): `__init__.py`, `Persistence and settings store modules.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Group 24`** (2 nodes): `test_project_structure.py`, `test_backend_structure_imports()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Group 25`** (2 nodes): `test_llm_extract.py`, `test_run_llm_extract_falls_back_to_curl_for_gemini_ssl_eof()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Group 26`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Persistence and settings store modules.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Group 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Group 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03 - nodes in this community are weakly interconnected._
- **Should `Group 5` be split into smaller, more focused modules?**
  _Cohesion score 0.14 - nodes in this community are weakly interconnected._