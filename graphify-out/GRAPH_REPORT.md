# Graph Report - .  (2026-05-23)

## Corpus Check
- 62 files · ~893,072 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 453 nodes · 782 edges · 33 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `build_packet_submission_draft()` - 14 edges
2. `_build_extract_payload()` - 12 edges
3. `_stringify()` - 12 edges
4. `normalizeSubmissionDraft()` - 11 edges
5. `_build_detail_reviews()` - 11 edges
6. `_parse_zip_content()` - 10 edges
7. `build_submission_draft()` - 9 edges
8. `run_mineru_and_read_text()` - 8 edges
9. `_build_submission_draft_from_llm()` - 8 edges
10. `merge_submission_draft()` - 8 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (44): _auto_rotate_pdf_with_ocrmypdf(), _auto_rotate_pdf_with_osd(), _build_customs_submission_context(), _build_customs_submission_prompt(), _build_extract_payload(), _build_history_preview_assets(), _build_platform_insights_payload(), _build_platform_recommendations() (+36 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (0):

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (31): _append_page_margins_to_markdown(), _collect_page_margin_items(), _collect_text_nodes(), _decode_text(), _dedupe_page_margin_items(), _download_and_parse_zip(), _extract_file_url(), _extract_margin_text() (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (26): _clean_payload_text(), _flatten_submission_payload(), _get_next_declaration_no(), _safe_json(), submit_to_customs_site(), _to_text(), _accept_dialog(), _fill_submission_form() (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.22
Nodes (26): _build_detail_reviews(), _build_field_reviews(), _build_header(), _build_invoice_group_quantities(), build_packet_submission_draft(), _build_packing_groups(), _default_detail(), _detail_from_invoice_line() (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.26
Nodes (19): _apply_detected_header_alias_overrides(), _build_default_detail_row(), build_empty_submission_draft(), build_submission_draft(), _build_submission_draft_from_llm(), _ensure_details(), _extract_numeric_text(), _fill_default_header_values() (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.24
Nodes (20): _build_summary(), _decode_text(), delete_history_record(), _extract_zip_to_dir(), get_history_asset_path(), get_history_primary_text(), get_history_zip_path(), _has_meaningful_value() (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.21
Nodes (19): _cell_value(), _column_index_from_cell_ref(), _column_name(), _compact_row(), _detail_header_map(), _escape_markdown_cell(), _fallback_sheet_defs(), _node_text() (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.3
Nodes (13): appendDraftDetailRow(), buildDraftSummary(), countPacketReviewItems(), createEmptyDetailRow(), createEmptyPacketMeta(), createEmptySubmissionDraft(), normalizeLegacyHeader(), normalizePacketMeta() (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.22
Nodes (9): buildDocTypeOptionsForVendor(), chooseTemplateSelection(), isCommonTemplateVendor(), normalizeTemplateVendor(), normalizeVendorKey(), resolveDocTypeForVendor(), resolveTemplateForSelection(), sameTemplateVendor() (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.34
Nodes (13): _common_default_templates(), _default_templates(), load_templates(), _normalize_customs_mapping(), _normalize_template(), _normalize_template_vendor(), normalize_templates(), _read_json() (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.32
Nodes (12): _build_history_assets(), _build_image_input(), build_qwen_vision_messages(), parse_qwen_vision_response(), _post_qwen_chat_completion(), _render_pdf_images(), _render_pdf_images_with_pdftoppm(), _render_pdf_images_with_pypdfium2() (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.32
Nodes (11): _build_chat_completions_endpoint(), _extract_assistant_content(), _extract_first_json_object(), _load_json_dict(), _normalize_content(), _parse_detected_dict(), _post_chat_completions(), _post_chat_completions_with_curl() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.38
Nodes (11): _default_settings(), _infer_provider(), load_llm_settings(), _normalize_customs_submit_mode(), _normalize_item(), normalize_llm_settings(), _read_json(), resolve_active_llm_config() (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (6): buildLlmSettingsPayloadForTest(), createId(), inferLlmProvider(), loadLlmSettings(), normalizeCustomsSubmitMode(), normalizeLlmConfig()

### Community 15 - "Community 15"
Cohesion: 0.35
Nodes (10): _bbox_from_obj(), _bbox_intersects(), extract_fields_by_regions(), _page_idx_from_dict(), parse_region_rules(), RegionRule, _text_from_dict(), TextNode (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.47
Nodes (7): buildFallbackPlatformInsights(), buildInsightCards(), buildRecommendations(), normalizePlatformInsights(), normalizeRecentHistory(), toNumber(), toText()

### Community 17 - "Community 17"
Cohesion: 0.33
Nodes (6): chooseDefaultEvidenceTab(), classifyEvidenceFile(), getLowerPath(), getPath(), pickPrimaryOriginalFile(), resolveOriginalPreviewFile()

### Community 18 - "Community 18"
Cohesion: 0.43
Nodes (6): buildExtractionLaunchReview(), buildFieldDetailView(), hasDetectedValue(), hasText(), isMissingTemplateName(), stringifyRawValue()

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (0):

### Community 20 - "Community 20"
Cohesion: 0.47
Nodes (3): buildExtractRequestFields(), normalizeOcrEngine(), normalizeTemplateOcrEngine()

### Community 21 - "Community 21"
Cohesion: 0.7
Nodes (4): _make_xlsx(), test_build_extract_payload_routes_xlsx_to_excel_text(), test_run_excel_and_read_text_adds_compact_table_for_sparse_invoice_rows(), test_run_excel_and_read_text_reads_xlsx_rows()

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (0):

### Community 23 - "Community 23"
Cohesion: 0.83
Nodes (3): bootstrap(), renderBootError(), tryRecoverAndReload()

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (2): buildAutoModeStatusView(), resolveStageLabel()

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (2): choosePreferredMarkdownPreview(), isImageOnlyMarkdown()

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (0):

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0):

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Persistence and settings store modules.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0):

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0):

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0):

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0):

## Knowledge Gaps
- **11 isolated node(s):** `Persistence and settings store modules.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。`, `优先点击常见的保存/提交按钮，找不到时再退回到原生表单提交。`, `尽量等待提交后的页面反馈完成，避免立即读取结果导致误判。` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (2 nodes): `layoutDensity.test.js`, `countSelector()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `__init__.py`, `Persistence and settings store modules.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `test_project_structure.py`, `test_backend_structure_imports()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `test_llm_extract.py`, `test_run_llm_extract_falls_back_to_curl_for_gemini_ssl_eof()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `test_platform_insights.py`, `test_platform_insights_api_summarizes_queue_templates_review_and_automation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Persistence and settings store modules.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._