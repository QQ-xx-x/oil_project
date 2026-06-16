# -*- coding: utf-8 -*-
"""工作台 SVG 图标资源。"""

from .icon_registry import common_svg_keys, oilfield_svg_keys


OILFIELD_SVG_KEYS = set(oilfield_svg_keys())
COMMON_SVG_KEYS = set(common_svg_keys())


def svg_icon(kind):
    return oilfield_svg_icon(kind) or common_svg_icon(kind)


def oilfield_svg_icon(kind):
    return SVG_ICONS.get(kind) if kind in OILFIELD_SVG_KEYS else None


def common_svg_icon(kind):
    return SVG_ICONS.get(kind) if kind in COMMON_SVG_KEYS else None


def _svg(body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
<defs>
  <linearGradient id="steel" x1="4" y1="3" x2="20" y2="21" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#f7fbff"/>
    <stop offset="1" stop-color="#cfdbe6"/>
  </linearGradient>
  <linearGradient id="blue" x1="5" y1="4" x2="19" y2="20" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#72b7d6"/>
    <stop offset="1" stop-color="#2f6f9f"/>
  </linearGradient>
  <linearGradient id="green" x1="5" y1="4" x2="19" y2="20" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#8fd0aa"/>
    <stop offset="1" stop-color="#2f9e66"/>
  </linearGradient>
  <linearGradient id="amber" x1="5" y1="4" x2="19" y2="20" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#f5ce75"/>
    <stop offset="1" stop-color="#c28a2a"/>
  </linearGradient>
  <linearGradient id="red" x1="5" y1="4" x2="19" y2="20" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#df8a76"/>
    <stop offset="1" stop-color="#b85d4f"/>
  </linearGradient>
  <linearGradient id="rock" x1="4" y1="3" x2="20" y2="21" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#d9c9a8"/>
    <stop offset="1" stop-color="#9a8664"/>
  </linearGradient>
  <filter id="shadow" x="-25%" y="-25%" width="150%" height="150%">
    <feDropShadow dx="0" dy="0.8" stdDeviation="0.7" flood-color="#506070" flood-opacity="0.28"/>
  </filter>
</defs>
{body}
</svg>"""


_CARD = 'fill="url(#steel)" stroke="#5d6b78" stroke-width="1.15"'
_STROKE = 'fill="none" stroke="#334155" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"'
_SOFT_STROKE = 'fill="none" stroke="#526477" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"'


SVG_ICONS = {
    "folder": _svg(f"""
<path d="M3.2 8.2h6.6l1.8 2h9.2v7.6c0 1.1-.9 2-2 2H5.2c-1.1 0-2-.9-2-2V8.2z" fill="url(#amber)" stroke="#7c5a1f" stroke-width="1.1" filter="url(#shadow)"/>
<path d="M3.4 7.1c0-1 .8-1.8 1.8-1.8h4.4l1.7 1.8h5.8c1 0 1.8.8 1.8 1.8v1.3H3.4V7.1z" fill="#f7d889" stroke="#7c5a1f" stroke-width="1.05"/>
"""),
    "file": _svg(f"""
<path d="M6.2 3.4h8.7l3.7 3.8v13.4H6.2z" {_CARD} filter="url(#shadow)"/>
<path d="M14.8 3.6v3.9h3.7" fill="#e9f0f6" stroke="#718192" stroke-width="1"/>
<path d="M8.8 11h6.6M8.8 14h6.6M8.8 17h4.3" {_SOFT_STROKE}/>
"""),
    "case_root": _svg(f"""
<ellipse cx="12" cy="5.2" rx="6.8" ry="2.6" fill="#88bfd1" stroke="#3d7187" stroke-width="1.05"/>
<path d="M5.2 5.2v9.8c0 1.4 3.1 2.6 6.8 2.6s6.8-1.2 6.8-2.6V5.2" fill="url(#blue)" stroke="#3d7187" stroke-width="1.05" filter="url(#shadow)"/>
<ellipse cx="12" cy="15" rx="6.8" ry="2.6" fill="#5ea6bf" stroke="#3d7187" stroke-width="1.05"/>
<path d="M8.4 9h7.2M8.4 12h7.2" stroke="#eef8fb" stroke-width="1.2" stroke-linecap="round"/>
"""),
    "case_section": _svg(f"""
<path d="M4 7.7h5.2l1.5 1.6H20v8.8c0 .9-.7 1.6-1.6 1.6H5.6c-.9 0-1.6-.7-1.6-1.6z" fill="#e5edf4" stroke="#68788a" stroke-width="1.1" filter="url(#shadow)"/>
<path d="M6.8 12h10.4M6.8 15h7.4" {_SOFT_STROKE}/>
"""),
    "keyword_param": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="2.2" {_CARD} filter="url(#shadow)"/>
<path d="M7.5 8.4h9M7.5 12h9M7.5 15.6h9" {_SOFT_STROKE}/>
<circle cx="10" cy="8.4" r="1.15" fill="#4f95ad" stroke="#ffffff" stroke-width=".45"/>
<circle cx="14.8" cy="12" r="1.15" fill="#2f9e66" stroke="#ffffff" stroke-width=".45"/>
<circle cx="11.9" cy="15.6" r="1.15" fill="#c28a2a" stroke="#ffffff" stroke-width=".45"/>
"""),
    "grid": _svg(f"""
<path d="M4.2 6.5 12 3l7.8 3.5v10.8L12 21l-7.8-3.7z" fill="url(#blue)" stroke="#355f75" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M4.4 6.7 12 10.2l7.6-3.5M12 10.2v10.3M7.9 8.2v10.6M16.1 8.2v10.6M4.5 12.2l7.5 3.3 7.5-3.3" stroke="#eaf8fb" stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "grid_file": _svg(f"""
<path d="M6.2 3.4h8.7l3.7 3.8v13.4H6.2z" {_CARD} filter="url(#shadow)"/>
<path d="M14.8 3.6v3.9h3.7" fill="#e9f0f6" stroke="#718192" stroke-width="1"/>
<rect x="8.4" y="10.2" width="7.2" height="7.2" fill="#dff2f7" stroke="#2f6f9f" stroke-width="1"/>
<path d="M10.8 10.2v7.2M13.2 10.2v7.2M8.4 12.6h7.2M8.4 15h7.2" stroke="#2f6f9f" stroke-width=".7"/>
"""),
    "lgr": _svg(f"""
<path d="M4.2 6.5 12 3l7.8 3.5v10.8L12 21l-7.8-3.7z" fill="url(#blue)" stroke="#355f75" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M4.4 6.7 12 10.2l7.6-3.5M12 10.2v10.3M4.5 12.2l7.5 3.3 7.5-3.3" stroke="#eaf8fb" stroke-width="1"/>
<rect x="10.2" y="11.6" width="4.2" height="4.2" fill="#f4c84b" stroke="#7c5a1f" stroke-width=".75"/>
<path d="M11.6 11.6v4.2M13 11.6v4.2M10.2 13h4.2M10.2 14.4h4.2" stroke="#7c5a1f" stroke-width=".45"/>
"""),
    "property_file": _svg(f"""
<path d="M6.2 3.4h8.7l3.7 3.8v13.4H6.2z" {_CARD} filter="url(#shadow)"/>
<path d="M14.8 3.6v3.9h3.7" fill="#e9f0f6" stroke="#718192" stroke-width="1"/>
<path d="M9 10h6M9 13h6M9 16h6" stroke="#2f9e66" stroke-width="1.45" stroke-linecap="round"/>
<circle cx="9" cy="10" r="1.1" fill="#2f9e66"/><circle cx="15" cy="13" r="1.1" fill="#2f9e66"/><circle cx="11.7" cy="16" r="1.1" fill="#2f9e66"/>
"""),
    "rock": _svg(f"""
<path d="M4.6 15.8 7.8 6.3l6.5-2.4 5.4 6.2-2.2 8.1-7.8 2z" fill="url(#rock)" stroke="#6f6048" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M7.8 6.3 11.2 12l3.1-8.1M11.2 12l6.3 6.2M11.2 12l-1.5 8.2" stroke="#f3e4c5" stroke-width=".9" stroke-linecap="round" stroke-linejoin="round" opacity=".75"/>
"""),
    "porosity": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="#f2eee4" stroke="#6f6048" stroke-width="1.15" filter="url(#shadow)"/>
<circle cx="8.2" cy="8.6" r="1.9" fill="#fff9ea" stroke="#8c7655" stroke-width=".85"/>
<circle cx="14.2" cy="7.7" r="1.45" fill="#fff9ea" stroke="#8c7655" stroke-width=".85"/>
<circle cx="12.1" cy="13" r="2.2" fill="#fff9ea" stroke="#8c7655" stroke-width=".85"/>
<circle cx="16.2" cy="16.1" r="1.5" fill="#fff9ea" stroke="#8c7655" stroke-width=".85"/>
<circle cx="7.6" cy="16" r="1.25" fill="#fff9ea" stroke="#8c7655" stroke-width=".85"/>
"""),
    "permeability": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="#eef7f0" stroke="#597966" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M7.1 8.1h8.5l1.4 1.4-1.4 1.4H7.1M7.1 13.1h7.4l1.4 1.4-1.4 1.4H7.1" fill="none" stroke="#2f9e66" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="8.3" cy="9.5" r="1.05" fill="#ffffff" stroke="#2f9e66" stroke-width=".8"/>
