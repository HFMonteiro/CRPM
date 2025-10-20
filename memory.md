# CRPM Memory

## 2025-10-20: Codespaces, Upload UX, and Robust Ingestion

- **Codespaces proxy 413**: Browser uploads >50MB often fail due to Codespaces/nginx proxy, not Streamlit. App now guides users to use the xes_logs/ folder or server-side URL fetch for large files.
- **File browser restored**: 'Browse files' is available for convenience, but warns about proxy limits. Folder and URL fetch are always reliable.
- **Sidebar workflow**: Users are guided to copy files to xes_logs/ (or any folder), click Refresh, and select from the dropdown. URL fetch is available for remote files.
- **No regressions**: All analytics, layout, and export features remain. Desktop 16:9 layout, analytics tabs, and conformance model selector are preserved.
- **README and memory.md**: Updated to reflect Codespaces/cross-proxy issues, robust ingestion, and workflow guidance.

## Key Decisions
- Remove browser upload as default; keep as fallback with warning.
- Always prefer local folder or URL fetch for large files.
- Document Codespaces/proxy 413 as a known issue.
- No features removed; only improved UX and reliability.

## Next Steps
- Monitor for further Codespaces/remote proxy issues.
- Consider adding a CLI or UI helper to move files into xes_logs/ from anywhere in the workspace.
- Continue aligning UI/UX with notebook and user feedback.
