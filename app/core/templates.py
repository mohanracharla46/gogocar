"""
Template configuration for Jinja2
"""
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

# Get templates directory
# Use absolute path based on this file's location to ensure it works regardless of CWD
_this_file = Path(__file__).resolve()
# __file__ resolves to: /path/to/gogocar/app/core/templates.py
# Go up 3 levels: app/core -> app -> gogocar -> templates
_project_root = _this_file.parent.parent.parent
templates_dir = _project_root / "templates"

# Ensure we use absolute path for Jinja2
templates_dir_abs = templates_dir.resolve()

# Verify templates directory exists
if not templates_dir_abs.exists():
    # Fallback: try relative to current working directory
    _cwd = Path.cwd()
    _fallback_templates = _cwd / "templates"
    if _fallback_templates.exists():
        templates_dir_abs = _fallback_templates.resolve()
    else:
        # Log error but don't raise - let Jinja2 handle it
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Templates directory not found. "
            f"Tried: {templates_dir_abs}, {_fallback_templates}. "
            f"This file: {_this_file}, Project root: {_project_root}, CWD: {_cwd}"
        )
        # Use fallback anyway - Jinja2 will raise TemplateNotFound if template doesn't exist
        templates_dir_abs = templates_dir_abs

# Create Jinja2 templates instance
# Use absolute path string to avoid any path resolution issues
templates = Jinja2Templates(directory=str(templates_dir_abs), auto_reload=True)

