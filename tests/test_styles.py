from crpm.styles import get_custom_css


def test_alert_descendant_text_inherits_readable_colors() -> None:
    css = get_custom_css()
    assert ".stInfo div, .stInfo p, .stInfo span, .stInfo label, .stInfo li" in css
    assert ".stWarning div, .stWarning p, .stWarning span, .stWarning label, .stWarning li" in css
    assert ".stError div, .stError p, .stError span, .stError label, .stError li" in css
    assert '.stAlert [data-testid="stMarkdownContainer"]' in css


def test_widget_labels_have_explicit_contrast_rules() -> None:
    css = get_custom_css()
    assert '[data-testid="stWidgetLabel"] p' in css
    assert '[data-testid="stRadio"] label' in css
    assert '[data-testid="stCheckbox"] label' in css
    assert '[data-testid="stSlider"] [data-testid="stWidgetLabel"] p' in css


def test_sidebar_alerts_have_explicit_readable_contrast_rules() -> None:
    css = get_custom_css()
    assert '[data-testid="stSidebar"] .stWarning' in css
    assert '[data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] p' in css
    assert '[data-testid="stSidebar"] .stInfo' in css
    assert '[data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] p' in css


def test_conformance_note_and_workflow_board_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-note" in css
    assert ".crpm-workflow-board" in css
    assert ".crpm-workflow-board svg" in css
    assert "width: 100%;" in css
    assert "height: auto;" in css
    assert ".crpm-empty-state" in css
    assert ".crpm-inline-empty" in css
    assert ".js-plotly-plot .hovertext path" in css
    assert ".js-plotly-plot .hovertext text" in css
    assert ".crpm-conformance-hero" in css
    assert ".crpm-conformance-stage-header" in css
    assert ".crpm-conformance-report-band" in css
    assert ".crpm-conformance-evidence-band" in css


def test_primary_button_and_inspector_styles_exist() -> None:
    css = get_custom_css()
    assert '.stButton button[kind="primary"]:focus' in css
    assert '[data-testid="stBaseButton-primary"] *' in css
    assert ".crpm-selection-card" in css
    assert ".crpm-detail-card" in css
    assert ".crpm-model-card-grid" in css
    assert ".crpm-ranked-table" in css
    assert ".crpm-rank-pill" in css
    assert ".crpm-table__metric-track" in css
    assert ".crpm-chip--conformant" in css


def test_conformance_compact_shell_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-conformance-kpi-strip" in css
    assert ".crpm-conformance-kpi-strip--rail" in css
    assert '[data-testid="stColumn"]:has(.crpm-inspector-deck-marker)' in css
    assert "max-height: calc(100vh - 5rem);" in css
    assert "overflow-y: auto;" in css
    assert ".crpm-inspector-deck__heading" in css
    assert ".crpm-inspector-orbit__thumb" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "min-height: 2rem;" in css
    assert "max-height: 360px;" in css
    assert ".crpm-workflow-board--horizontal" in css


def test_overview_and_bi_card_styles_exist() -> None:
    css = get_custom_css()
    assert ".crpm-dashboard-topbar" in css
    assert ".crpm-dashboard-badge--watch" in css
    assert ".crpm-dashboard-bar-list" in css
    assert ".crpm-dashboard-card-stack" in css
    assert ".crpm-filter-parent-label" in css
    assert ".crpm-filter-composer" in css
    assert ".crpm-active-filter-summary" in css
    assert '[data-testid="stBaseButton-tertiary"]' in css
    assert ".crpm-dashboard-section-title" in css
    assert ".crpm-overview-command-center" in css
    assert ".crpm-overview-map-frame" in css
    assert "height: clamp(360px, 46vh, 540px);" in css
    assert ".crpm-overview-map-frame--expanded" in css
    assert ".crpm-overview-map-frame--expanded {\n        height: auto;" in css
    assert "overflow-x: auto;" in css
    assert "overflow-y: hidden;" in css
    assert ".crpm-overview-map-frame .crpm-workflow-board {\n        display: flex;" in css
    assert ".crpm-overview-map-frame .crpm-workflow-board svg {\n        width: auto !important;" in css
    assert "height: 100% !important;" in css
    assert "width: 100% !important;" in css
    assert ".crpm-overview-map-frame--expanded .crpm-workflow-board {\n        height: auto;" in css
    assert ".crpm-bi-card-grid" in css
    assert ".crpm-page-card-grid" in css
    assert ".crpm-reading-order-band" in css
    assert ".crpm-shell-hero--compact" in css
    assert ".crpm-shell-hero__meta" in css
    assert ".crpm-run-context" in css
    assert "grid-template-columns: minmax(0, 1fr) auto;" in css
    assert ".crpm-run-context__chip strong" in css
    assert ".crpm-retained-state-chip" in css
    assert ".crpm-chip--watch" in css
    assert ".crpm-chip--deviation-heavy" in css
    assert ".crpm-header-badges" in css
    assert ".crpm-build-badge" in css
    assert ".crpm-fmup-badge" in css
    assert ".crpm-sidebar-provenance" in css


