"""Custom CSS styling for CRPM Process Mining Workbench."""


def get_custom_css() -> str:
    """Generate custom CSS for the Streamlit application."""
    return """
    <style>
    :root {
        --crpm-bg: #f5f3f8;
        --crpm-bg-soft: #efecf4;
        --crpm-sidebar: #1b2127;
        --crpm-sidebar-soft: #242b33;
        --crpm-sidebar-panel: #10161b;
        --crpm-sidebar-border: rgba(173, 191, 214, 0.16);
        --crpm-sidebar-text: #eef3f8;
        --crpm-sidebar-text-soft: #b4c0cd;
        --crpm-sidebar-accent: #6f88c6;
        --crpm-sidebar-width: 14rem;
        --crpm-surface: #fcfbfd;
        --crpm-surface-alt: #f7f4fa;
        --crpm-forest: #365348;
        --crpm-forest-strong: #274239;
        --crpm-lavender: #8e7aa8;
        --crpm-lavender-soft: #e8e0f0;
        --crpm-border: rgba(71, 88, 79, 0.16);
        --crpm-border-strong: rgba(71, 88, 79, 0.28);
        --crpm-shadow: 0 12px 28px rgba(50, 41, 66, 0.09);
        --crpm-shadow-soft: 0 8px 18px rgba(50, 41, 66, 0.06);
        --crpm-text: #1f2c25;
        --crpm-text-soft: #536159;
        --crpm-muted: #6d6b79;
        --crpm-info-bg: #eef2f8;
        --crpm-info-accent: #7180a8;
        --crpm-success-bg: #edf4ef;
        --crpm-success-accent: #557863;
        --crpm-warning-bg: #f7f2e9;
        --crpm-warning-accent: #8f7653;
        --crpm-error-bg: #f8ecef;
        --crpm-error-accent: #8b5c66;
    }

    .stApp {
        color: var(--crpm-text);
        scroll-padding-top: 4.25rem;
    }

    [data-testid="stAppViewContainer"],
    .stAppViewContainer,
    .main {
        background: linear-gradient(180deg, var(--crpm-bg-soft) 0%, var(--crpm-bg) 42%, #f8f6fb 100%) !important;
    }

    [data-testid="stHeader"],
    .stApp header {
        background: rgba(245, 243, 248, 0.96) !important;
        color: var(--crpm-text) !important;
        border-bottom: 1px solid rgba(71, 88, 79, 0.12) !important;
        padding: 0.32rem 0.65rem !important;
        box-shadow: 0 5px 16px rgba(50, 41, 66, 0.055) !important;
        backdrop-filter: blur(14px) !important;
    }

    [data-testid="stHeader"] [data-testid="stToolbar"],
    .stApp header [data-testid="stToolbar"] {
        color: var(--crpm-text) !important;
    }

    .block-container {
        max-width: min(1580px, 100%) !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding-top: 2.1rem !important;
        padding-bottom: 7rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        color: var(--crpm-text) !important;
    }

    .main .block-container,
    .main .block-container p,
    .main .block-container li {
        color: var(--crpm-text);
    }

    .stApp a {
        color: var(--crpm-forest-strong) !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--crpm-forest-strong) !important;
        letter-spacing: 0;
    }

    h1 {
        font-size: 1.92rem !important;
        margin-bottom: 0.52rem !important;
    }

    h2 {
        font-size: 1.45rem !important;
        margin-top: 0.44rem !important;
        margin-bottom: 0.28rem !important;
    }

    h3 {
        font-size: 1.18rem !important;
        margin-top: 0.3rem !important;
        margin-bottom: 0.16rem !important;
    }

    .crpm-dashboard-topbar {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.72rem;
        margin: 0.04rem 0 0.38rem 0;
        padding: 0.56rem 0.68rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.38);
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(28, 45, 64, 0.06);
    }

    .crpm-dashboard-topbar,
    .crpm-dashboard-map-toolbar,
    .crpm-dashboard-bar-list,
    .crpm-overview-map-frame,
    .crpm-conformance-kpi-strip,
    .crpm-conformance-inspector-grid {
        scroll-margin-top: 4.25rem;
    }

    .crpm-dashboard-topbar__copy {
        min-width: 0;
        display: grid;
        gap: 0.1rem;
    }

    .crpm-dashboard-topbar__label {
        font-size: 0.72rem;
        font-weight: 800;
        line-height: 1.1;
        color: #315f96;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    .crpm-dashboard-topbar__title {
        font-size: 1.08rem;
        font-weight: 800;
        line-height: 1.1;
        color: #142233;
        letter-spacing: 0;
    }

    .crpm-dashboard-topbar__subtitle,
    .crpm-dashboard-topbar__meta {
        font-size: 0.78rem;
        line-height: 1.22;
        color: #506174;
        letter-spacing: 0;
    }

    .crpm-dashboard-topbar__meta {
        font-size: 0.72rem;
        color: #697789;
    }

    .crpm-dashboard-topbar__badges {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.34rem;
        min-width: 14rem;
    }

    .crpm-dashboard-badge {
        display: inline-grid;
        gap: 0.04rem;
        min-width: 6.8rem;
        padding: 0.34rem 0.48rem;
        border-radius: 8px;
        border: 1px solid rgba(151, 166, 184, 0.34);
        background: #f8fafc;
        color: #26384d;
    }

    .crpm-dashboard-badge span {
        font-size: 0.7rem;
        line-height: 1.05;
        color: #667789;
    }

    .crpm-dashboard-badge strong {
        font-size: 0.78rem;
        line-height: 1.08;
        color: #142233;
    }

    .crpm-dashboard-badge--accent {
        border-color: rgba(31, 95, 191, 0.32);
        background: #eff5ff;
    }

    .crpm-dashboard-badge--success {
        border-color: rgba(34, 126, 92, 0.28);
        background: #f0faf5;
    }

    .crpm-dashboard-section-title {
        margin: 0.04rem 0 0.2rem 0;
        font-size: 0.82rem;
        font-weight: 800;
        line-height: 1.1;
        color: #142233;
        letter-spacing: 0;
    }

    .crpm-dashboard-bar-list {
        display: grid;
        gap: 0.34rem;
        margin: 0 0 0.42rem 0;
        padding: 0.5rem 0.54rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.34);
        background: #ffffff;
        box-shadow: 0 3px 10px rgba(28, 45, 64, 0.045);
    }

    .crpm-dashboard-bar-list__title {
        font-size: 0.74rem;
        font-weight: 800;
        line-height: 1.08;
        color: #34465b;
        letter-spacing: 0;
    }

    .crpm-dashboard-bar-row {
        display: grid;
        gap: 0.12rem;
        min-width: 0;
    }

    .crpm-dashboard-bar-row__head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.34rem;
        min-width: 0;
    }

    .crpm-dashboard-bar-row__label {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.72rem;
        line-height: 1.12;
        color: #334155;
    }

    .crpm-dashboard-bar-row__value {
        flex: 0 0 auto;
        font-size: 0.72rem;
        font-weight: 800;
        line-height: 1.12;
        color: #16283d;
    }

    .crpm-dashboard-bar-row__track {
        position: relative;
        height: 0.46rem;
        overflow: hidden;
        border-radius: 999px;
        background: #e7edf4;
    }

    .crpm-dashboard-bar-row__fill {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: #2f6fbe;
    }

    .crpm-dashboard-bar-row--success .crpm-dashboard-bar-row__fill {
        background: #2d8a62;
    }

    .crpm-dashboard-bar-row--watch .crpm-dashboard-bar-row__fill,
    .crpm-dashboard-bar-row--high .crpm-dashboard-bar-row__fill {
        background: #b9732f;
    }

    .crpm-dashboard-bar-row--accent .crpm-dashboard-bar-row__fill,
    .crpm-dashboard-bar-row--medium .crpm-dashboard-bar-row__fill {
        background: #4f7fc7;
    }

    .crpm-dashboard-card-stack {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.38rem;
        margin: 0 0 0.42rem 0;
    }

    .crpm-dashboard-card-stack .crpm-bi-card {
        border-radius: 8px;
        padding: 0.54rem 0.58rem;
        box-shadow: 0 3px 10px rgba(28, 45, 64, 0.04);
        background: #ffffff;
    }

    .crpm-dashboard-card-stack .crpm-bi-card__header {
        margin: 0 0 0.24rem 0;
        padding: 0;
        border: 0;
        background: transparent;
    }

    .crpm-dashboard-card-stack .crpm-bi-card__eyebrow,
    .crpm-dashboard-card-stack .crpm-bi-card__body {
        font-size: 0.72rem;
        line-height: 1.18;
    }

    .crpm-dashboard-card-stack .crpm-bi-card__title,
    .crpm-dashboard-card-stack .crpm-bi-card__value {
        font-size: 0.86rem;
        line-height: 1.12;
    }

    .crpm-filter-parent-label {
        margin: 0.12rem 0 0.28rem 0;
        font-size: 0.72rem;
        font-weight: 800;
        line-height: 1.1;
        color: #34465b;
    }

    .crpm-filter-composer {
        display: grid;
        gap: 0.12rem;
        margin: 0.16rem 0 0.22rem 0;
        padding: 0.34rem 0.44rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.22);
        background: rgba(248, 250, 252, 0.78);
        box-shadow: none;
    }

    .crpm-filter-composer__title {
        font-size: 0.72rem;
        font-weight: 800;
        line-height: 1.12;
        color: #142233;
    }

    .crpm-filter-composer__body {
        font-size: 0.74rem;
        line-height: 1.18;
        color: #59687a;
    }

    .crpm-active-filter-summary {
        display: grid;
        gap: 0.18rem;
        margin: 0.22rem 0 0.24rem 0;
        padding: 0.28rem 0.34rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.24);
        background: rgba(248, 250, 252, 0.74);
    }

    .crpm-active-filter-summary__title {
        font-size: 0.74rem;
        font-weight: 800;
        line-height: 1.14;
        color: #34465b;
        text-transform: uppercase;
    }

    .crpm-active-filter-summary__chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.14rem;
    }

    .crpm-active-filter-summary__chip {
        display: inline-grid;
        gap: 0.02rem;
        max-width: 100%;
        padding: 0.18rem 0.26rem;
        border-radius: 7px;
        border: 1px solid rgba(151, 166, 184, 0.32);
        background: #ffffff;
        color: #26384d;
    }

    .crpm-active-filter-summary__chip span {
        font-size: 0.72rem;
        line-height: 1.12;
        color: #667789;
    }

    .crpm-active-filter-summary__chip strong {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.72rem;
        line-height: 1.08;
        color: #142233;
    }

    .crpm-overview-command-center,
    .crpm-conformance-cockpit-marker {
        margin: 0;
        padding: 0;
        height: 0;
    }

    .crpm-overview-map-frame {
        margin: 0 0 0.42rem 0;
        padding: 0.46rem;
        height: clamp(280px, 38vh, 420px);
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.34);
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(28, 45, 64, 0.05);
        overflow: auto;
    }

    .crpm-overview-map-frame .crpm-workflow-board {
        margin: 0;
        min-height: 280px;
        border-radius: 6px;
        box-shadow: none;
    }

    .crpm-overview-map-frame .crpm-workflow-board svg {
        min-height: 280px;
    }

    .crpm-dashboard-map-toolbar {
        border-radius: 8px !important;
        border-color: rgba(157, 173, 190, 0.34) !important;
        background: #ffffff !important;
        box-shadow: 0 2px 8px rgba(28, 45, 64, 0.035) !important;
    }

    .crpm-conformance-kpi-strip--cockpit {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: 0 0 0.34rem 0;
    }

    .crpm-conformance-kpi-strip--cockpit .crpm-bi-card {
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 3px 10px rgba(28, 45, 64, 0.04);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.45rem !important;
        margin-top: 0.25rem !important;
        margin-bottom: 0.55rem !important;
        padding: 0.3rem !important;
        background: rgba(252, 251, 253, 0.92) !important;
        border: 1px solid rgba(71, 88, 79, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: var(--crpm-shadow-soft) !important;
        width: fit-content !important;
        max-width: 100% !important;
        flex-wrap: wrap !important;
    }

    .stTabs [data-baseweb="tab-list"] button {
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.55rem 0.95rem !important;
        border-radius: 15px !important;
        background-color: transparent !important;
        color: var(--crpm-text-soft) !important;
        border: 1px solid transparent !important;
        transition: transform 0.16s ease, background-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease !important;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #557c93 0%, #6d87b5 100%) !important;
        border-color: rgba(85, 124, 147, 0.35) !important;
        box-shadow: 0 7px 16px rgba(68, 54, 88, 0.16) !important;
    }

    .stTabs [data-baseweb="tab-list"] button:hover {
        color: var(--crpm-forest) !important;
        background-color: rgba(232, 224, 240, 0.62) !important;
        transform: translateY(-1px) !important;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"]:hover {
        color: #ffffff !important;
        background: linear-gradient(135deg, #496f86 0%, #5f79a5 100%) !important;
    }

    div[role="radiogroup"][aria-label="button group"] {
        gap: 0.32rem !important;
        padding: 0.24rem !important;
        border-radius: 16px !important;
        border: 1px solid rgba(71, 88, 79, 0.12) !important;
        background: linear-gradient(180deg, rgba(250, 249, 252, 0.98) 0%, rgba(243, 240, 248, 0.98) 100%) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85) !important;
    }

    div[role="radiogroup"][aria-label="button group"] > button {
        min-height: 2.25rem !important;
        padding: 0.34rem 0.68rem !important;
        border-radius: 12px !important;
        border: 1px solid rgba(142, 122, 168, 0.12) !important;
        background: rgba(255, 255, 255, 0.62) !important;
        color: var(--crpm-text-soft) !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.76) !important;
        transition: transform 0.16s ease, background-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease !important;
    }

    div[role="radiogroup"][aria-label="button group"] > button:hover {
        transform: translateY(-1px) !important;
        border-color: rgba(92, 121, 165, 0.18) !important;
        background: rgba(234, 239, 248, 0.92) !important;
        color: var(--crpm-forest-strong) !important;
    }

    div[role="radiogroup"][aria-label="button group"] > button[aria-checked="true"],
    div[role="radiogroup"][aria-label="button group"] > button[aria-pressed="true"],
    div[role="radiogroup"][aria-label="button group"] > button[data-selected="true"] {
        background: linear-gradient(135deg, #31586d 0%, #5f79a5 100%) !important;
        border-color: rgba(63, 83, 129, 0.32) !important;
        color: #ffffff !important;
        box-shadow: 0 9px 20px rgba(50, 41, 66, 0.14) !important;
    }

    div[role="radiogroup"][aria-label="button group"] > button[aria-checked="true"] *,
    div[role="radiogroup"][aria-label="button group"] > button[aria-pressed="true"] *,
    div[role="radiogroup"][aria-label="button group"] > button[data-selected="true"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2026 0%, #151b21 100%) !important;
        border-right: 1px solid var(--crpm-sidebar-border) !important;
        min-width: var(--crpm-sidebar-width) !important;
        max-width: var(--crpm-sidebar-width) !important;
        box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.03) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        width: var(--crpm-sidebar-width) !important;
        min-width: var(--crpm-sidebar-width) !important;
        max-width: var(--crpm-sidebar-width) !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0.4rem !important;
        padding-left: 0.68rem !important;
        padding-right: 0.68rem !important;
        color: var(--crpm-sidebar-text) !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] p,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] label,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] span {
        color: var(--crpm-sidebar-text) !important;
        font-size: 0.84rem !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        font-size: 1.18rem !important;
        color: var(--crpm-sidebar-text) !important;
        line-height: 1.2 !important;
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] span {
        color: var(--crpm-sidebar-text-soft) !important;
        font-size: 0.72rem !important;
    }

    .stButton button,
    .stDownloadButton button {
        font-weight: 600 !important;
        border-radius: 12px !important;
        padding: 0.52rem 0.95rem !important;
        white-space: nowrap !important;
        transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease !important;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 12px 18px rgba(50, 41, 66, 0.13) !important;
    }

    .stButton button[kind="primary"],
    .stDownloadButton button {
        background: linear-gradient(135deg, #24463b 0%, #4f5fa5 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(29, 45, 52, 0.18) !important;
        text-shadow: 0 1px 1px rgba(0, 0, 0, 0.22) !important;
        box-shadow: 0 10px 22px rgba(42, 46, 86, 0.16) !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em !important;
    }

    .stButton button[kind="primary"] *,
    .stButton button[kind="primary"] p,
    .stButton button[kind="primary"] span,
    .stDownloadButton button *,
    .stDownloadButton button p,
    .stDownloadButton button span,
    [data-testid="stBaseButton-primary"] *,
    [data-testid="stBaseButton-primary"] p,
    [data-testid="stBaseButton-primary"] span {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
    }

    .stButton button[kind="primary"]:hover,
    .stDownloadButton button:hover {
        background: linear-gradient(135deg, #1f3d34 0%, #465496 100%) !important;
        filter: saturate(1.04) !important;
    }

    .stButton button[kind="primary"]:focus,
    .stButton button[kind="primary"]:focus-visible,
    .stDownloadButton button:focus,
    .stDownloadButton button:focus-visible {
        outline: 3px solid rgba(71, 110, 198, 0.28) !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 4px rgba(96, 127, 205, 0.18), 0 12px 24px rgba(42, 46, 86, 0.18) !important;
    }

    .stButton button[kind="secondary"],
    [data-testid="stBaseButton-secondary"] {
        background: rgba(255, 255, 255, 0.76) !important;
        color: var(--crpm-forest-strong) !important;
        border: 1px solid rgba(101, 120, 143, 0.3) !important;
        width: auto !important;
        min-width: 4.8rem !important;
        min-height: 2.05rem !important;
        padding: 0.24rem 0.5rem !important;
        font-size: 0.72rem !important;
        line-height: 1 !important;
        justify-content: center !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    .stButton button[kind="secondary"] *,
    [data-testid="stBaseButton-secondary"] * {
        color: var(--crpm-forest-strong) !important;
        font-size: inherit !important;
        line-height: 1.05 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }

    .stButton button[kind="tertiary"],
    [data-testid="stBaseButton-tertiary"] {
        width: 100% !important;
        min-height: 2.28rem !important;
        padding: 0.38rem 0.62rem !important;
        border-radius: 8px !important;
        border: 1px solid rgba(101, 120, 143, 0.28) !important;
        background: rgba(255, 255, 255, 0.78) !important;
        color: #26384d !important;
        box-shadow: 0 1px 5px rgba(28, 45, 64, 0.03) !important;
        justify-content: center !important;
    }

    .stButton button[kind="tertiary"] *,
    [data-testid="stBaseButton-tertiary"] * {
        color: #26384d !important;
        font-size: 0.76rem !important;
        line-height: 1.08 !important;
        white-space: nowrap !important;
    }

    .stAlert {
        border-radius: 14px !important;
        border: 1px solid rgba(71, 88, 79, 0.12) !important;
        padding: 0.8rem 0.95rem !important;
        box-shadow: var(--crpm-shadow-soft) !important;
        overflow: hidden !important;
    }

    .stAlert [data-testid="stMarkdownContainer"],
    .stAlert [data-testid="stMarkdownContainer"] p,
    .stAlert [data-testid="stMarkdownContainer"] span,
    .stAlert [data-testid="stMarkdownContainer"] div,
    .stAlert [data-testid="stMarkdownContainer"] li {
        color: inherit !important;
        opacity: 1 !important;
    }

    .stSuccess {
        background: var(--crpm-success-bg) !important;
        border-color: rgba(85, 120, 99, 0.18) !important;
        color: var(--crpm-forest-strong) !important;
    }

    .stInfo {
        background: rgba(238, 242, 248, 0.56) !important;
        border-color: rgba(113, 128, 168, 0.14) !important;
        color: #30435f !important;
        box-shadow: none !important;
    }

    .stSuccess div, .stSuccess p, .stSuccess span, .stSuccess label, .stSuccess li,
    .stInfo div, .stInfo p, .stInfo span, .stInfo label, .stInfo li,
    .stWarning div, .stWarning p, .stWarning span, .stWarning label, .stWarning li,
    .stError div, .stError p, .stError span, .stError label, .stError li {
        color: inherit !important;
        opacity: 1 !important;
    }

    .stWarning {
        background: var(--crpm-warning-bg) !important;
        border-color: rgba(143, 118, 83, 0.18) !important;
        color: #5c4931 !important;
    }

    .stWarning [data-testid="stMarkdownContainer"],
    .stWarning [data-testid="stMarkdownContainer"] p,
    .stWarning [data-testid="stMarkdownContainer"] span,
    .stWarning [data-testid="stMarkdownContainer"] div,
    .stWarning [data-testid="stMarkdownContainer"] li {
        color: #4b3825 !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] .stWarning {
        background: rgba(247, 242, 233, 0.98) !important;
        border-color: rgba(143, 118, 83, 0.28) !important;
        color: #3f2f17 !important;
    }

    [data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] div,
    [data-testid="stSidebar"] .stWarning [data-testid="stMarkdownContainer"] li {
        color: #3f2f17 !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] .stInfo {
        background: rgba(238, 242, 248, 0.94) !important;
        border-color: rgba(113, 128, 168, 0.24) !important;
        color: #2b3c56 !important;
    }

    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] div,
    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] li {
        color: #2b3c56 !important;
        opacity: 1 !important;
    }

    .stError {
        background: var(--crpm-error-bg) !important;
        border-color: rgba(139, 92, 102, 0.18) !important;
        color: #633943 !important;
    }

    .crpm-workflow-board {
        background: rgba(252, 251, 253, 0.78);
        border: 1px solid rgba(71, 88, 79, 0.12);
        border-radius: 22px;
        box-shadow: var(--crpm-shadow-soft);
        margin: 0.04rem 0 0.24rem 0;
        overflow: hidden;
        padding: 0.02rem;
    }

    .crpm-workflow-board svg {
        display: block;
        height: auto;
        width: 100%;
    }

    .crpm-workflow-board--horizontal {
        overflow-x: auto;
        overflow-y: visible;
        padding: 0;
        width: 100%;
        max-width: 100%;
        margin-left: 0;
        margin-right: 0;
    }

    .crpm-workflow-board--horizontal svg {
        display: block;
        min-width: 100%;
        width: auto;
    }

    .crpm-workflow-board--horizontal[data-fit-mode="shelf"] {
        overflow-x: visible;
    }

    .crpm-workflow-board--horizontal[data-fit-mode="shelf"] svg {
        min-width: 0;
        width: 100%;
        max-width: 100%;
    }

    .crpm-conformance-board-shelf {
        margin: 0.12rem 0 0.28rem 0;
        padding: 0.22rem 0.34rem 0.16rem 0.34rem;
        border-radius: 20px;
        border: 1px solid rgba(71, 88, 79, 0.11);
        background:
            radial-gradient(circle at top right, rgba(95, 121, 165, 0.08), transparent 28%),
            linear-gradient(180deg, rgba(252, 251, 253, 0.98), rgba(246, 243, 249, 0.98));
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-conformance-board-shelf__eyebrow {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--crpm-lavender);
        margin-bottom: 0.12rem;
    }

    .crpm-conformance-board-shelf__title {
        font-size: 0.98rem;
        font-weight: 800;
        line-height: 1.08;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.12rem;
    }

    .crpm-conformance-board-shelf__body {
        font-size: 0.76rem;
        line-height: 1.28;
        color: var(--crpm-text-soft);
        margin-bottom: 0.06rem;
        max-width: 58rem;
    }

    .crpm-conformance-board-shelf__meta,
    .crpm-conformance-board-shelf__summary {
        margin: 0 0 0.06rem 0;
        padding: 0.22rem 0.38rem;
        border-radius: 12px;
        border: 1px solid rgba(113, 128, 168, 0.12);
        background: rgba(251, 250, 253, 0.92);
        font-size: 0.74rem;
        line-height: 1.18;
        color: var(--crpm-text-soft);
    }

    .crpm-conformance-board-shelf .crpm-workflow-board {
        margin: 0;
        background: rgba(255, 255, 255, 0.84);
    }

    @media (max-width: 1180px) {
        .crpm-workflow-board--horizontal {
            width: 100%;
            margin-left: 0;
            margin-right: 0;
        }
    }

    .streamlit-expanderHeader,
    [data-testid="stFileUploader"] {
        background: rgba(252, 251, 253, 0.88) !important;
        border: 1px solid rgba(71, 88, 79, 0.12) !important;
        border-radius: 14px !important;
        box-shadow: var(--crpm-shadow-soft) !important;
    }

    .streamlit-expanderHeader:hover,
    [data-testid="stFileUploader"]:hover {
        background: rgba(244, 239, 248, 0.98) !important;
        border-color: rgba(142, 122, 168, 0.24) !important;
    }

    [data-testid="stSidebar"] .streamlit-expanderHeader,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background: linear-gradient(180deg, rgba(19, 26, 32, 0.96) 0%, rgba(16, 22, 27, 0.96) 100%) !important;
        border: 1px solid rgba(154, 171, 196, 0.18) !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .streamlit-expanderHeader:hover,
    [data-testid="stSidebar"] [data-testid="stFileUploader"]:hover {
        background: linear-gradient(180deg, rgba(26, 34, 42, 0.98) 0%, rgba(18, 25, 31, 0.98) 100%) !important;
        border-color: rgba(111, 136, 198, 0.32) !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(252, 251, 253, 0.98) !important;
        border: 1px solid rgba(71, 88, 79, 0.16) !important;
        border-radius: 12px !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
        color: #2c3742 !important;
        font-size: 0.68rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] p:first-child,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] div:first-child,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] strong {
        color: #24313d !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] p:not(:first-child) {
        color: #5d6874 !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background: #ffffff !important;
        color: #3d4651 !important;
        border: 1px solid rgba(71, 88, 79, 0.18) !important;
        box-shadow: 0 2px 8px rgba(50, 41, 66, 0.08) !important;
        font-size: 0.76rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
        background: #f6f7fb !important;
        color: #273440 !important;
        border-color: rgba(95, 121, 165, 0.28) !important;
        box-shadow: 0 6px 14px rgba(50, 41, 66, 0.12) !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input {
        background-color: rgba(255, 255, 255, 0.92) !important;
        color: var(--crpm-text) !important;
        border: 1px solid rgba(142, 122, 168, 0.18) !important;
        border-radius: 10px !important;
    }

    [data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.92) !important;
        color: var(--crpm-text) !important;
        border: 1px solid rgba(142, 122, 168, 0.18) !important;
        border-radius: 10px !important;
    }

    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stTextArea textarea,
    [data-testid="stSidebar"] .stNumberInput input,
    [data-testid="stSidebar"] .stDateInput input {
        background: rgba(12, 17, 22, 0.98) !important;
        color: var(--crpm-sidebar-text) !important;
        border: 1px solid rgba(154, 171, 196, 0.2) !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="base-input"] > div {
        background: rgba(12, 17, 22, 0.98) !important;
        color: var(--crpm-sidebar-text) !important;
        border: 1px solid rgba(154, 171, 196, 0.2) !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] svg,
    [data-testid="stSidebar"] [data-baseweb="base-input"] svg {
        fill: var(--crpm-sidebar-text-soft) !important;
    }

    [data-baseweb="popover"] {
        color: var(--crpm-text) !important;
    }

    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: var(--crpm-text) !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stNumberInput label,
    [data-testid="stSidebar"] .stTextArea label,
    [data-testid="stSidebar"] .stDateInput label {
        color: var(--crpm-sidebar-text-soft) !important;
        font-size: 0.78rem !important;
    }

    .stCheckbox label, .stRadio label {
        color: var(--crpm-text) !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stRadio label {
        color: var(--crpm-sidebar-text) !important;
    }

    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    [data-testid="stWidgetLabel"] label {
        color: var(--crpm-text) !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] span,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label {
        color: var(--crpm-sidebar-text-soft) !important;
        font-size: 0.78rem !important;
    }

    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label span,
    [data-testid="stRadio"] label p,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label span,
    [data-testid="stCheckbox"] label p,
    [data-testid="stSlider"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSlider"] [data-testid="stWidgetLabel"] span {
        color: var(--crpm-text) !important;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label span,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label span,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label p,
    [data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stWidgetLabel"] span {
        color: var(--crpm-sidebar-text) !important;
        font-size: 0.78rem !important;
    }

    [data-baseweb="radio"] label,
    [data-baseweb="radio"] label span,
    [data-baseweb="checkbox"] label,
    [data-baseweb="checkbox"] label span {
        color: var(--crpm-text) !important;
        opacity: 1 !important;
    }

    [data-baseweb="radio"] input:checked + div,
    [data-baseweb="checkbox"] input:checked + div,
    [data-baseweb="radio"] input:checked ~ div,
    [data-baseweb="checkbox"] input:checked ~ div,
    [data-testid="stRadio"] label[data-checked="true"] span,
    [data-testid="stCheckbox"] label[data-checked="true"] span {
        color: var(--crpm-forest-strong) !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] span,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label[data-checked="true"] span {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: rgba(177, 84, 73, 0.96) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] * {
        color: #fff4f0 !important;
        fill: #fff4f0 !important;
        font-size: 0.76rem !important;
    }

    [data-testid="stSidebar"] .stButton button:not([kind="primary"]) {
        background: rgba(15, 21, 27, 0.96) !important;
        color: var(--crpm-sidebar-text) !important;
        border: 1px solid rgba(154, 171, 196, 0.18) !important;
        box-shadow: none !important;
        font-size: 0.76rem !important;
    }

    [data-testid="stSidebar"] .stButton button[kind="primary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #24463b 0%, #485da5 100%) !important;
        border: 1px solid rgba(130, 151, 214, 0.22) !important;
        box-shadow: 0 12px 22px rgba(10, 13, 19, 0.42) !important;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--crpm-forest), var(--crpm-lavender)) !important;
    }

    .stCaption {
        color: var(--crpm-muted) !important;
        font-size: 0.84rem !important;
        margin-bottom: 0.2rem !important;
    }

    .crpm-note {
        margin: 0.16rem 0 0.48rem 0 !important;
        padding: 0.68rem 0.82rem !important;
        border-radius: 12px !important;
        border: 1px solid rgba(71, 88, 79, 0.12) !important;
        border-left: 4px solid rgba(142, 122, 168, 0.45) !important;
        background: rgba(252, 251, 253, 0.78) !important;
        color: #21342b !important;
        font-size: 0.89rem !important;
        line-height: 1.45 !important;
        box-shadow: none !important;
    }

    .crpm-note,
    .crpm-note p,
    .crpm-note span,
    .crpm-note div,
    .crpm-legend-note,
    .crpm-legend-note p,
    .crpm-legend-note span,
    .crpm-legend-note div {
        color: #21342b !important;
    }

    .crpm-legend-note {
        margin: 0.14rem 0 0.46rem 0 !important;
        padding: 0.58rem 0.76rem !important;
        border-radius: 12px !important;
        border: 1px solid rgba(71, 88, 79, 0.12) !important;
        background: rgba(247, 244, 250, 0.82) !important;
        font-size: 0.88rem !important;
        line-height: 1.42 !important;
        box-shadow: none !important;
    }

    .crpm-selection-card,
    .crpm-detail-card,
    .crpm-mini-note,
    .crpm-model-card,
    .crpm-ranked-table,
    .crpm-mode-banner {
        color: var(--crpm-text) !important;
    }

    .crpm-mode-banner {
        margin: 0.08rem 0 0.34rem 0;
        padding: 0.6rem 0.78rem;
        border-radius: 14px;
        border: 1px solid rgba(71, 88, 79, 0.14);
        background: rgba(252, 251, 253, 0.96);
        box-shadow: 0 8px 18px rgba(50, 41, 66, 0.05);
    }

    .crpm-mode-banner--board {
        border-left: 4px solid #7a9488;
        background: linear-gradient(180deg, rgba(250, 252, 251, 0.96) 0%, rgba(248, 246, 251, 0.96) 100%);
    }

    .crpm-mode-banner--interactive {
        border-left: 4px solid #5d84c1;
        background: linear-gradient(180deg, rgba(248, 251, 255, 0.96) 0%, rgba(245, 248, 253, 0.98) 100%);
    }

    .crpm-mode-banner__title {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.18rem;
    }

    .crpm-mode-banner__body {
        font-size: 0.84rem;
        color: var(--crpm-text-soft);
        line-height: 1.42;
    }

    .crpm-selection-card {
        margin: 0.12rem 0 0.26rem 0;
        padding: 0.48rem 0.56rem;
        border-radius: 12px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.96);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-selection-card--overview {
        border-left: 4px solid #8d95a8;
    }

    .crpm-selection-card--conformant {
        border-left: 4px solid #4d8f65;
    }

    .crpm-selection-card--log-deviation {
        border-left: 4px solid #b17b34;
    }

    .crpm-selection-card--model-deviation {
        border-left: 4px solid #b56576;
    }

    .crpm-selection-card__eyebrow {
        font-size: 0.56rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-selection-card__title {
        font-size: 0.74rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        line-height: 1.18;
    }

    .crpm-selection-card__meta {
        margin-top: 0.18rem;
        font-size: 0.63rem;
        color: var(--crpm-text-soft);
        line-height: 1.22;
    }

    .crpm-detail-card {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 0.55rem;
        margin: 0.14rem 0 0.5rem 0;
        padding: 0.8rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.1);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-detail-card--node {
        border-left: 4px solid #4d8f65;
    }

    .crpm-detail-card--edge {
        border-left: 4px solid #b17b34;
    }

    .crpm-detail-card__item {
        min-width: 0;
        padding: 0.55rem 0.65rem;
        border-radius: 12px;
        background: rgba(245, 243, 248, 0.78);
        border: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-detail-card__label {
        font-size: 0.58rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-detail-card__value {
        font-size: 0.74rem;
        font-weight: 600;
        color: var(--crpm-forest-strong);
        line-height: 1.18;
        word-break: break-word;
    }

    .crpm-model-card-grid {
        display: grid;
        gap: 0.6rem;
        width: 100%;
        max-width: 100%;
        min-width: 0;
    }

    .crpm-model-card {
        box-sizing: border-box;
        position: relative;
        width: 100%;
        max-width: 100%;
        min-width: 0;
        overflow: hidden;
        padding: 0.82rem 0.9rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
        border-left: 4px solid rgba(54, 83, 72, 0.42);
    }

    .crpm-model-card__rank {
        font-size: 0.61rem;
        font-weight: 700;
        color: var(--crpm-muted);
        margin-bottom: 0.2rem;
    }

    .crpm-model-card__title {
        font-size: 0.77rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.55rem;
        line-height: 1.18;
    }

    .crpm-model-card__grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 8.5rem), 1fr));
        gap: 0.55rem;
        min-width: 0;
    }

    .crpm-model-card__grid div {
        box-sizing: border-box;
        min-width: 0;
        padding: 0.46rem 0.52rem;
        border-radius: 12px;
        background: rgba(245, 243, 248, 0.82);
        border: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-model-card__grid span {
        display: block;
        font-size: 0.58rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-model-card__grid strong {
        display: block;
        font-size: 0.67rem;
        color: var(--crpm-forest-strong);
        line-height: 1.18;
        word-break: break-word;
    }

    .crpm-mini-note {
        margin-bottom: 0.36rem;
        padding: 0.65rem 0.78rem;
        border-radius: 12px;
        border: 1px solid rgba(71, 88, 79, 0.1);
        background: rgba(252, 251, 253, 0.96);
        line-height: 1.45;
        font-size: 0.84rem;
    }

    .crpm-ranked-table {
        border: 1px solid rgba(71, 88, 79, 0.1);
        border-radius: 16px;
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
        max-width: 100%;
        min-width: 0;
        overflow: hidden;
    }

    .crpm-ranked-table__title {
        padding: 0.62rem 0.78rem 0.44rem 0.78rem;
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
    }

    .crpm-ranked-table__scroller {
        width: 100%;
        max-width: 100%;
        min-width: 0;
        max-height: 360px;
        overflow-x: hidden;
        overflow-y: auto;
        border-top: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-ranked-table table {
        width: 100%;
        min-width: 100%;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.66rem;
    }

    .crpm-ranked-table thead th {
        position: sticky;
        top: 0;
        z-index: 1;
        padding: 0.52rem 0.52rem;
        background: #f4eff8;
        color: var(--crpm-forest-strong);
        text-align: left;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        border-bottom: 1px solid rgba(71, 88, 79, 0.12);
        overflow-wrap: anywhere;
        white-space: normal;
    }

    .crpm-ranked-table th,
    .crpm-ranked-table td {
        max-width: 0;
        overflow-wrap: anywhere;
        word-break: normal;
    }

    .crpm-ranked-table tbody tr:nth-child(odd) {
        background: rgba(247, 244, 250, 0.5);
    }

    .crpm-ranked-table tbody tr:hover {
        background: rgba(232, 224, 240, 0.38);
    }

    .crpm-conformance-inspector-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(242px, 1fr));
        gap: 0.42rem;
        margin: 0.04rem 0 0.22rem 0;
    }

    .crpm-conformance-inspector-grid .crpm-bi-card {
        min-height: 82px;
        padding: 0.6rem 0.7rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-conformance-inspector-grid .crpm-bi-card__eyebrow {
        font-size: 0.7rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--crpm-muted);
        margin-bottom: 0.12rem;
    }

    .crpm-conformance-inspector-grid .crpm-bi-card__title {
        font-size: 0.66rem;
        font-weight: 700;
        line-height: 1.06;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.16rem;
    }

    .crpm-conformance-inspector-grid .crpm-bi-card__value {
        font-size: 1.36rem;
        font-weight: 800;
        line-height: 1.05;
        color: #102e41;
    }

    .crpm-conformance-inspector-grid .crpm-bi-card__body {
        display: none;
    }

    .crpm-conformance-panel {
        margin: 0.03rem 0 0.14rem 0;
        padding: 0.44rem 0.54rem;
        border-radius: 13px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-conformance-panel--muted {
        background: rgba(249, 248, 251, 0.98);
    }

    .crpm-conformance-panel__eyebrow {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--crpm-muted);
        margin-bottom: 0.16rem;
    }

    .crpm-conformance-panel__title {
        font-size: 0.78rem;
        font-weight: 800;
        line-height: 1.08;
        color: var(--crpm-forest-strong);
    }

    .crpm-conformance-panel__body {
        font-size: 0.7rem;
        line-height: 1.12;
        color: var(--crpm-text-soft);
    }

    .crpm-conformance-panel--rail {
        border-color: rgba(157, 173, 190, 0.22);
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(28, 45, 64, 0.032);
    }

    .crpm-conformance-side-title {
        margin: 0.02rem 0 0.16rem 0;
        font-size: 0.82rem;
        font-weight: 800;
        line-height: 1.05;
        color: var(--crpm-forest-strong);
        letter-spacing: 0;
    }

    .crpm-conformance-side-title--rail {
        font-size: 0.76rem;
    }

    .crpm-conformance-side-title--inspector {
        font-size: 0.76rem;
    }

    .crpm-conformance-side-subtitle {
        margin: 0.12rem 0 0.16rem 0;
        font-size: 0.7rem;
        font-weight: 800;
        line-height: 1.04;
        color: var(--crpm-forest-strong);
        letter-spacing: 0.01em;
        text-transform: uppercase;
    }

    .crpm-conformance-side-rail {
        margin: 0 0 0.06rem 0;
        padding: 0.34rem 0.42rem 0.28rem 0.42rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.26);
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(28, 45, 64, 0.032);
    }

    .crpm-conformance-side-rail--filters {
        border-left: 3px solid rgba(85, 124, 147, 0.24);
    }

    .crpm-conformance-side-rail--inspector {
        border-left: 3px solid rgba(100, 89, 148, 0.18);
    }

    .crpm-conformance-side-lead {
        font-size: 0.72rem;
        line-height: 1.22;
        color: var(--crpm-text-soft);
        margin-top: -0.02rem;
        max-width: 23rem;
    }

    .crpm-conformance-hero,
    .crpm-conformance-stage-header,
    .crpm-conformance-report-band,
    .crpm-conformance-evidence-band {
        margin: 0 0 0.12rem 0;
        padding: 0.3rem 0.46rem;
        border-radius: 8px;
        border: 1px solid rgba(157, 173, 190, 0.26);
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(28, 45, 64, 0.032);
    }

    .crpm-conformance-hero__eyebrow,
    .crpm-conformance-stage-header__eyebrow,
    .crpm-conformance-report-band__label {
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--crpm-muted);
        margin-bottom: 0.12rem;
    }

    .crpm-conformance-hero__row {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.38rem;
        flex-wrap: wrap;
    }

    .crpm-conformance-hero__title,
    .crpm-conformance-stage-header__title {
        font-size: 0.84rem;
        font-weight: 800;
        line-height: 1.08;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.04rem;
    }

    .crpm-conformance-hero__body,
    .crpm-conformance-stage-header__body,
    .crpm-conformance-report-band__body,
    .crpm-conformance-evidence-band {
        font-size: 0.66rem;
        line-height: 1.16;
        color: var(--crpm-text-soft);
    }

    .crpm-conformance-stage-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.42rem;
        min-height: 2.55rem;
    }

    .crpm-conformance-stage-header__copy {
        min-width: 0;
    }

    .crpm-conformance-stage-header__chips {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.22rem;
        min-width: 0;
    }

    .crpm-conformance-stage-header__chips span {
        display: inline-flex;
        align-items: center;
        min-height: 1.35rem;
        max-width: 10rem;
        padding: 0.18rem 0.34rem;
        border-radius: 999px;
        border: 1px solid rgba(157, 173, 190, 0.32);
        background: #f8fafc;
        color: #34465b;
        font-size: 0.62rem;
        font-weight: 700;
        line-height: 1.05;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .crpm-conformance-hero__badge {
        display: inline-grid;
        gap: 0.14rem;
        min-width: 12rem;
        padding: 0.34rem 0.48rem;
        border-radius: 13px;
        border: 1px solid rgba(103, 128, 168, 0.14);
        background: rgba(245, 248, 252, 0.96);
        color: var(--crpm-forest-strong);
    }

    .crpm-conformance-hero__badge span {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--crpm-muted);
    }

    .crpm-conformance-hero__badge strong {
        font-size: 0.8rem;
        font-weight: 800;
        line-height: 1.12;
    }

    .crpm-table__cell {
        padding: 0.44rem 0.52rem;
        color: var(--crpm-text);
        border-bottom: 1px solid rgba(71, 88, 79, 0.08);
        vertical-align: middle;
    }

    .crpm-table__cell--rank {
        width: 1%;
        white-space: nowrap;
    }

    .crpm-table__cell--num {
        text-align: right;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }

    .crpm-table__cell--label {
        max-width: 22rem;
        min-width: 11rem;
        line-height: 1.35;
        font-weight: 600;
        white-space: normal;
    }

    .crpm-table__cell--chip {
        white-space: nowrap;
    }

    .crpm-ranked-table .crpm-table__cell--label {
        max-width: none;
        min-width: 0;
    }

    .crpm-ranked-table .crpm-table__cell--chip,
    .crpm-ranked-table .crpm-table__cell--num {
        white-space: normal;
    }

    .crpm-ranked-table .crpm-table__metric-track {
        min-width: 0;
    }

    .crpm-rank-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 2rem;
        padding: 0.2rem 0.42rem;
        border-radius: 999px;
        background: rgba(238, 242, 248, 0.96);
        border: 1px solid rgba(113, 128, 168, 0.16);
        color: #30435f;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1;
    }

    .crpm-table__metric-cell {
        display: grid;
        gap: 0.18rem;
        justify-items: end;
    }

    .crpm-table__metric-value {
        position: relative;
        z-index: 1;
    }

    .crpm-table__metric-track {
        position: relative;
        width: 100%;
        min-width: 3.9rem;
        height: 0.26rem;
        border-radius: 999px;
        background: rgba(142, 122, 168, 0.12);
        overflow: hidden;
    }

    .crpm-table__metric-fill {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(54, 83, 72, 0.85), rgba(79, 95, 165, 0.85));
    }

    .crpm-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 6.2rem;
        padding: 0.24rem 0.5rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1;
        white-space: nowrap;
        border: 1px solid transparent;
    }

    .crpm-ranked-table .crpm-chip {
        width: 100%;
        max-width: 100%;
        min-width: 0;
        overflow: hidden;
        line-height: 1.12;
        text-align: center;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .crpm-chip--conformant {
        background: #e6f5ea;
        color: #205737;
        border-color: rgba(52, 122, 76, 0.16);
    }

    .crpm-chip--model-deviation {
        background: #f9e7eb;
        color: #7a3142;
        border-color: rgba(160, 87, 105, 0.18);
    }

    .crpm-chip--log-deviation {
        background: #f8edd8;
        color: #755115;
        border-color: rgba(176, 122, 61, 0.18);
    }

    .crpm-chip--mixed {
        background: #efe8fb;
        color: #5b3d88;
        border-color: rgba(111, 86, 162, 0.2);
    }

    .crpm-chip--overview,
    .crpm-chip--neutral {
        background: #eef2f8;
        color: #30435f;
        border-color: rgba(113, 128, 168, 0.18);
    }

    .crpm-chip--watch {
        background: #f8edd8;
        color: #755115;
        border-color: rgba(176, 122, 61, 0.18);
    }

    .crpm-chip--deviation-heavy {
        background: #f9e7eb;
        color: #7a3142;
        border-color: rgba(160, 87, 105, 0.18);
    }

    .crpm-chip--low,
    .crpm-chip--moderate,
    .crpm-chip--high,
    .crpm-chip--critical {
        color: #20312a;
    }

    .js-plotly-plot .legend text {
        fill: #1f2c25 !important;
    }

    .crpm-empty-state,
    .crpm-inline-empty {
        background: rgba(252, 251, 253, 0.86) !important;
        border: 1px dashed rgba(113, 128, 168, 0.22) !important;
        color: var(--crpm-muted) !important;
        border-radius: 12px !important;
        line-height: 1.45 !important;
    }

    .crpm-empty-state {
        margin: 0.3rem 0 0.54rem 0 !important;
        padding: 0.9rem 1rem !important;
        box-shadow: none !important;
    }

    .crpm-inline-empty {
        margin: 0.35rem 0 0.35rem 0 !important;
        padding: 0.6rem 0.8rem !important;
        font-size: 0.9rem !important;
    }

    .crpm-dfg-vector {
        margin: 0.12rem 0 0.56rem 0;
        padding: 0.72rem 0.82rem;
        min-height: 272px;
        border-radius: 18px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
        overflow: hidden;
    }

    .crpm-dfg-map-canvas {
        display: flex;
        align-items: flex-start;
        justify-content: center;
        min-height: 272px;
    }

    .crpm-dfg-vector svg {
        width: 100%;
        max-width: 100%;
        min-width: 0;
        height: clamp(240px, 30vh, 340px);
    }

    .stMarkdown ul, .stMarkdown ol {
        margin-left: 1.3rem !important;
        margin-bottom: 0.42rem !important;
    }

    .stMarkdown strong {
        color: var(--crpm-forest-strong) !important;
    }

    hr {
        margin: 0.36rem 0 0.56rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, rgba(54, 83, 72, 0), rgba(54, 83, 72, 0.12), rgba(142, 122, 168, 0.12), rgba(54, 83, 72, 0)) !important;
    }

    .stMarkdown code {
        background-color: rgba(232, 224, 240, 0.55) !important;
        padding: 0.18rem 0.35rem !important;
        border-radius: 6px !important;
        font-size: 0.86rem !important;
    }

    .stMarkdown pre {
        background-color: #2f3138 !important;
        border-radius: 12px !important;
    }

    .quality-badge {
        padding: 4px 12px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
        margin: 4px;
        box-shadow: var(--crpm-shadow-soft);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .crpm-section-title {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        color: var(--crpm-forest-strong) !important;
        margin-bottom: 0.55rem !important;
    }

    .crpm-section-title__icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.35rem;
        height: 2.35rem;
        border-radius: 0.85rem;
        background: linear-gradient(135deg, rgba(232, 224, 240, 1), rgba(219, 229, 223, 1));
        color: var(--crpm-forest-strong);
        font-size: 1rem;
        font-weight: 700;
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-section-title__text {
        line-height: 1.2;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 18px !important;
        border: 1px solid rgba(71, 88, 79, 0.11) !important;
        background: linear-gradient(180deg, rgba(252, 251, 253, 0.98) 0%, rgba(247, 244, 250, 0.96) 100%) !important;
        box-shadow: var(--crpm-shadow) !important;
        transition: box-shadow 0.16s ease, border-color 0.16s ease !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(142, 122, 168, 0.22) !important;
        box-shadow: 0 16px 30px rgba(50, 41, 66, 0.11) !important;
    }

    .crpm-card-wrapper {
        padding: 0.05rem 0;
        margin-bottom: 0.2rem;
    }

    .crpm-card__header {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin-bottom: 0.5rem;
    }

    .crpm-card__icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 0.9rem;
        background: linear-gradient(135deg, rgba(232, 224, 240, 1), rgba(219, 229, 223, 1));
        color: var(--crpm-forest-strong);
        font-size: 0.95rem;
        font-weight: 700;
    }

    .crpm-card__title {
        font-size: 1.08rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
    }

    .crpm-card__description {
        color: var(--crpm-text-soft);
        font-size: 0.92rem;
        margin-bottom: 0.45rem;
    }

    .crpm-card-accent {
        height: 3px;
        border-radius: 999px;
        margin-bottom: 0.8rem;
        background: linear-gradient(90deg, rgba(54, 83, 72, 0.25), rgba(142, 122, 168, 0.12));
    }

    .crpm-card-accent--info {
        background: linear-gradient(90deg, rgba(113, 128, 168, 0.35), rgba(142, 122, 168, 0.12));
    }

    .crpm-card-accent--warning {
        background: linear-gradient(90deg, rgba(143, 118, 83, 0.35), rgba(143, 118, 83, 0.1));
    }

    .crpm-card-accent--success {
        background: linear-gradient(90deg, rgba(85, 120, 99, 0.35), rgba(142, 122, 168, 0.1));
    }

    .crpm-shell-hero {
        border: 1px solid rgba(71, 88, 79, 0.12);
        border-radius: 18px;
        padding: 0.72rem 0.88rem 0.74rem 0.88rem;
        margin-bottom: 0.56rem;
        background: linear-gradient(135deg, rgba(252, 251, 253, 0.98), rgba(238, 242, 248, 0.96));
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-shell-hero--compact {
        display: grid;
        gap: 0.18rem;
    }

    .crpm-shell-hero__eyebrow {
        font-size: 0.66rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--crpm-lavender);
        margin-bottom: 0;
    }

    .crpm-shell-hero__title {
        font-size: 1.6rem;
        font-weight: 700;
        line-height: 1.2;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.45rem;
        max-width: 46rem;
    }

    .crpm-shell-hero__body {
        font-size: 0.82rem;
        line-height: 1.38;
        color: var(--crpm-text-soft);
        max-width: 56rem;
    }

    .crpm-shell-hero__meta {
        font-size: 0.72rem;
        line-height: 1.32;
        color: var(--crpm-muted);
    }

    .crpm-shell-panel {
        border: 1px solid rgba(71, 88, 79, 0.1);
        border-radius: 18px;
        padding: 0.95rem 1rem;
        background: rgba(252, 251, 253, 0.95);
        box-shadow: var(--crpm-shadow-soft);
        margin-bottom: 0.45rem;
    }

    .crpm-shell-panel--muted {
        background: rgba(247, 244, 250, 0.92);
    }

    .crpm-shell-panel__title,
    .crpm-shell-section-intro__title {
        font-size: 0.92rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.28rem;
        letter-spacing: 0.01em;
    }

    .crpm-shell-panel__body,
    .crpm-shell-section-intro__body {
        font-size: 0.92rem;
        line-height: 1.5;
        color: var(--crpm-text-soft);
    }

    .crpm-shell-section-intro {
        margin: 0.04rem 0 0.42rem 0;
        padding: 0.58rem 0.72rem;
        border-left: 4px solid rgba(85, 120, 99, 0.35);
        border-radius: 0 14px 14px 0;
        background: rgba(252, 251, 253, 0.86);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-overview-hero {
        margin: 0.1rem 0 0.62rem 0;
        padding: 0.92rem 1rem 0.92rem 1rem;
        border-radius: 24px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background:
            radial-gradient(circle at top right, rgba(79, 95, 165, 0.11), transparent 34%),
            radial-gradient(circle at bottom left, rgba(54, 83, 72, 0.11), transparent 28%),
            linear-gradient(160deg, rgba(252, 251, 253, 0.98), rgba(238, 242, 248, 0.96));
        box-shadow: var(--crpm-shadow);
    }

    .crpm-overview-hero__eyebrow {
        font-size: 0.79rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--crpm-lavender);
        margin-bottom: 0.22rem;
    }

    .crpm-overview-hero__title {
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.18;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.26rem;
        max-width: 48rem;
    }

    .crpm-overview-hero__body {
        font-size: 0.95rem;
        line-height: 1.56;
        color: var(--crpm-text-soft);
        max-width: 56rem;
    }

    .crpm-overview-hero__chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.56rem;
    }

    .crpm-overview-hero__chip {
        display: inline-flex;
        align-items: center;
        padding: 0.38rem 0.7rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        line-height: 1;
        border: 1px solid rgba(71, 88, 79, 0.1);
        background: rgba(252, 251, 253, 0.92);
        color: var(--crpm-forest-strong);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-overview-hero__chip--success {
        background: #edf4ef;
        color: #205737;
    }

    .crpm-overview-hero__chip--accent {
        background: #eef2f8;
        color: #30435f;
    }

    .crpm-bi-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.58rem;
        margin-bottom: 0.16rem;
    }

    .crpm-kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
        gap: 0.5rem;
        margin-bottom: 0.14rem;
    }

    .crpm-kpi-grid .crpm-bi-card {
        padding: 0.68rem 0.74rem;
        border-radius: 13px;
    }

    .crpm-kpi-grid .crpm-bi-card__header {
        margin: -0.14rem -0.18rem 0.32rem -0.18rem;
        padding: 0.22rem 0.28rem 0.28rem 0.28rem;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(246, 244, 249, 0.92), rgba(251, 249, 252, 0.45));
    }

    .crpm-kpi-grid .crpm-bi-card__value {
        font-size: 1.14rem;
    }

    .crpm-conformance-kpi-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.34rem;
        margin: 0.04rem 0 0.1rem 0;
    }

    .crpm-conformance-kpi-strip--rail {
        grid-template-columns: 1fr;
        margin: 0.02rem 0 0.12rem 0;
    }

    .crpm-conformance-kpi-strip .crpm-bi-card {
        min-width: 0;
        padding: 0.42rem 0.5rem;
        border-radius: 12px;
        box-shadow: 0 6px 14px rgba(50, 41, 66, 0.045);
    }

    .crpm-conformance-kpi-strip .crpm-bi-card__header {
        margin: -0.1rem -0.14rem 0.26rem -0.14rem;
        padding: 0.18rem 0.24rem 0.2rem 0.24rem;
        border-radius: 10px;
    }

    .crpm-conformance-kpi-strip .crpm-bi-card__eyebrow {
        font-size: 0.64rem;
        margin-bottom: 0.1rem;
    }

    .crpm-conformance-kpi-strip .crpm-bi-card__title {
        font-size: 0.84rem;
        margin-bottom: 0;
        line-height: 1.12;
    }

    .crpm-conformance-kpi-strip .crpm-bi-card__value {
        font-size: 0.9rem;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 0;
    }

    .crpm-conformance-kpi-strip .crpm-bi-card__body {
        display: none;
    }

    .crpm-conformance-kpi-strip--rail .crpm-bi-card {
        padding: 0.36rem 0.4rem;
        border-color: rgba(71, 88, 79, 0.08);
        box-shadow: 0 4px 10px rgba(50, 41, 66, 0.032);
    }

    .crpm-conformance-kpi-strip--rail .crpm-bi-card__eyebrow {
        font-size: 0.51rem;
    }

    .crpm-conformance-kpi-strip--rail .crpm-bi-card__title {
        font-size: 0.67rem;
        line-height: 1.04;
    }

    .crpm-conformance-kpi-strip--rail .crpm-bi-card__value {
        font-size: 0.72rem;
    }

    @media (max-width: 1100px) {
        .crpm-conformance-kpi-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 1180px) {
        .crpm-dashboard-topbar {
            align-items: stretch;
            flex-direction: column;
        }

        .crpm-dashboard-topbar__badges {
            min-width: 0;
            justify-content: flex-start;
        }

        .crpm-dashboard-badge {
            flex: 1 1 9rem;
            min-width: 0;
        }
    }

    .crpm-bi-card {
        min-width: 0;
        padding: 0.75rem 0.8rem;
        border-radius: 15px;
        border: 1px solid rgba(71, 88, 79, 0.13);
        background: linear-gradient(180deg, rgba(253, 252, 254, 0.99), rgba(248, 246, 250, 0.98));
        box-shadow: 0 10px 22px rgba(50, 41, 66, 0.065);
    }

    .crpm-bi-card__header {
        margin: -0.14rem -0.18rem 0.38rem -0.18rem;
        padding: 0.27rem 0.32rem 0.31rem 0.32rem;
        border-radius: 11px;
        background: linear-gradient(180deg, rgba(245, 242, 248, 0.9), rgba(252, 251, 253, 0.38));
        border: 1px solid rgba(142, 122, 168, 0.08);
    }

    .crpm-bi-card__eyebrow {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-bi-card__title {
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.25;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.26rem;
    }

    .crpm-bi-card__value {
        font-size: 1.08rem;
        font-weight: 700;
        line-height: 1.15;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.18rem;
        word-break: break-word;
    }

    .crpm-bi-card__body {
        font-size: 0.82rem;
        line-height: 1.4;
        color: var(--crpm-text-soft);
    }

    .crpm-bi-card--accent {
        background: linear-gradient(180deg, rgba(238, 242, 248, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-bi-card--accent .crpm-bi-card__header {
        background: linear-gradient(180deg, rgba(234, 240, 247, 0.94), rgba(250, 251, 253, 0.44));
        border-color: rgba(113, 128, 168, 0.1);
    }

    .crpm-bi-card--success {
        background: linear-gradient(180deg, rgba(237, 244, 239, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-bi-card--success .crpm-bi-card__header {
        background: linear-gradient(180deg, rgba(235, 244, 237, 0.95), rgba(251, 252, 251, 0.46));
        border-color: rgba(85, 120, 99, 0.11);
    }

    .crpm-page-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.56rem;
        margin-bottom: 0.16rem;
    }

    .crpm-page-card {
        min-width: 0;
        padding: 0.75rem 0.8rem;
        border-radius: 15px;
        border: 1px solid rgba(71, 88, 79, 0.13);
        background: linear-gradient(180deg, rgba(252, 251, 253, 0.99), rgba(247, 244, 250, 0.97));
        box-shadow: 0 10px 22px rgba(50, 41, 66, 0.065);
    }

    .crpm-page-card__order {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--crpm-lavender);
        margin: -0.14rem -0.18rem 0.32rem -0.18rem;
        padding: 0.24rem 0.31rem 0.22rem 0.31rem;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(245, 242, 248, 0.9), rgba(252, 251, 253, 0.4));
        border: 1px solid rgba(142, 122, 168, 0.08);
    }

    .crpm-page-card__title {
        font-size: 0.92rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.22rem;
    }

    .crpm-page-card__body {
        font-size: 0.82rem;
        line-height: 1.42;
        color: var(--crpm-text-soft);
        margin-bottom: 0.42rem;
    }

    .crpm-page-card__meta {
        font-size: 0.78rem;
        font-weight: 700;
        color: var(--crpm-muted);
    }

    .crpm-reading-order-band {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        flex-wrap: wrap;
        margin: 0.18rem 0 0.26rem 0;
        padding: 0.72rem 0.88rem;
        border-radius: 16px;
        border: 1px solid rgba(113, 128, 168, 0.18);
        border-left: 4px solid rgba(93, 132, 193, 0.62);
        background: linear-gradient(180deg, rgba(241, 245, 251, 0.96), rgba(249, 248, 252, 0.98));
        box-shadow: 0 8px 18px rgba(50, 41, 66, 0.055);
    }

    .crpm-reading-order-band__eyebrow {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--crpm-lavender);
    }

    .crpm-reading-order-band__title {
        font-size: 0.95rem;
        font-weight: 800;
        color: var(--crpm-forest-strong);
    }

    .crpm-reading-order-band__body {
        font-size: 0.84rem;
        line-height: 1.42;
        color: var(--crpm-text-soft);
    }

    .crpm-inline-notice {
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.11);
        padding: 0.8rem 1rem;
        margin: 0.12rem 0 0.4rem 0;
        background: rgba(252, 251, 253, 0.97);
        box-shadow: var(--crpm-shadow);
    }

    .crpm-inline-notice strong {
        color: var(--crpm-forest-strong);
        display: block;
        margin-bottom: 0.25rem;
    }

    .crpm-inline-notice ul {
        margin: 0.1rem 0 0 1.15rem !important;
    }

    .crpm-inline-notice--info {
        background: linear-gradient(180deg, rgba(238, 242, 248, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-inline-notice--warning {
        background: linear-gradient(180deg, rgba(247, 242, 233, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-inline-notice--success {
        background: linear-gradient(180deg, rgba(237, 244, 239, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-sidebar-divider {
        height: 1px;
        margin: 0.75rem 0 0.8rem 0;
        background: linear-gradient(90deg, rgba(54, 83, 72, 0), rgba(54, 83, 72, 0.16), rgba(142, 122, 168, 0.18), rgba(54, 83, 72, 0));
    }

    .crpm-sidebar-section {
        margin: 0.75rem 0 0.45rem 0;
        padding-top: 0.55rem;
        border-top: 1px solid rgba(71, 88, 79, 0.1);
        font-size: 0.87rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        letter-spacing: 0.01em;
    }

    .crpm-header-badges {
        position: static;
        top: 0.34rem;
        z-index: auto;
        display: flex;
        align-items: center;
        gap: 0.42rem;
        width: fit-content;
        margin: 0 0 0.16rem 0;
    }

    .crpm-up-badge,
    .crpm-fmup-badge,
    .crpm-author-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: rgba(252, 251, 253, 0.9);
        border: 1px solid rgba(142, 122, 168, 0.22);
        box-shadow: 0 5px 12px rgba(50, 41, 66, 0.08);
        backdrop-filter: blur(10px);
        transition: transform 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease;
        text-decoration: none !important;
    }

    .crpm-up-badge:hover,
    .crpm-fmup-badge:hover,
    .crpm-author-badge:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 24px rgba(50, 41, 66, 0.15);
        background: rgba(252, 251, 253, 0.98);
    }

    .crpm-up-badge,
    .crpm-fmup-badge {
        min-width: 3.55rem;
        height: 2.55rem;
        padding: 0.18rem 0.38rem;
    }

    .crpm-up-badge img,
    .crpm-fmup-badge img {
        max-width: none;
        max-height: 1.78rem;
        width: auto;
        height: auto;
        display: block;
    }

    .crpm-badge-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.55rem;
        height: 1.55rem;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(35, 67, 57, 0.1), rgba(73, 93, 166, 0.16));
        color: var(--crpm-forest-strong);
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        flex: 0 0 auto;
    }

    .crpm-badge-icon--up {
        background: linear-gradient(135deg, rgba(73, 93, 166, 0.14), rgba(255, 255, 255, 0.98));
    }

    .crpm-up-badge span,
    .crpm-fmup-badge span {
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
    }

    .crpm-author-badge {
        min-height: 1.8rem;
        padding: 0.28rem 0.68rem;
    }

    .crpm-author-badge span {
        color: var(--crpm-forest-strong) !important;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }

    .crpm-image {
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.1);
        padding: 0.8rem;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
    }

    .crpm-image img {
        width: 100%;
        height: auto;
        display: block;
        border-radius: 12px;
    }

    .crpm-image figcaption {
        font-size: 0.86rem;
        color: var(--crpm-muted);
        text-align: center;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 243, 249, 0.98)) !important;
        border: 1px solid rgba(71, 88, 79, 0.11) !important;
        border-radius: 16px !important;
        padding: 0.95rem 1rem !important;
        box-shadow: var(--crpm-shadow-soft) !important;
        transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-1px) !important;
        border-color: rgba(142, 122, 168, 0.22) !important;
        box-shadow: 0 12px 22px rgba(50, 41, 66, 0.1) !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--crpm-muted) !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--crpm-forest-strong) !important;
        font-weight: 700 !important;
        font-size: 1.48rem !important;
    }

    [data-testid="stDataFrame"] {
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid rgba(71, 88, 79, 0.11) !important;
        box-shadow: var(--crpm-shadow-soft) !important;
        background: rgba(255, 255, 255, 0.94) !important;
    }

    .dataframe thead tr {
        background: rgba(232, 224, 240, 0.38) !important;
    }

    .dataframe th {
        border-bottom: 1px solid rgba(71, 88, 79, 0.12) !important;
        color: var(--crpm-forest-strong) !important;
        background: rgba(247, 244, 250, 0.96) !important;
    }

    .dataframe th span,
    .dataframe th p,
    .dataframe td span,
    .dataframe td p {
        color: var(--crpm-text) !important;
    }

    .dataframe td {
        border-bottom: 1px solid rgba(71, 88, 79, 0.08) !important;
    }

    .dataframe tbody tr:hover {
        background: rgba(232, 224, 240, 0.16) !important;
    }

    .crpm-footer {
        margin-top: 1.8rem;
        padding-top: 0.9rem;
        padding-bottom: 3.8rem;
        border-top: 1px solid rgba(71, 88, 79, 0.12);
    }

    .crpm-footer__row {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        flex-wrap: wrap;
        min-height: 2.4rem;
        padding: 0.42rem 0.6rem;
        border-radius: 12px;
        background: rgba(252, 251, 253, 0.92);
        border: 1px solid rgba(71, 88, 79, 0.1);
    }

    .crpm-footer__logo {
        height: 36px;
        width: auto;
        opacity: 0.98;
    }

    .crpm-footer__logo-link {
        display: inline-flex;
        align-items: center;
    }

    .crpm-footer__logo-fallback {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 3.4rem;
        height: 2rem;
        padding: 0 0.55rem;
        border-radius: 999px;
        background: rgba(232, 224, 240, 0.86);
        border: 1px solid rgba(142, 122, 168, 0.24);
        color: var(--crpm-forest-strong);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .crpm-footer__text {
        font-size: 0.9rem;
        color: var(--crpm-text-soft);
    }

    .crpm-legal-bar {
        position: relative;
        z-index: 10;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.5rem;
        min-height: 1.5rem;
        padding: 0.24rem 0.75rem;
        margin: 0.42rem 0 0 0;
        background: rgba(30, 45, 54, 0.9);
        color: rgba(250, 247, 252, 0.94);
        border-top: 1px solid rgba(232, 224, 240, 0.18);
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(34, 29, 43, 0.08);
        backdrop-filter: blur(10px);
        font-size: 0.7rem;
        text-align: center;
    }

    .crpm-legal-bar,
    .crpm-legal-bar div,
    .crpm-legal-bar p,
    .crpm-legal-bar span,
    .crpm-legal-bar a {
        color: rgba(250, 247, 252, 0.94) !important;
    }

    .crpm-legal-bar strong {
        color: #ffffff !important;
        font-weight: 700;
    }

    a:focus-visible,
    button:focus-visible,
    input:focus-visible,
    select:focus-visible,
    textarea:focus-visible,
    [role="button"]:focus-visible,
    [tabindex]:focus-visible {
        outline: 3px solid #f0b429 !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 2px rgba(16, 46, 65, 0.22) !important;
    }

    button,
    [role="button"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primary"] {
        min-height: 2.5rem;
    }

    @media (max-width: 1100px) {
        .crpm-section-title {
            font-size: 1.42rem !important;
        }
    }

    @media (max-width: 768px) {
        .block-container {
            max-width: 100% !important;
            padding-left: 0.95rem !important;
            padding-right: 0.95rem !important;
            padding-bottom: 7.2rem !important;
        }
        [data-testid="stSidebar"] {
            min-width: auto !important;
            max-width: none !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: auto !important;
            min-width: auto !important;
            max-width: none !important;
        }
        .crpm-header-badges {
            display: flex !important;
            flex-wrap: wrap !important;
            justify-content: center !important;
            gap: 0.38rem !important;
            position: static !important;
            margin: 0.4rem auto 0.2rem auto !important;
            max-width: calc(100vw - 1rem) !important;
        }
        .crpm-header-badges img {
            height: 34px !important;
            width: auto !important;
            max-width: 42vw !important;
        }
        .crpm-author-badge {
            min-height: 34px !important;
            padding: 0.35rem 0.55rem !important;
            font-size: 0.72rem !important;
        }
        .crpm-legal-bar {
            min-height: 1.8rem;
            padding: 0.34rem 0.7rem;
            font-size: 0.72rem;
        }
    }
    </style>
    """


def apply_custom_styling():
    """Apply custom CSS styling to the Streamlit app."""
    import streamlit as st

    st.markdown(get_custom_css(), unsafe_allow_html=True)


__all__ = ["get_custom_css", "apply_custom_styling"]
