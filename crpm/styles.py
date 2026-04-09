"""Custom CSS styling for CRPM Process Mining Workbench."""


def get_custom_css() -> str:
    """Generate custom CSS for the Streamlit application."""
    return """
    <style>
    :root {
        --crpm-bg: #f5f3f8;
        --crpm-bg-soft: #efecf4;
        --crpm-sidebar: #f2eef6;
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
    }

    [data-testid="stAppViewContainer"],
    .stAppViewContainer,
    .main {
        background: linear-gradient(180deg, var(--crpm-bg-soft) 0%, var(--crpm-bg) 42%, #f8f6fb 100%) !important;
    }

    .stApp header {
        background: rgba(245, 243, 248, 0.92) !important;
        color: var(--crpm-text) !important;
        border-bottom: 1px solid rgba(71, 88, 79, 0.12) !important;
        padding: 0.55rem 1.15rem !important;
        box-shadow: 0 8px 24px rgba(50, 41, 66, 0.07) !important;
        backdrop-filter: blur(14px) !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 100 !important;
    }

    .stApp header [data-testid="stToolbar"] {
        color: var(--crpm-text) !important;
    }

    .main .block-container {
        padding-top: 1rem !important;
    }

    .block-container {
        max-width: min(1460px, calc(100vw - 18.2rem)) !important;
        margin: 0 auto !important;
        padding-top: 1rem !important;
        padding-bottom: 8.2rem !important;
        padding-left: 1.6rem !important;
        padding-right: 1.6rem !important;
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
        letter-spacing: -0.03em;
    }

    h1 {
        font-size: 1.92rem !important;
        margin-bottom: 0.85rem !important;
    }

    h2 {
        font-size: 1.45rem !important;
        margin-top: 1rem !important;
        margin-bottom: 0.65rem !important;
    }

    h3 {
        font-size: 1.18rem !important;
        margin-top: 0.9rem !important;
        margin-bottom: 0.45rem !important;
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

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--crpm-sidebar) 0%, #f6f2f8 100%) !important;
        border-right: 1px solid rgba(71, 88, 79, 0.14) !important;
        min-width: 17rem !important;
        max-width: 17rem !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        width: 17rem !important;
        min-width: 17rem !important;
        max-width: 17rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0.4rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        color: var(--crpm-text) !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] p,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] label,
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] span {
        color: var(--crpm-text) !important;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.35rem !important;
        color: var(--crpm-forest-strong) !important;
        line-height: 1.2 !important;
    }

    .stButton button,
    .stDownloadButton button {
        font-weight: 600 !important;
        border-radius: 12px !important;
        padding: 0.52rem 0.95rem !important;
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

    .stButton button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.76) !important;
        color: var(--crpm-forest-strong) !important;
        border: 1px solid rgba(142, 122, 168, 0.22) !important;
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
        border-radius: 24px;
        box-shadow: var(--crpm-shadow-soft);
        margin: 0.35rem 0 1rem 0;
        overflow: hidden;
        padding: 0.45rem;
    }

    .crpm-workflow-board svg {
        display: block;
        height: auto;
        width: 100%;
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

    [data-baseweb="popover"] {
        color: var(--crpm-text) !important;
    }

    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: var(--crpm-text) !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }

    .stCheckbox label, .stRadio label {
        color: var(--crpm-text) !important;
        font-weight: 600 !important;
    }

    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    [data-testid="stWidgetLabel"] label {
        color: var(--crpm-text) !important;
        opacity: 1 !important;
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

    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--crpm-forest), var(--crpm-lavender)) !important;
    }

    .stCaption {
        color: var(--crpm-muted) !important;
        font-size: 0.84rem !important;
    }

    .crpm-note {
        margin: 0.25rem 0 0.75rem 0 !important;
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
        margin: 0.2rem 0 0.7rem 0 !important;
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
        margin: 0.2rem 0 0.7rem 0;
        padding: 0.7rem 0.86rem;
        border-radius: 14px;
        border: 1px solid rgba(71, 88, 79, 0.14);
        background: rgba(252, 251, 253, 0.96);
        box-shadow: var(--crpm-shadow-soft);
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
        margin: 0.35rem 0 0.8rem 0;
        padding: 0.9rem 1rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.96);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-selection-card__eyebrow {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-selection-card__title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        line-height: 1.25;
    }

    .crpm-selection-card__meta {
        margin-top: 0.35rem;
        font-size: 0.85rem;
        color: var(--crpm-text-soft);
        line-height: 1.42;
    }

    .crpm-detail-card {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem;
        margin: 0.25rem 0 0.8rem 0;
        padding: 0.8rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.1);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-detail-card__item {
        min-width: 0;
        padding: 0.55rem 0.65rem;
        border-radius: 12px;
        background: rgba(245, 243, 248, 0.78);
        border: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-detail-card__label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-detail-card__value {
        font-size: 0.92rem;
        font-weight: 600;
        color: var(--crpm-forest-strong);
        line-height: 1.3;
        word-break: break-word;
    }

    .crpm-model-card-grid {
        display: grid;
        gap: 0.7rem;
    }

    .crpm-model-card {
        position: relative;
        padding: 0.9rem 0.95rem;
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.12);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-model-card__rank {
        font-size: 0.76rem;
        font-weight: 700;
        color: var(--crpm-muted);
        margin-bottom: 0.2rem;
    }

    .crpm-model-card__title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.65rem;
        line-height: 1.25;
    }

    .crpm-model-card__grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem;
    }

    .crpm-model-card__grid div {
        min-width: 0;
        padding: 0.5rem 0.55rem;
        border-radius: 12px;
        background: rgba(245, 243, 248, 0.82);
        border: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-model-card__grid span {
        display: block;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--crpm-muted);
        margin-bottom: 0.18rem;
    }

    .crpm-model-card__grid strong {
        display: block;
        font-size: 0.9rem;
        color: var(--crpm-forest-strong);
        line-height: 1.3;
        word-break: break-word;
    }

    .crpm-mini-note {
        margin-bottom: 0.55rem;
        padding: 0.7rem 0.8rem;
        border-radius: 12px;
        border: 1px solid rgba(71, 88, 79, 0.1);
        background: rgba(252, 251, 253, 0.96);
        line-height: 1.45;
        font-size: 0.88rem;
    }

    .crpm-ranked-table {
        border: 1px solid rgba(71, 88, 79, 0.1);
        border-radius: 16px;
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
        overflow: hidden;
    }

    .crpm-ranked-table__title {
        padding: 0.75rem 0.85rem 0.55rem 0.85rem;
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
    }

    .crpm-ranked-table__scroller {
        max-height: 336px;
        overflow: auto;
        border-top: 1px solid rgba(71, 88, 79, 0.08);
    }

    .crpm-ranked-table table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.82rem;
    }

    .crpm-ranked-table thead th {
        position: sticky;
        top: 0;
        z-index: 1;
        padding: 0.56rem 0.55rem;
        background: #f4eff8;
        color: var(--crpm-forest-strong);
        text-align: left;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        border-bottom: 1px solid rgba(71, 88, 79, 0.12);
        white-space: nowrap;
    }

    .crpm-ranked-table tbody tr:nth-child(odd) {
        background: rgba(247, 244, 250, 0.5);
    }

    .crpm-ranked-table tbody tr:hover {
        background: rgba(232, 224, 240, 0.38);
    }

    .crpm-table__cell {
        padding: 0.48rem 0.55rem;
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
        max-width: 0;
        min-width: 0;
        line-height: 1.35;
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
        min-width: 6.7rem;
        padding: 0.28rem 0.58rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 700;
        line-height: 1;
        white-space: nowrap;
        border: 1px solid transparent;
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
        margin: 0.5rem 0 0.85rem 0 !important;
        padding: 0.9rem 1rem !important;
        box-shadow: none !important;
    }

    .crpm-inline-empty {
        margin: 0.35rem 0 0.35rem 0 !important;
        padding: 0.6rem 0.8rem !important;
        font-size: 0.9rem !important;
    }

    .stMarkdown ul, .stMarkdown ol {
        margin-left: 1.3rem !important;
        margin-bottom: 0.6rem !important;
    }

    .stMarkdown strong {
        color: var(--crpm-forest-strong) !important;
    }

    hr {
        margin: 0.55rem 0 0.8rem 0 !important;
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
        border-radius: 22px;
        padding: 1.1rem 1.25rem 1.2rem 1.25rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, rgba(252, 251, 253, 0.98), rgba(238, 242, 248, 0.96));
        box-shadow: var(--crpm-shadow);
    }

    .crpm-shell-hero__eyebrow {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--crpm-lavender);
        margin-bottom: 0.4rem;
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
        font-size: 0.98rem;
        line-height: 1.55;
        color: var(--crpm-text-soft);
        max-width: 52rem;
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
        margin: 0.1rem 0 0.9rem 0;
        padding: 0.9rem 1rem;
        border-left: 4px solid rgba(85, 120, 99, 0.35);
        border-radius: 0 14px 14px 0;
        background: rgba(252, 251, 253, 0.86);
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-overview-hero {
        margin: 0.15rem 0 0.95rem 0;
        padding: 1.15rem 1.2rem 1.1rem 1.2rem;
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
        margin-bottom: 0.35rem;
    }

    .crpm-overview-hero__title {
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.18;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.42rem;
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
        margin-top: 0.8rem;
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
        gap: 0.75rem;
        margin-bottom: 0.85rem;
    }

    .crpm-bi-card {
        min-width: 0;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        border: 1px solid rgba(71, 88, 79, 0.11);
        background: rgba(252, 251, 253, 0.98);
        box-shadow: var(--crpm-shadow-soft);
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
        font-size: 0.98rem;
        font-weight: 700;
        line-height: 1.25;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.38rem;
    }

    .crpm-bi-card__value {
        font-size: 1.18rem;
        font-weight: 700;
        line-height: 1.15;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.28rem;
        word-break: break-word;
    }

    .crpm-bi-card__body {
        font-size: 0.87rem;
        line-height: 1.45;
        color: var(--crpm-text-soft);
    }

    .crpm-bi-card--accent {
        background: linear-gradient(180deg, rgba(238, 242, 248, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-bi-card--success {
        background: linear-gradient(180deg, rgba(237, 244, 239, 0.98), rgba(252, 251, 253, 0.98));
    }

    .crpm-page-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.7rem;
        margin-bottom: 0.7rem;
    }

    .crpm-page-card {
        min-width: 0;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        border: 1px solid rgba(71, 88, 79, 0.11);
        background: linear-gradient(180deg, rgba(252, 251, 253, 0.98), rgba(247, 244, 250, 0.96));
        box-shadow: var(--crpm-shadow-soft);
    }

    .crpm-page-card__order {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--crpm-lavender);
        margin-bottom: 0.22rem;
    }

    .crpm-page-card__title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
        margin-bottom: 0.32rem;
    }

    .crpm-page-card__body {
        font-size: 0.87rem;
        line-height: 1.48;
        color: var(--crpm-text-soft);
        margin-bottom: 0.55rem;
    }

    .crpm-page-card__meta {
        font-size: 0.78rem;
        font-weight: 700;
        color: var(--crpm-muted);
    }

    .crpm-inline-notice {
        border-radius: 16px;
        border: 1px solid rgba(71, 88, 79, 0.11);
        padding: 0.8rem 1rem;
        margin: 0.18rem 0 0.65rem 0;
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
        position: fixed;
        top: 0.52rem;
        left: calc(17rem + 1.05rem);
        z-index: 108;
        display: flex;
        align-items: center;
        gap: 0.62rem;
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
        box-shadow: 0 10px 20px rgba(50, 41, 66, 0.12);
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
        width: 3.15rem;
        height: 3.15rem;
        padding: 0.25rem;
    }

    .crpm-up-badge img,
    .crpm-fmup-badge img {
        max-width: 2rem;
        max-height: 2rem;
        width: auto;
        height: auto;
        display: block;
    }

    .crpm-up-badge span,
    .crpm-fmup-badge span {
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--crpm-forest-strong);
    }

    .crpm-author-badge {
        min-height: 2rem;
        padding: 0.38rem 0.9rem;
    }

    .crpm-author-badge span {
        color: var(--crpm-forest-strong) !important;
        font-size: 0.76rem;
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
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 140;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.5rem;
        min-height: 2rem;
        padding: 0.38rem 1rem;
        background: rgba(39, 66, 57, 0.94);
        color: rgba(250, 247, 252, 0.94);
        border-top: 1px solid rgba(232, 224, 240, 0.18);
        box-shadow: 0 -8px 18px rgba(34, 29, 43, 0.16);
        backdrop-filter: blur(10px);
        font-size: 0.79rem;
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
            display: none !important;
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