def test_dfg_map_canvas_has_desktop_height_guard() -> None:
    css = get_custom_css()
    assert ".crpm-dfg-map-canvas" in css
    assert "overflow-x: auto;" in css
    assert "overflow-y: hidden;" in css
    assert "align-items: center;" in css
    assert "justify-content: center;" in css
    assert "min-height: clamp(320px, 36vh, 460px);" in css
    assert "max-width: 100%;" in css
    assert "height: clamp(320px, 38vh, 480px);" in css


def test_footer_uses_compact_signature_without_body_logo() -> None:
    css = get_custom_css()
    assert ".crpm-footer--compact" in css
    assert "min-height: 1.6rem;" in css
    assert ".crpm-footer__text" in css
    assert "font-size: 0.78rem;" in css


def test_dashboard_header_avoids_cockpit_clipping() -> None:
    css = get_custom_css()
    assert '[data-testid="stHeader"]' in css
    assert "position: relative !important;" not in css
    assert "scroll-padding-top: 4.25rem;" in css
    assert "overflow-anchor: none;" in css
    assert '[data-testid="stMain"],\n    .stMain,\n    section.stMain' in css
    assert ".crpm-header-badges {\n        position: fixed;" in css
    assert "left: calc(var(--crpm-sidebar-width) + 0.78rem);" in css
    assert "max-width: calc(100vw - var(--crpm-sidebar-width) - 9.5rem);" in css
    assert "right: 8rem;" in css
    assert "z-index: 1000001;" in css
    assert ".crpm-dashboard-map-toolbar" in css
    assert "scroll-margin-top: 4.25rem;" in css
    assert "@media (max-width: 1180px)" in css


def test_sidebar_width_is_tokenized_for_process_map_space() -> None:
    css = get_custom_css()
    assert "--crpm-sidebar-width: 12.75rem;" in css
    assert "min(1720px, 100%)" in css
    assert "min-width: var(--crpm-sidebar-width) !important;" in css
    assert "width: var(--crpm-sidebar-width) !important;" in css


def test_dense_filter_text_keeps_readable_minimum_sizes() -> None:
    css = get_custom_css()
    assert ".crpm-active-filter-summary__title {\n        font-size: 0.74rem;" in css
    assert ".crpm-active-filter-summary__chip span {\n        font-size: 0.72rem;" in css
    assert ".crpm-conformance-hero__badge span {\n        font-size: 0.72rem;" in css


def test_main_expander_summary_has_readable_light_surface() -> None:
    css = get_custom_css()
    assert '[data-testid="stMainBlockContainer"] [data-testid="stExpander"] > details > summary' in css
    assert "background: rgba(252, 251, 253, 0.96) !important;" in css
    assert "color: var(--crpm-text) !important;" in css


def test_conformance_model_cards_stay_inside_narrow_rails() -> None:
    css = get_custom_css()
    assert ".crpm-model-card-grid {\n        display: grid;\n        gap: 0.6rem;\n        width: 100%;" in css
    assert ".crpm-model-card {\n        box-sizing: border-box;" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(min(100%, 8.5rem), 1fr));" in css


def test_ranked_tables_do_not_force_right_rail_overflow() -> None:
    css = get_custom_css()
    assert ".crpm-ranked-table caption" in css
    assert ".crpm-ranked-table {\n        border: 1px solid rgba(71, 88, 79, 0.1);" in css
    assert "max-width: 100%;" in css
    assert ".crpm-ranked-table__scroller {\n        width: 100%;" in css
    assert "overflow-x: auto;" in css
    assert "table-layout: fixed;" in css
    assert "overflow-wrap: anywhere;" in css
    assert "white-space: normal;" in css
    assert ".crpm-ranked-table .crpm-table__cell--label {" in css
    assert ".crpm-ranked-table--wide th" in css
    assert "min-width: 6.5rem;" in css
    assert "min-width: 11rem;" in css
    assert "overflow-wrap: break-word;" in css
    assert ".crpm-ranked-table .crpm-table__cell--num {" in css
    assert "min-width: 4.2rem;" in css
    assert ".crpm-ranked-table .crpm-table__metric-track {\n        min-width: 0;" in css
    assert ".crpm-ranked-table .crpm-chip {\n        width: 100%;" in css
    assert "text-overflow: ellipsis;" in css
