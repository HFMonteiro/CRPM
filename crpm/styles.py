"""Custom CSS styling for CRPM Process Mining Workbench.

This module provides centralized styling for consistent UI/UX across the application.
"""


def get_custom_css() -> str:
    """Generate custom CSS for the Streamlit application.

    Returns:
        CSS string to be injected via st.markdown with unsafe_allow_html=True
    """
    return """
    <style>
    /* ===================================================================
       Typography - Bold Headers and Clear Hierarchy
       =================================================================== */

    h1, h2, h3, h4, h5, h6 {
        font-weight: 700 !important;
        color: #2c3e50 !important;
        letter-spacing: -0.5px;
    }

    h1 {
        font-size: 2rem !important;
        margin-bottom: 1rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }

    h3 {
        font-weight: 600 !important;
        font-size: 1.25rem !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Tab Labels - Bold */
    .stTabs [data-baseweb="tab-list"] button {
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.75rem 1.5rem !important;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        font-weight: 700 !important;
    }

    /* ===================================================================
       Metrics - Bold and Prominent
       =================================================================== */

    [data-testid="stMetricLabel"] {
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #6c757d !important;
    }

    [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        font-size: 1.75rem !important;
        color: #2c3e50 !important;
    }

    [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }

    /* ===================================================================
       Sidebar - Professional Appearance
       =================================================================== */

    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        border-right: 2px solid #e0e0e0 !important;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        margin-bottom: 1rem !important;
        color: #1f77b4 !important;
    }

    [data-testid="stSidebar"] .stMarkdown {
        font-size: 0.9rem !important;
    }

    /* ===================================================================
       Buttons - Bold and Modern
       =================================================================== */

    .stButton button {
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }

    .stButton button[kind="primary"] {
        background-color: #1f77b4 !important;
        border: none !important;
        font-weight: 700 !important;
    }

    .stButton button[kind="secondary"] {
        border: 2px solid #1f77b4 !important;
        color: #1f77b4 !important;
        font-weight: 600 !important;
    }

    /* ===================================================================
       Info/Warning/Error/Success Boxes - Styled Cards
       =================================================================== */

    .stAlert {
        border-radius: 8px !important;
        border-left: 4px solid !important;
        padding: 1rem !important;
        font-weight: 500 !important;
    }

    .stSuccess {
        background-color: #d4edda !important;
        border-left-color: #28a745 !important;
        color: #155724 !important;
    }

    .stInfo {
        background-color: #d1ecf1 !important;
        border-left-color: #17a2b8 !important;
        color: #0c5460 !important;
    }

    .stWarning {
        background-color: #fff3cd !important;
        border-left-color: #ffc107 !important;
        color: #856404 !important;
    }

    .stError {
        background-color: #f8d7da !important;
        border-left-color: #dc3545 !important;
        color: #721c24 !important;
    }

    /* ===================================================================
       Data Tables - Professional and Clean
       =================================================================== */

    .dataframe {
        font-size: 0.9rem !important;
        border-radius: 8px !important;
        overflow: hidden;
    }

    .dataframe thead tr {
        background-color: #f0f2f6 !important;
    }

    .dataframe th {
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0.75rem !important;
        border-bottom: 2px solid #dee2e6 !important;
    }

    .dataframe td {
        padding: 0.5rem 0.75rem !important;
        border-bottom: 1px solid #e9ecef !important;
    }

    .dataframe tbody tr:hover {
        background-color: #f8f9fa !important;
    }

    /* ===================================================================
       Expanders - Refined Cards
       =================================================================== */

    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 1rem !important;
        border-radius: 6px !important;
        background-color: #f8f9fa !important;
        padding: 0.75rem 1rem !important;
    }

    .streamlit-expanderHeader:hover {
        background-color: #e9ecef !important;
    }

    /* ===================================================================
       File Uploaders - Modern
       =================================================================== */

    [data-testid="stFileUploader"] {
        border-radius: 8px !important;
        border: 2px dashed #dee2e6 !important;
        padding: 1rem !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #1f77b4 !important;
        background-color: #f8f9fa !important;
    }

    /* ===================================================================
       Select Boxes and Inputs - Refined
       =================================================================== */

    .stSelectbox label, .stTextInput label, .stNumberInput label {
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #495057 !important;
    }

    /* ===================================================================
       Checkboxes and Radio Buttons - Clear
       =================================================================== */

    .stCheckbox label, .stRadio label {
        font-weight: 600 !important;
    }

    /* ===================================================================
       Progress Bars - Smooth
       =================================================================== */

    .stProgress > div > div > div {
        background-color: #1f77b4 !important;
    }

    /* ===================================================================
       Container Spacing - Balanced Layout
       =================================================================== */

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }

    /* Individual sections */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        padding: 0.5rem 0;
    }

    /* ===================================================================
       Captions - Light and Readable
       =================================================================== */

    .stCaption {
        color: #6c757d !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
    }

    /* ===================================================================
       Plotly Charts - Clean Borders
       =================================================================== */

    .js-plotly-plot {
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* ===================================================================
       Download Buttons - Consistent Style
       =================================================================== */

    .stDownloadButton button {
        font-weight: 600 !important;
        font-size: 0.875rem !important;
    }

    /* ===================================================================
       Spinner - Professional
       =================================================================== */

    .stSpinner > div {
        border-top-color: #1f77b4 !important;
    }

    /* ===================================================================
       Markdown Content - Better Spacing
       =================================================================== */

    .stMarkdown p {
        margin-bottom: 0.75rem !important;
    }

    .stMarkdown ul, .stMarkdown ol {
        margin-left: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }

    .stMarkdown li {
        margin-bottom: 0.25rem !important;
    }

    .stMarkdown strong {
        font-weight: 700 !important;
        color: #2c3e50 !important;
    }

    /* ===================================================================
       Horizontal Rules - Styled Dividers
       =================================================================== */

    hr {
        margin: 2rem 0 !important;
        border: none !important;
        border-top: 2px solid #e0e0e0 !important;
    }

    /* ===================================================================
       Code Blocks - Refined
       =================================================================== */

    code {
        background-color: #f4f4f4 !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 4px !important;
        font-family: 'Monaco', 'Menlo', 'Consolas', monospace !important;
        font-size: 0.875rem !important;
    }

    pre {
        background-color: #2d2d2d !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }

    /* ===================================================================
       Quality Badges - Enhanced
       =================================================================== */

    .quality-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        margin: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
    """


def apply_custom_styling():
    """Apply custom CSS styling to the Streamlit app.

    This function should be called once at the beginning of the app,
    after imports and before st.set_page_config().
    """
    import streamlit as st
    st.markdown(get_custom_css(), unsafe_allow_html=True)


__all__ = ["get_custom_css", "apply_custom_styling"]