<circle cx="11.2" cy="14.5" r="1.05" fill="#ffffff" stroke="#2f9e66" stroke-width=".8"/>
"""),
    "fluid": _svg(f"""
<path d="M12 3.7c3.6 4.2 5.5 7 5.5 10 0 3.2-2.4 5.8-5.5 5.8s-5.5-2.6-5.5-5.8c0-3 1.9-5.8 5.5-10z" fill="url(#blue)" stroke="#2d6684" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M9.2 14.5c.7 1.4 1.7 2.1 3.2 2.1" stroke="#eaf8fb" stroke-width="1.2" stroke-linecap="round"/>
<path d="M8.9 11.1c1.8-.8 4.2-.8 6 0" stroke="#bfe8f4" stroke-width="1" stroke-linecap="round"/>
"""),
    "saturation": _svg(f"""
<path d="M12 3.7c3.6 4.2 5.5 7 5.5 10 0 3.2-2.4 5.8-5.5 5.8s-5.5-2.6-5.5-5.8c0-3 1.9-5.8 5.5-10z" fill="url(#blue)" stroke="#2d6684" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M6.8 13.2c3.4-1.8 6.9 2 10.4.2v2.4c-1.6 2.7-4.4 3.8-7 2.7-1.8-.8-3.1-2.8-3.4-5.3z" fill="#eaf8fb" opacity=".72"/>
<path d="M7.1 13.1c3.2-1.7 6.4 1.7 9.8.2" stroke="#2d6684" stroke-width=".9" stroke-linecap="round"/>
"""),
    "pressure": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<rect x="7.2" y="11.1" width="2.4" height="5.6" rx=".6" fill="#5799c7"/>
<rect x="10.8" y="8.3" width="2.4" height="8.4" rx=".6" fill="#f0ad4e"/>
<rect x="14.4" y="6.1" width="2.4" height="10.6" rx=".6" fill="#d9534f"/>
<path d="M6.8 17.2h10.4" stroke="#526477" stroke-width="1" stroke-linecap="round"/>
"""),
    "fracture": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="#fff4ef" stroke="#8d4a42" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M7.4 18.1 10 11.6l-1.2-2.4 3.1-3.4 1.6 5.2 3.1-1.7-2.1 8.9" fill="none" stroke="#b85d4f" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M10.1 11.6h3.3M13.6 11.1l1.1 3" stroke="#efaa9c" stroke-width="1" stroke-linecap="round"/>
