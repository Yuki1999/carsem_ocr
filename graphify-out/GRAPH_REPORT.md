# Graph Report - .  (2026-06-01)

## Corpus Check
- 96 files · ~1,247,609 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 661 nodes · 1203 edges · 54 communities detected
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `_tenant_repository_session()` - 23 edges
2. `HistoryRepository` - 21 edges
3. `Base` - 18 edges
4. `TimestampMixin` - 17 edges
5. `UuidPrimaryKeyMixin` - 17 edges
6. `_database_stores_enabled()` - 14 edges
7. `build_packet_submission_draft()` - 14 edges
8. `TenantOwnedMixin` - 14 edges
9. `_build_extract_payload()` - 13 edges
10. `_build_platform_insights_payload()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `LlmSettingsRepository` --uses--> `LlmConfig`  [INFERRED]
  app/repositories/llm_settings.py → app/db/models.py
- `LlmSettingsRepository` --uses--> `TenantSetting`  [INFERRED]
  app/repositories/llm_settings.py → app/db/models.py
- `AuditRepository` --uses--> `AuditLog`  [INFERRED]
  app/repositories/audit.py → app/db/models.py
- `HistoryRepository` --uses--> `HistoryAsset`  [INFERRED]
  app/repositories/history.py → app/db/models.py
- `HistoryRepository` --uses--> `HistoryRecord`  [INFERRED]
  app/repositories/history.py → app/db/models.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (77): _auto_rotate_pdf_with_ocrmypdf(), _auto_rotate_pdf_with_osd(), _build_customs_submission_context(), _build_customs_submission_prompt(), _build_extract_payload(), _build_history_preview_assets(), _build_platform_insights_payload(), _build_platform_recommendations() (+69 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (0):

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (20): AssetRef, _decode_text(), _is_text_file(), LocalAssetStorage, _normalize_component(), _normalize_relative_path(), collect_legacy_output(), copy_legacy_record_assets() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (31): _append_page_margins_to_markdown(), _collect_page_margin_items(), _collect_text_nodes(), _decode_text(), _dedupe_page_margin_items(), _download_and_parse_zip(), _extract_file_url(), _extract_margin_text() (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (26): _clean_payload_text(), _flatten_submission_payload(), _get_next_declaration_no(), _safe_json(), submit_to_customs_site(), _to_text(), _accept_dialog(), _fill_submission_form() (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.24
Nodes (25): create_api_key(), CreatedApiKey, main(), parse_scopes(), DeclarativeBase, ApiClient, ApiKey, AuditLog (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (26): _build_detail_reviews(), _build_field_reviews(), _build_header(), _build_invoice_group_quantities(), build_packet_submission_draft(), _build_packing_groups(), _default_detail(), _detail_from_invoice_line() (+18 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (19): buildLlmSettingsPayloadForTest(), createId(), inferLlmProvider(), loadLlmSettings(), normalizeCustomsSubmitMode(), normalizeLlmConfig(), appendDraftDetailRow(), buildDraftSummary() (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (23): _build_chat_completions_endpoint(), _extract_assistant_content(), _extract_first_json_object(), _load_json_dict(), _normalize_content(), _parse_detected_dict(), _post_chat_completions(), _post_chat_completions_with_curl() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (13): AuditRepository, _looks_secret_key(), _redact(), redact_audit_payload(), AppSettings, get_settings(), PermissionError, build_system_tenant_context() (+5 more)

### Community 10 - "Community 10"
Cohesion: 0.26
Nodes (19): _apply_detected_header_alias_overrides(), _build_default_detail_row(), build_empty_submission_draft(), build_submission_draft(), _build_submission_draft_from_llm(), _ensure_details(), _extract_numeric_text(), _fill_default_header_values() (+11 more)

### Community 11 - "Community 11"
Cohesion: 0.24
Nodes (20): _build_summary(), _decode_text(), delete_history_record(), _extract_zip_to_dir(), get_history_asset_path(), get_history_primary_text(), get_history_zip_path(), _has_meaningful_value() (+12 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (5): _asset_file_payload(), _dedupe_files(), HistoryRepository, _looks_text(), row_id()

### Community 13 - "Community 13"
Cohesion: 0.21
Nodes (19): _cell_value(), _column_index_from_cell_ref(), _column_name(), _compact_row(), _detail_header_map(), _escape_markdown_cell(), _fallback_sheet_defs(), _node_text() (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.21
Nodes (4): _apply_job_updates(), build_request_hash(), JobRepository, _tenant_uuid()

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (9): buildDocTypeOptionsForVendor(), chooseTemplateSelection(), isCommonTemplateVendor(), normalizeTemplateVendor(), normalizeVendorKey(), resolveDocTypeForVendor(), resolveTemplateForSelection(), sameTemplateVendor() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.34
Nodes (13): _common_default_templates(), _default_templates(), load_templates(), _normalize_customs_mapping(), _normalize_template(), _normalize_template_vendor(), normalize_templates(), _read_json() (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.38
Nodes (11): _default_settings(), _infer_provider(), load_llm_settings(), _normalize_customs_submit_mode(), _normalize_item(), normalize_llm_settings(), _read_json(), resolve_active_llm_config() (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.35
Nodes (10): _bbox_from_obj(), _bbox_intersects(), extract_fields_by_regions(), _page_idx_from_dict(), parse_region_rules(), RegionRule, _text_from_dict(), TextNode (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.47
Nodes (7): buildFallbackPlatformInsights(), buildInsightCards(), buildRecommendations(), normalizePlatformInsights(), normalizeRecentHistory(), toNumber(), toText()

### Community 20 - "Community 20"
Cohesion: 0.33
Nodes (6): chooseDefaultEvidenceTab(), classifyEvidenceFile(), getLowerPath(), getPath(), pickPrimaryOriginalFile(), resolveOriginalPreviewFile()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (2): get_agent_context(), _scopes_from_payload()

### Community 22 - "Community 22"
Cohesion: 0.43
Nodes (6): buildExtractionLaunchReview(), buildFieldDetailView(), hasDetectedValue(), hasText(), isMissingTemplateName(), stringifyRawValue()

### Community 23 - "Community 23"
Cohesion: 0.48
Nodes (4): create_engine_from_settings(), create_session_factory(), get_db_session(), get_session_factory()

### Community 24 - "Community 24"
Cohesion: 0.29
Nodes (0):

### Community 25 - "Community 25"
Cohesion: 0.47
Nodes (3): buildExtractRequestFields(), normalizeOcrEngine(), normalizeTemplateOcrEngine()

### Community 26 - "Community 26"
Cohesion: 0.47
Nodes (4): _enable_tenant_rls(), _grant_app_role_privileges(), Create multitenant foundation schema.  Revision ID: 20260601_0001 Revises: Creat, upgrade()

### Community 27 - "Community 27"
Cohesion: 0.7
Nodes (4): _make_xlsx(), test_build_extract_payload_routes_xlsx_to_excel_text(), test_run_excel_and_read_text_adds_compact_table_for_sparse_invoice_rows(), test_run_excel_and_read_text_reads_xlsx_rows()

### Community 28 - "Community 28"
Cohesion: 0.4
Nodes (0):

### Community 29 - "Community 29"
Cohesion: 0.83
Nodes (3): bootstrap(), renderBootError(), tryRecoverAndReload()

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (2): buildAutoModeStatusView(), resolveStageLabel()

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (2): choosePreferredMarkdownPreview(), isImageOnlyMarkdown()

### Community 32 - "Community 32"
Cohesion: 0.83
Nodes (3): get_or_create_tenant(), load_tenant(), _looks_like_uuid()

### Community 33 - "Community 33"
Cohesion: 0.83
Nodes (3): _database_url(), run_migrations_offline(), run_migrations_online()

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (0):

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (0):

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (0):

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (0):

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (0):

### Community 39 - "Community 39"
Cohesion: 0.67
Nodes (0):

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (0):

### Community 41 - "Community 41"
Cohesion: 0.67
Nodes (0):

### Community 42 - "Community 42"
Cohesion: 0.67
Nodes (0):

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0):

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Operational commands.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0):

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0):

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0):

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0):

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0):

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0):

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0):

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0):

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0):

## Knowledge Gaps
- **12 isolated node(s):** `Operational commands.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。`, `优先点击常见的保存/提交按钮，找不到时再退回到原生表单提交。`, `尽量等待提交后的页面反馈完成，避免立即读取结果导致误判。` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 43`** (2 nodes): `layoutDensity.test.js`, `countSelector()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `__init__.py`, `Operational commands.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `test_project_structure.py`, `test_backend_structure_imports()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `test_health.py`, `test_readiness_endpoint_reports_basic_checks_without_db_mode()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `test_llm_extract.py`, `test_run_llm_extract_falls_back_to_curl_for_gemini_ssl_eof()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `test_create_api_key_command.py`, `test_parse_scopes_accepts_comma_and_space_separated_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `test_api_keys.py`, `test_api_key_hash_verifies_without_storing_plain_secret()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (2 nodes): `test_audit_repository.py`, `test_redact_audit_payload_masks_secret_fields()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (2 nodes): `test_migration_sql.py`, `test_initial_migration_enables_rls_for_tenant_tables()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (2 nodes): `test_platform_insights.py`, `test_platform_insights_api_summarizes_queue_templates_review_and_automation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuditRepository` connect `Community 9` to `Community 5`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `HistoryRepository` (e.g. with `HistoryAsset` and `HistoryRecord`) actually correct?**
  _`HistoryRepository` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Operational commands.`, `使用 Playwright 登录报关系统并提交一份草稿数据。`, `记录弹窗文案，并确保弹窗被接受，不阻塞后续页面脚本。` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.03 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._