"""),
    "dfn_file": _svg(f"""
<path d="M6.2 3.4h8.7l3.7 3.8v13.4H6.2z" {_CARD} filter="url(#shadow)"/>
<path d="M14.8 3.6v3.9h3.7" fill="#e9f0f6" stroke="#718192" stroke-width="1"/>
<path d="M8.6 17.1 10.6 12l-1-1.8 2.5-2.8 1.3 4.2 2.4-1.4-1.7 7" fill="none" stroke="#b85d4f" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "well": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="#eef7fb" stroke="#4f7893" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M12 5.8v12.1" stroke="#1d9bd1" stroke-width="2.1" stroke-linecap="round"/>
<path d="M12 11.1c2.4.6 4 2.1 5.2 4.5" stroke="#e15b32" stroke-width="1.25" stroke-linecap="round" fill="none"/>
<path d="M8.5 7.3h7M8.5 9.3h7" stroke="#9ab9cc" stroke-width=".8" stroke-linecap="round"/>
"""),
    "solver": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<circle cx="8.3" cy="8.4" r="2" fill="#ffffff" stroke="#526477" stroke-width="1"/>
<circle cx="15.7" cy="8.4" r="2" fill="#ffffff" stroke="#526477" stroke-width="1"/>
<circle cx="12" cy="15.7" r="2.1" fill="#ffffff" stroke="#526477" stroke-width="1"/>
<path d="M10.3 8.4h3.4M9.3 10.1l1.6 3.6M14.7 10.1l-1.6 3.6" {_SOFT_STROKE}/>
"""),
    "run": _svg(f"""
<circle cx="12" cy="12" r="8.4" fill="url(#green)" stroke="#1e6f49" stroke-width="1.2" filter="url(#shadow)"/>
<path d="M10.2 8.1v7.8l6-3.9z" fill="#ffffff" stroke="#ffffff" stroke-width=".8" stroke-linejoin="round"/>
"""),
    "validate": _svg(f"""
<path d="M12 3.8 18.5 6v5.6c0 4.2-2.6 6.7-6.5 8.6-3.9-1.9-6.5-4.4-6.5-8.6V6z" fill="url(#steel)" stroke="#5d6b78" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M8.4 12.1 11 14.7l5-5.6" fill="none" stroke="#2f9e66" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "result": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<path d="M7.3 16.7V12M12 16.7V8M16.7 16.7v-6.1" stroke="#2f6f9f" stroke-width="1.7" stroke-linecap="round"/>
<path d="M6.7 17.2h10.8" stroke="#526477" stroke-width="1" stroke-linecap="round"/>
<circle cx="16.8" cy="7.7" r="2" fill="#2f9e66" stroke="#ffffff" stroke-width=".8"/>
"""),
    "layer": _svg(f"""
<path d="M12 4.4 20 8.1 12 11.8 4 8.1z" fill="#e8eef5" stroke="#526477" stroke-width="1.05" filter="url(#shadow)"/>
<path d="M4 11.3 12 15l8-3.7" fill="none" stroke="#6f8794" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M4 14.6 12 18.3l8-3.7" fill="none" stroke="#3d7187" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "chart": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<path d="M7 16.6h10.4M7 7.4v9.2" stroke="#526477" stroke-width="1" stroke-linecap="round"/>
<path d="M7.4 14.9 10.3 12l2.7 1.5 4-5.2" fill="none" stroke="#2670c9" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="10.3" cy="12" r="1" fill="#2670c9"/><circle cx="13" cy="13.5" r="1" fill="#2670c9"/>
"""),
    "database": _svg(f"""
<ellipse cx="12" cy="6.4" rx="6.4" ry="2.7" fill="#88bfd1" stroke="#3d7187" stroke-width="1.05"/>
<path d="M5.6 6.4v8.8c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7V6.4" fill="url(#blue)" stroke="#3d7187" stroke-width="1.05" filter="url(#shadow)"/>
<path d="M5.6 10.8c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7" fill="none" stroke="#eaf8fb" stroke-width="1"/>
"""),
    "import": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<path d="M12 6.6v7.7M8.9 11.3l3.1 3.1 3.1-3.1" fill="none" stroke="#2c8c68" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M7.7 17h8.6" stroke="#526477" stroke-width="1.1" stroke-linecap="round"/>
"""),
    "save": _svg(f"""
<path d="M5.1 4.4h12l1.8 1.8v13.4H5.1z" fill="url(#steel)" stroke="#5d6b78" stroke-width="1.15" filter="url(#shadow)"/>
<rect x="8" y="5.7" width="7.2" height="4.2" rx=".6" fill="#ffffff" stroke="#718192" stroke-width=".8"/>
<rect x="8" y="14.1" width="8" height="4" rx=".8" fill="#ffffff" stroke="#718192" stroke-width=".8"/>
<path d="M13.6 6.2v2.9" stroke="#2f6f9f" stroke-width="1" stroke-linecap="round"/>
"""),
    "new": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<path d="M12 7.3v9.4M7.3 12h9.4" stroke="#d88c18" stroke-width="2" stroke-linecap="round"/>
"""),
    "copy": _svg(f"""
<rect x="6.2" y="5.3" width="9.8" height="12" rx="1.4" fill="#dce6ef" stroke="#6f7f91" stroke-width="1.05" filter="url(#shadow)"/>
<rect x="8.4" y="7.1" width="9.4" height="11.6" rx="1.4" fill="#ffffff" stroke="#6f7f91" stroke-width="1.05"/>
<path d="M10.4 10.5h5.2M10.4 13.2h5.2M10.4 15.9h3.4" {_SOFT_STROKE}/>
"""),
    "window": _svg(f"""
<rect x="4.2" y="4.7" width="15.6" height="14.6" rx="2" fill="url(#steel)" stroke="#5d6b78" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M4.6 8.2h14.8" stroke="#6f7f91" stroke-width="1.05"/>
<circle cx="7" cy="6.5" r=".65" fill="#d9534f"/><circle cx="9.2" cy="6.5" r=".65" fill="#f0ad4e"/><circle cx="11.4" cy="6.5" r=".65" fill="#2f9e66"/>
"""),
    "process": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" {_CARD} filter="url(#shadow)"/>
<path d="M7.4 8.3h6.8l2.4 2.4-2.4 2.4H7.4M9.8 13.1 7.4 15.5l2.4 2.4h6.8" fill="none" stroke="#2c8c68" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "search": _svg(f"""
<circle cx="10.7" cy="10.4" r="5.1" fill="url(#steel)" stroke="#5d6b78" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M14.6 14.3 19 18.7" stroke="#334155" stroke-width="1.8" stroke-linecap="round"/>
<path d="M8.4 9.4c.6-1 1.4-1.5 2.6-1.5" stroke="#ffffff" stroke-width="1.1" stroke-linecap="round"/>
"""),
    "warning": _svg(f"""
<path d="M12 4.1 20.2 18.5H3.8z" fill="url(#amber)" stroke="#8a651f" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M12 9.1v4.6" stroke="#5d4200" stroke-width="1.8" stroke-linecap="round"/>
<circle cx="12" cy="16.2" r=".85" fill="#5d4200"/>
"""),
    "monitor": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="#edf6ef" stroke="#597966" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M6.7 13h2.4l1.2-4.1 2.1 7 1.5-4.4h3.4" fill="none" stroke="#2f9e66" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
"""),
    "case": _svg(f"""
<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3" fill="url(#blue)" stroke="#355f75" stroke-width="1.15" filter="url(#shadow)"/>
<path d="M7.2 8h9.6M7.2 12h9.6M7.2 16h6.4" stroke="#eaf8fb" stroke-width="1.2" stroke-linecap="round"/>
"""),
}
