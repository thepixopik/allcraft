#!/usr/bin/env python3
"""Assemble all 15 Craft web app artifacts into dist/, maintain a permanent rolling backup in the 'studio-cache' GitHub Release (90-day Actions artifact expiry fallback), strip + repack Wasm into 1.5 MiB pipelined streaming chunks, inject <base href> + Photoshop-style splash UI + Zero-Clone CacheStorage Wasm loader, and emit /prefetch-manifest.json."""

import datetime
import gzip
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import generate_pages

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS_CONFIG = ROOT / "apps.json"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"
CF_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB Cloudflare Pages single-asset limit
STREAM_CHUNK_BYTES = int(1.5 * 1024 * 1024)  # 1.5 MiB pipelined streaming chunks
HUB_REPO = (os.environ.get("GITHUB_REPOSITORY") or "thepixopik/allcraft").strip()
CACHE_RELEASE_TAG = "studio-cache"
CACHE_MANIFEST_ASSET = "cache-manifest.json"

SPLASH_PROFILES = {
    "vector": {
        "container_id": "vectorcraft_loading",
        "bar_id": "vc_load_bar",
        "pct_id": "vc_load_pct",
        "code": "Vc",
        "title": "The AllCraft Vector",
        "tagline": "Precision Vector Illustration & Typography Studio",
        "accent": "#E8573F",
        "accent_soft": "rgba(232, 87, 63, 0.22)",
        "badge_bg": "#2B1410",
        "stages": [
            "Initializing WebGPU Vector Engine…",
            "Loading Pen, Bézier & Path Boolean Tools…",
            "Reading Typography, Swatches & Gradients…",
            "Preparing Multi-Artboard Canvas…",
            "Compiling Native Studio Runtime…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="g1" cx="65%" cy="32%" r="65%"><stop offset="0%" stop-color="#ff7b54" stop-opacity="0.55"/><stop offset="100%" stop-color="#171214" stop-opacity="0"/></radialGradient>
            <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#e8573f"/><stop offset="100%" stop-color="#ffb36b"/></linearGradient>
          </defs>
          <rect width="260" height="360" fill="#171315"/>
          <rect width="260" height="360" fill="url(#g1)"/>
          <circle cx="170" cy="135" r="78" fill="none" stroke="url(#g2)" stroke-width="2.2" opacity="0.75"/>
          <path d="M 38 270 C 68 120, 195 240, 224 88" fill="none" stroke="url(#g2)" stroke-width="3.5"/>
          <line x1="38" y1="270" x2="68" y2="120" stroke="#ffb36b" stroke-width="1.3" stroke-dasharray="4 4" opacity="0.8"/>
          <line x1="224" y1="88" x2="195" y2="240" stroke="#ffb36b" stroke-width="1.3" stroke-dasharray="4 4" opacity="0.8"/>
          <rect x="33" y="265" width="10" height="10" rx="2" fill="#171315" stroke="#fff" stroke-width="2"/>
          <rect x="219" y="83" width="10" height="10" rx="2" fill="#171315" stroke="#fff" stroke-width="2"/>
          <circle cx="68" cy="120" r="5" fill="#ffb36b"/>
          <circle cx="195" cy="240" r="5" fill="#ffb36b"/>
          <polygon points="130,152 154,202 130,192 106,202" fill="#fff" opacity="0.92"/>
        </svg>""",
    },
    "photo": {
        "container_id": "photocraft_loading",
        "bar_id": "pc_load_bar",
        "pct_id": "pc_load_pct",
        "code": "Ph",
        "title": "The AllCraft Photo",
        "tagline": "Non-Destructive Imaging, RAW & Layer Compositing",
        "accent": "#31A8FF",
        "accent_soft": "rgba(49, 168, 255, 0.24)",
        "badge_bg": "#081E36",
        "stages": [
            "Initializing WebGPU & 32-Bit Color Engine…",
            "Reading Brushes, Gradients & Tool Presets…",
            "Loading Camera RAW & Smart Filter Pipeline…",
            "Preparing Non-Destructive Layer Compositor…",
            "Building Workspace Panels & Shortcuts…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="pg1" cx="35%" cy="28%" r="70%"><stop offset="0%" stop-color="#31a8ff" stop-opacity="0.62"/><stop offset="55%" stop-color="#1d4ed8" stop-opacity="0.24"/><stop offset="100%" stop-color="#0b1320" stop-opacity="0"/></radialGradient>
            <radialGradient id="pg2" cx="78%" cy="74%" r="55%"><stop offset="0%" stop-color="#38bdf8" stop-opacity="0.45"/><stop offset="100%" stop-color="#0b1320" stop-opacity="0"/></radialGradient>
            <linearGradient id="pg3" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#7dd3fc"/></linearGradient>
          </defs>
          <rect width="260" height="360" fill="#0b1320"/>
          <rect width="260" height="360" fill="url(#pg1)"/>
          <rect width="260" height="360" fill="url(#pg2)"/>
          <rect x="46" y="72" width="142" height="178" rx="18" fill="rgba(255,255,255,0.05)" stroke="rgba(125,211,252,0.35)" stroke-width="1.5" transform="rotate(-8 117 161)"/>
          <rect x="68" y="96" width="142" height="178" rx="18" fill="rgba(14,30,56,0.72)" stroke="url(#pg3)" stroke-width="1.8" transform="rotate(5 139 185)"/>
          <circle cx="122" cy="152" r="22" fill="none" stroke="#7dd3fc" stroke-width="2" opacity="0.9"/>
          <path d="M 74 248 Q 116 188, 146 218 T 208 176" fill="none" stroke="#38bdf8" stroke-width="3"/>
        </svg>""",
    },
    "light": {
        "container_id": "lightcraft_loading",
        "bar_id": "lc_load_bar",
        "pct_id": "lc_load_pct",
        "code": "Lc",
        "title": "The AllCraft Light",
        "tagline": "RAW Photo Catalog, Culling & Color Darkroom",
        "accent": "#22D3EE",
        "accent_soft": "rgba(34, 211, 238, 0.24)",
        "badge_bg": "#06232B",
        "stages": [
            "Initializing Linear RAW & HDR Color Pipeline…",
            "Loading Camera DCP Profiles & Lens Database…",
            "Preparing Tone Curves, Color Wheels & Masks…",
            "Starting Multi-Worker Thumbnail & Catalog Engine…",
            "Opening RAW Darkroom…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="ck1" cx="55%" cy="34%" r="68%"><stop offset="0%" stop-color="#22d3ee" stop-opacity="0.52"/><stop offset="100%" stop-color="#09161b" stop-opacity="0"/></radialGradient>
            <linearGradient id="ck2" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stop-color="#0891b2"/><stop offset="100%" stop-color="#67e8f9"/></linearGradient>
          </defs>
          <rect width="260" height="360" fill="#09161b"/>
          <rect width="260" height="360" fill="url(#ck1)"/>
          <circle cx="130" cy="142" r="56" fill="none" stroke="url(#ck2)" stroke-width="2.2"/>
          <circle cx="130" cy="142" r="34" fill="none" stroke="rgba(103,232,249,0.45)" stroke-width="1.5"/>
          <path d="M 38 268 Q 74 214, 108 242 T 168 198 T 224 238 L 224 268 Z" fill="rgba(34,211,238,0.22)" stroke="#22d3ee" stroke-width="2"/>
          <path d="M 48 268 C 92 260, 148 196, 214 190" fill="none" stroke="#fff" stroke-width="2" opacity="0.85"/>
        </svg>""",
    },
    "design": {
        "container_id": "designcraft_loading",
        "bar_id": "dc_load_bar",
        "pct_id": "dc_load_pct",
        "code": "Ds",
        "title": "The AllCraft Design",
        "tagline": "Desktop Publishing, Master Layouts & Prepress Studio",
        "accent": "#F59E0B",
        "accent_soft": "rgba(245, 158, 11, 0.24)",
        "badge_bg": "#2E1C06",
        "stages": [
            "Initializing Multi-Page Layout & Grid Engine…",
            "Loading OpenType Typography & Paragraph Composer…",
            "Preparing Master Spreads & CMYK Separations…",
            "Loading IDML, INDD, EPUB & Print PDF Exporters…",
            "Opening Publishing Workspace…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="lg1" cx="60%" cy="32%" r="68%"><stop offset="0%" stop-color="#f59e0b" stop-opacity="0.5"/><stop offset="100%" stop-color="#19140d" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#19140d"/>
          <rect width="260" height="360" fill="url(#lg1)"/>
          <rect x="34" y="88" width="94" height="176" rx="6" fill="rgba(255,255,255,0.06)" stroke="#fbbf24" stroke-width="1.4"/>
          <rect x="132" y="88" width="94" height="176" rx="6" fill="rgba(255,255,255,0.06)" stroke="#fbbf24" stroke-width="1.4"/>
          <rect x="46" y="102" width="70" height="64" rx="4" fill="rgba(245,158,11,0.35)"/>
          <line x1="46" y1="182" x2="114" y2="182" stroke="rgba(255,255,255,0.45)" stroke-width="3"/>
          <line x1="46" y1="196" x2="106" y2="196" stroke="rgba(255,255,255,0.3)" stroke-width="3"/>
          <line x1="144" y1="106" x2="212" y2="106" stroke="#fde68a" stroke-width="4"/>
          <rect x="144" y="124" width="32" height="122" rx="3" fill="rgba(255,255,255,0.12)"/>
          <rect x="182" y="124" width="32" height="122" rx="3" fill="rgba(255,255,255,0.12)"/>
        </svg>""",
    },
    "ani": {
        "container_id": "anicraft_loading",
        "bar_id": "an_load_bar",
        "pct_id": "an_load_pct",
        "code": "An",
        "title": "The AllCraft Ani",
        "tagline": "2D Vector Animation, Tweens, Bones & Onion Skin",
        "accent": "#C084FC",
        "accent_soft": "rgba(192, 132, 252, 0.24)",
        "badge_bg": "#210E36",
        "stages": [
            "Initializing 2D Vector Stage & Brush Engine…",
            "Loading Classic Tweens, Shape Hints & Easing…",
            "Preparing Armature Bones, IK & Onion Skin…",
            "Loading FLA/XFL, Lottie, GIF & WebP Exporters…",
            "Opening Animation Stage…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="an1" cx="55%" cy="34%" r="68%"><stop offset="0%" stop-color="#a855f7" stop-opacity="0.52"/><stop offset="100%" stop-color="#140d1d" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#140d1d"/>
          <rect width="260" height="360" fill="url(#an1)"/>
          <path d="M 42 226 Q 130 82, 218 226" fill="none" stroke="rgba(192,132,252,0.45)" stroke-width="2" stroke-dasharray="5 5"/>
          <circle cx="56" cy="204" r="18" fill="rgba(192,132,252,0.12)" stroke="rgba(192,132,252,0.35)" stroke-width="1.5"/>
          <circle cx="92" cy="156" r="21" fill="rgba(192,132,252,0.22)" stroke="rgba(192,132,252,0.55)" stroke-width="1.6"/>
          <circle cx="136" cy="136" r="25" fill="rgba(192,132,252,0.38)" stroke="#d8b4fe" stroke-width="2"/>
          <circle cx="186" cy="176" r="28" fill="#c084fc" stroke="#fff" stroke-width="2.2"/>
          <rect x="34" y="256" width="192" height="28" rx="6" fill="rgba(255,255,255,0.06)" stroke="rgba(192,132,252,0.35)"/>
          <circle cx="58" cy="270" r="4" fill="#fff"/><circle cx="106" cy="270" r="4" fill="#c084fc"/><circle cx="154" cy="270" r="4" fill="#c084fc"/><circle cx="202" cy="270" r="4" fill="#fff"/>
        </svg>""",
    },
    "texture": {
        "container_id": "texturecraft_loading",
        "bar_id": "tc_load_bar",
        "pct_id": "tc_load_pct",
        "extra_html": '<progress id="texturecraft_progress" max="1" hidden></progress><p id="texturecraft_status" hidden></p>',
        "code": "Tx",
        "title": "The AllCraft Texture",
        "tagline": "3D PBR Viewport Painting, Smart Masks & Mesh Bakers",
        "accent": "#FB7185",
        "accent_soft": "rgba(251, 113, 133, 0.24)",
        "badge_bg": "#2E0B14",
        "stages": [
            "Initializing WebGPU 3D PBR & UV Viewport…",
            "Loading glTF, USDZ, FBX & OBJ Mesh Importers…",
            "Preparing AO, Curvature & Normal Map Bakers…",
            "Loading Smart Materials, Brushes & Stencils…",
            "Opening 3D Painting Studio…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="tx1" cx="48%" cy="38%" r="64%"><stop offset="0%" stop-color="#fb7185" stop-opacity="0.58"/><stop offset="100%" stop-color="#190c10" stop-opacity="0"/></radialGradient>
            <radialGradient id="tx2" cx="40%" cy="35%" r="55%"><stop offset="0%" stop-color="#ffe4e6"/><stop offset="38%" stop-color="#fb7185"/><stop offset="100%" stop-color="#881337"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#190c10"/>
          <rect width="260" height="360" fill="url(#tx1)"/>
          <circle cx="130" cy="158" r="66" fill="url(#tx2)"/>
          <ellipse cx="130" cy="158" rx="66" ry="24" fill="none" stroke="rgba(255,255,255,0.42)" stroke-width="1.4" stroke-dasharray="4 4"/>
          <ellipse cx="130" cy="158" rx="24" ry="66" fill="none" stroke="rgba(255,255,255,0.42)" stroke-width="1.4" stroke-dasharray="4 4"/>
          <rect x="52" y="248" width="156" height="36" rx="7" fill="rgba(255,255,255,0.06)" stroke="rgba(251,113,133,0.4)"/>
        </svg>""",
    },
    "material": {
        "container_id": "materialcraft_loading",
        "bar_id": "mc_load_bar",
        "pct_id": "mc_load_pct",
        "extra_html": '<progress id="materialcraft_progress" max="1" hidden></progress><p id="materialcraft_status" hidden></p>',
        "code": "Mt",
        "title": "The AllCraft Material",
        "tagline": "Node-Based Procedural PBR Materials & 3D Preview",
        "accent": "#E879F9",
        "accent_soft": "rgba(232, 121, 249, 0.24)",
        "badge_bg": "#2B0B30",
        "stages": [
            "Initializing Procedural Graph & Tile Engine…",
            "Downloading SBS Node & Noise Pattern Library…",
            "Preparing Function Graphs & Normal Synthesis…",
            "Starting Live 2D & 3D PBR Material Renderer…",
            "Opening Material Graph Studio…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="mt1" cx="55%" cy="35%" r="68%"><stop offset="0%" stop-color="#d946ef" stop-opacity="0.52"/><stop offset="100%" stop-color="#170b1a" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#170b1a"/>
          <rect width="260" height="360" fill="url(#mt1)"/>
          <path d="M 88 122 C 118 122, 118 176, 148 176" fill="none" stroke="#e879f9" stroke-width="2.5"/>
          <path d="M 88 228 C 118 228, 118 188, 148 188" fill="none" stroke="#f0abfc" stroke-width="2.5"/>
          <rect x="34" y="98" width="54" height="48" rx="8" fill="rgba(232,121,249,0.18)" stroke="#e879f9" stroke-width="1.6"/>
          <rect x="34" y="204" width="54" height="48" rx="8" fill="rgba(232,121,249,0.18)" stroke="#e879f9" stroke-width="1.6"/>
          <rect x="148" y="148" width="76" height="68" rx="10" fill="rgba(232,121,249,0.28)" stroke="#f5d0fe" stroke-width="2"/>
          <circle cx="186" cy="182" r="20" fill="#e879f9"/>
        </svg>""",
    },
    "word": {
        "container_id": "wordcraft_loading",
        "bar_id": "wc_load_bar",
        "pct_id": "wc_load_pct",
        "code": "Wd",
        "title": "The AllCraft Word",
        "tagline": "Print-Layout Word Processor, Equations & Citations",
        "accent": "#818CF8",
        "accent_soft": "rgba(129, 140, 248, 0.24)",
        "badge_bg": "#15173B",
        "stages": [
            "Initializing Print-Layout Page & Font Shaper…",
            "Loading DOCX, ODT, RTF & Markdown Parsers…",
            "Preparing LaTeX Equation & Citation Engine…",
            "Loading Track Changes, Styles & Mail Merge…",
            "Opening Document Workspace…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="wg1" cx="55%" cy="32%" r="68%"><stop offset="0%" stop-color="#6366f1" stop-opacity="0.55"/><stop offset="100%" stop-color="#111222" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#111222"/>
          <rect width="260" height="360" fill="url(#wg1)"/>
          <rect x="54" y="72" width="152" height="212" rx="12" fill="rgba(255,255,255,0.06)" stroke="#818cf8" stroke-width="1.6"/>
          <text x="74" y="132" font-family="Georgia, serif" font-size="38" font-weight="700" fill="#c7d2fe">Aa</text>
          <line x1="74" y1="158" x2="186" y2="158" stroke="#818cf8" stroke-width="3.5" stroke-linecap="round"/>
          <line x1="74" y1="178" x2="178" y2="178" stroke="rgba(255,255,255,0.38)" stroke-width="3" stroke-linecap="round"/>
          <line x1="74" y1="196" x2="184" y2="196" stroke="rgba(255,255,255,0.38)" stroke-width="3" stroke-linecap="round"/>
          <line x1="74" y1="214" x2="152" y2="214" stroke="rgba(255,255,255,0.28)" stroke-width="3" stroke-linecap="round"/>
          <rect x="74" y="234" width="68" height="24" rx="5" fill="rgba(99,102,241,0.28)" stroke="#818cf8" stroke-width="1"/>
        </svg>""",
    },
    "grid": {
        "container_id": "gridcraft_loading",
        "bar_id": "gc_load_bar",
        "pct_id": "gc_load_pct",
        "code": "Gd",
        "title": "The AllCraft Grid",
        "tagline": "Spreadsheets, 400+ Formulas, PivotTables & Analytics",
        "accent": "#4ADE80",
        "accent_soft": "rgba(74, 222, 128, 0.24)",
        "badge_bg": "#082914",
        "stages": [
            "Initializing Vectorized Calculation Engine…",
            "Loading 400+ Excel Formulas & XLSX/ODS Parsers…",
            "Preparing PivotTables, Charts & Conditional Rules…",
            "Loading Sandboxed Python & Macro Runtime…",
            "Opening Workbook Grid…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="gg1" cx="55%" cy="34%" r="68%"><stop offset="0%" stop-color="#22c55e" stop-opacity="0.52"/><stop offset="100%" stop-color="#0a1910" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#0a1910"/>
          <rect width="260" height="360" fill="url(#gg1)"/>
          <rect x="38" y="78" width="184" height="128" rx="10" fill="rgba(255,255,255,0.05)" stroke="#4ade80" stroke-width="1.6"/>
          <line x1="38" y1="110" x2="222" y2="110" stroke="rgba(74,222,128,0.45)" stroke-width="1.4"/>
          <line x1="38" y1="142" x2="222" y2="142" stroke="rgba(255,255,255,0.12)" stroke-width="1.2"/>
          <line x1="38" y1="174" x2="222" y2="174" stroke="rgba(255,255,255,0.12)" stroke-width="1.2"/>
          <line x1="98" y1="78" x2="98" y2="206" stroke="rgba(255,255,255,0.14)" stroke-width="1.2"/>
          <line x1="160" y1="78" x2="160" y2="206" stroke="rgba(255,255,255,0.14)" stroke-width="1.2"/>
          <rect x="98" y="110" width="62" height="32" fill="rgba(34,197,94,0.26)" stroke="#4ade80" stroke-width="2"/>
          <rect x="54" y="248" width="24" height="36" rx="4" fill="#16a34a"/>
          <rect x="92" y="232" width="24" height="52" rx="4" fill="#22c55e"/>
          <rect x="130" y="218" width="24" height="66" rx="4" fill="#4ade80"/>
          <rect x="168" y="202" width="24" height="82" rx="4" fill="#86efac"/>
        </svg>""",
    },
    "deck": {
        "container_id": "deckcraft_loading",
        "bar_id": "dk_load_bar",
        "pct_id": "dk_load_pct",
        "code": "Dk",
        "title": "The AllCraft Deck",
        "tagline": "Presentations, Slide Masters, Animations & Live Show",
        "accent": "#FB923C",
        "accent_soft": "rgba(251, 146, 60, 0.24)",
        "badge_bg": "#2E1305",
        "stages": [
            "Initializing GPU Slide & Transition Renderer…",
            "Loading PPTX, POTX & ODP Theme Engine…",
            "Preparing Keyframe Animations & Morph Solver…",
            "Loading SmartArt, Charts & Presenter View…",
            "Opening Presentation Studio…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="dk1" cx="55%" cy="34%" r="68%"><stop offset="0%" stop-color="#f97316" stop-opacity="0.54"/><stop offset="100%" stop-color="#19110c" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#19110c"/>
          <rect width="260" height="360" fill="url(#dk1)"/>
          <rect x="44" y="84" width="164" height="104" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(251,146,60,0.4)" stroke-width="1.4" transform="rotate(-4 126 136)"/>
          <rect x="48" y="102" width="168" height="108" rx="12" fill="rgba(36,20,10,0.86)" stroke="#fb923c" stroke-width="1.8"/>
          <polygon points="118,136 154,156 118,176" fill="#fed7aa"/>
          <rect x="48" y="232" width="50" height="34" rx="6" fill="rgba(249,115,22,0.28)" stroke="#fb923c" stroke-width="1.4"/>
          <rect x="107" y="232" width="50" height="34" rx="6" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.18)" stroke-width="1.2"/>
          <rect x="166" y="232" width="50" height="34" rx="6" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.18)" stroke-width="1.2"/>
        </svg>""",
    },
    "pdf": {
        "container_id": "pdfcraft_loading",
        "bar_id": "pdf_load_bar",
        "pct_id": "pdf_load_pct",
        "code": "Pd",
        "title": "The AllCraft PDF",
        "tagline": "Document Editing, On-Device OCR, Forms & Signing",
        "accent": "#10B981",
        "accent_soft": "rgba(16, 185, 129, 0.24)",
        "badge_bg": "#08291E",
        "stages": [
            "Initializing Vector Page Renderer & Font Engine…",
            "Loading Form Fields, Redaction & Digital Signer…",
            "Preparing On-Device Neural OCR Worker…",
            "Loading Page Organizer & Preflight Rules…",
            "Opening PDF Workbench…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="dg1" cx="55%" cy="35%" r="68%"><stop offset="0%" stop-color="#10b981" stop-opacity="0.5"/><stop offset="100%" stop-color="#0d1916" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#0d1916"/>
          <rect width="260" height="360" fill="url(#dg1)"/>
          <rect x="58" y="76" width="144" height="196" rx="12" fill="rgba(255,255,255,0.06)" stroke="#34d399" stroke-width="1.6"/>
          <line x1="80" y1="112" x2="162" y2="112" stroke="#a7f3d0" stroke-width="4" stroke-linecap="round"/>
          <line x1="80" y1="132" x2="180" y2="132" stroke="rgba(255,255,255,0.35)" stroke-width="3" stroke-linecap="round"/>
          <line x1="80" y1="148" x2="172" y2="148" stroke="rgba(255,255,255,0.35)" stroke-width="3" stroke-linecap="round"/>
          <line x1="44" y1="176" x2="216" y2="176" stroke="#10b981" stroke-width="2.5"/>
          <path d="M 82 232 Q 106 206, 122 228 T 174 216" fill="none" stroke="#34d399" stroke-width="2.8" stroke-linecap="round"/>
        </svg>""",
    },
    "film": {
        "container_id": "loading",
        "bar_id": "fc_load_bar",
        "pct_id": "fc_load_pct",
        "extra_status_id": "status",
        "code": "Fm",
        "title": "The AllCraft Film",
        "tagline": "Multi-Track Non-Linear Video, Color & Audio Suite",
        "accent": "#A855F7",
        "accent_soft": "rgba(168, 85, 247, 0.24)",
        "badge_bg": "#211036",
        "stages": [
            "Initializing Hardware WebCodecs & GPU Scopes…",
            "Loading Lumetri Color Grading & LUT Pipeline…",
            "Preparing Audio Track Mixer & DSP Effects…",
            "Building Multi-Track Timeline & Transitions…",
            "Launching Real-Time Playback Engine…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="fg1" cx="65%" cy="30%" r="70%"><stop offset="0%" stop-color="#c084fc" stop-opacity="0.55"/><stop offset="100%" stop-color="#140f1f" stop-opacity="0"/></radialGradient>
            <linearGradient id="fg2" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#9333ea"/><stop offset="100%" stop-color="#ec4899"/></linearGradient>
          </defs>
          <rect width="260" height="360" fill="#140f1f"/>
          <rect width="260" height="360" fill="url(#fg1)"/>
          <rect x="28" y="108" width="128" height="22" rx="6" fill="url(#fg2)" opacity="0.9"/>
          <rect x="86" y="140" width="144" height="22" rx="6" fill="#7c3aed" opacity="0.75"/>
          <rect x="42" y="172" width="160" height="22" rx="6" fill="#a855f7" opacity="0.55"/>
          <rect x="28" y="216" width="202" height="36" rx="6" fill="rgba(192,132,252,0.05)" stroke="rgba(192,132,252,0.3)"/>
          <path d="M 38 234 L 54 222 L 66 244 L 82 220 L 96 242 L 112 226 L 128 244 L 146 221 L 164 240 L 182 226 L 204 238 L 218 232" fill="none" stroke="#e879f9" stroke-width="2"/>
          <line x1="134" y1="76" x2="134" y2="278" stroke="#fff" stroke-width="2"/>
          <polygon points="127,76 141,76 134,86" fill="#fff"/>
        </svg>""",
    },
    "effect": {
        "container_id": "loading",
        "bar_id": "ec_load_bar",
        "pct_id": "ec_load_pct",
        "extra_status_id": "status",
        "code": "Ef",
        "title": "The AllCraft Effect",
        "tagline": "Motion Graphics, 3D VFX Compositing & Roto Studio",
        "accent": "#F472B6",
        "accent_soft": "rgba(244, 114, 182, 0.24)",
        "badge_bg": "#2D0C20",
        "stages": [
            "Initializing 32-Bit Float GPU Compositor…",
            "Loading Keyframe Speed Graph & JS Expression Engine…",
            "Preparing 3D Camera Tracker, Meshes & Lights…",
            "Loading Roto Brush, Keying & VFX Shaders…",
            "Opening Motion & VFX Studio…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="eg1" cx="55%" cy="32%" r="68%"><stop offset="0%" stop-color="#ec4899" stop-opacity="0.56"/><stop offset="100%" stop-color="#180c16" stop-opacity="0"/></radialGradient>
            <linearGradient id="eg2" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stop-color="#db2777"/><stop offset="100%" stop-color="#f9a8d4"/></linearGradient>
          </defs>
          <rect width="260" height="360" fill="#180c16"/>
          <rect width="260" height="360" fill="url(#eg1)"/>
          <polygon points="130,78 192,114 192,186 130,222 68,186 68,114" fill="rgba(244,114,182,0.08)" stroke="url(#eg2)" stroke-width="2"/>
          <line x1="130" y1="78" x2="130" y2="222" stroke="rgba(249,168,212,0.35)" stroke-width="1.4"/>
          <line x1="68" y1="114" x2="192" y2="186" stroke="rgba(249,168,212,0.35)" stroke-width="1.4"/>
          <path d="M 36 274 C 86 274, 102 224, 130 224 C 158 224, 174 274, 224 274" fill="none" stroke="#f472b6" stroke-width="3"/>
          <rect x="124" y="218" width="12" height="12" transform="rotate(45 130 224)" fill="#fff"/>
          <rect x="52" y="268" width="10" height="10" transform="rotate(45 57 273)" fill="#f472b6"/>
          <rect x="198" y="268" width="10" height="10" transform="rotate(45 203 273)" fill="#f472b6"/>
        </svg>""",
    },
    "sound": {
        "container_id": "soundcraft_loading",
        "bar_id": "sc_load_bar",
        "pct_id": "sc_load_pct",
        "code": "Sd",
        "title": "The AllCraft Sound",
        "tagline": "Multi-Track Audio DAW, MIDI, Score & Mastering",
        "accent": "#2DD4BF",
        "accent_soft": "rgba(45, 212, 191, 0.24)",
        "badge_bg": "#062825",
        "stages": [
            "Initializing Low-Latency WebAudio & DSP Engine…",
            "Loading Multi-Track Mixing Console & Sends…",
            "Preparing MIDI Piano Roll, Sampler & Notation…",
            "Loading EQ, Dynamics, Reverb & Mastering Suite…",
            "Opening Audio Workstation…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="sg1" cx="55%" cy="35%" r="68%"><stop offset="0%" stop-color="#14b8a6" stop-opacity="0.52"/><stop offset="100%" stop-color="#091918" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#091918"/>
          <rect width="260" height="360" fill="url(#sg1)"/>
          <g stroke="#2dd4bf" stroke-width="5" stroke-linecap="round">
            <line x1="42" y1="168" x2="42" y2="192"/><line x1="60" y1="142" x2="60" y2="218"/>
            <line x1="78" y1="112" x2="78" y2="248"/><line x1="96" y1="134" x2="96" y2="226"/>
            <line x1="114" y1="92" x2="114" y2="268"/><line x1="132" y1="124" x2="132" y2="236"/>
            <line x1="150" y1="104" x2="150" y2="256"/><line x1="168" y1="140" x2="168" y2="220"/>
            <line x1="186" y1="118" x2="186" y2="242"/><line x1="204" y1="152" x2="204" y2="208"/>
            <line x1="222" y1="168" x2="222" y2="192"/>
          </g>
          <line x1="28" y1="180" x2="234" y2="180" stroke="rgba(255,255,255,0.28)" stroke-width="1.4"/>
        </svg>""",
    },
    "cad": {
        "container_id": "cadcraft_loading",
        "bar_id": "cd_load_bar",
        "pct_id": "cd_load_pct",
        "code": "Cd",
        "title": "The AllCraft CAD",
        "tagline": "2D/3D Technical Drafting, DWG/DXF & Parametric CAD",
        "accent": "#F87171",
        "accent_soft": "rgba(248, 113, 113, 0.24)",
        "badge_bg": "#2D0C0C",
        "stages": [
            "Initializing Precision 2D/3D CAD Viewport…",
            "Loading Native DWG, DXF & SHX Vector Fonts…",
            "Preparing Object Snaps & Parametric Solver…",
            "Loading Blocks, Layers, LISP & Plotter Engine…",
            "Opening CAD Workstation…",
        ],
        "art_svg": """<svg viewBox="0 0 260 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="cg1" cx="55%" cy="35%" r="68%"><stop offset="0%" stop-color="#ef4444" stop-opacity="0.48"/><stop offset="100%" stop-color="#170f11" stop-opacity="0"/></radialGradient>
          </defs>
          <rect width="260" height="360" fill="#170f11"/>
          <rect width="260" height="360" fill="url(#cg1)"/>
          <g stroke="rgba(255,255,255,0.06)" stroke-width="1">
            <line x1="0" y1="90" x2="260" y2="90"/><line x1="0" y1="150" x2="260" y2="150"/>
            <line x1="0" y1="210" x2="260" y2="210"/><line x1="0" y1="270" x2="260" y2="270"/>
            <line x1="65" y1="0" x2="65" y2="360"/><line x1="130" y1="0" x2="130" y2="360"/><line x1="195" y1="0" x2="195" y2="360"/>
          </g>
          <polygon points="130,84 202,126 202,210 130,252 58,210 58,126" fill="rgba(239,68,68,0.08)" stroke="#f87171" stroke-width="2"/>
          <polyline points="58,126 130,168 202,126" fill="none" stroke="#fca5a5" stroke-width="1.6"/>
          <line x1="130" y1="168" x2="130" y2="252" stroke="#fca5a5" stroke-width="1.6"/>
          <circle cx="130" cy="168" r="24" fill="none" stroke="#38bdf8" stroke-width="1.6" stroke-dasharray="4 3"/>
          <line x1="58" y1="276" x2="202" y2="276" stroke="#f87171" stroke-width="1.5"/>
          <line x1="58" y1="270" x2="58" y2="282" stroke="#f87171" stroke-width="1.5"/>
          <line x1="202" y1="270" x2="202" y2="282" stroke="#f87171" stroke-width="1.5"/>
        </svg>""",
    },
}


class StripCrossOriginAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is None:
            return None
        orig_host = urllib.parse.urlparse(req.full_url).hostname
        new_host = urllib.parse.urlparse(newurl).hostname
        if orig_host != new_host:
            new_req.headers.pop("Authorization", None)
            new_req.unredirected_hdrs.pop("Authorization", None)
        return new_req


OPENER = urllib.request.build_opener(StripCrossOriginAuthRedirectHandler)


def gh_request_json(
    method: str, url: str, token: str, payload: dict | None = None, timeout: int = 60
) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "allcraft-studio-assembler",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with OPENER.open(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def gh_get_json(url: str, token: str) -> dict:
    return gh_request_json("GET", url, token, timeout=60)


def gh_download_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "allcraft-studio-assembler",
        },
    )
    with OPENER.open(req, timeout=180) as resp:
        return resp.read()


def gh_download_release_asset(asset_api_url: str, token: str) -> bytes:
    """Download raw binary bytes from a GitHub Release asset API URL."""
    req = urllib.request.Request(
        asset_api_url,
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "allcraft-studio-assembler",
        },
    )
    with OPENER.open(req, timeout=180) as resp:
        return resp.read()


def get_or_create_cache_release(
    hub_repo: str, token: str, create_if_missing: bool = False
) -> dict | None:
    """Fetch (or create) the rolling 'studio-cache' pre-release on the Studio Hub repo."""
    tag_url = f"https://api.github.com/repos/{hub_repo}/releases/tags/{CACHE_RELEASE_TAG}"
    try:
        return gh_get_json(tag_url, token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print(f"    WARN: [studio-cache] Could not read release '{CACHE_RELEASE_TAG}' (HTTP {exc.code})")
            return None
    except Exception as exc:
        print(f"    WARN: [studio-cache] Release lookup error: {exc}")
        return None

    if not create_if_missing:
        return None

    create_url = f"https://api.github.com/repos/{hub_repo}/releases"
    payload = {
        "tag_name": CACHE_RELEASE_TAG,
        "target_commitish": "main",
        "name": "AllCraft Studio Artifact Cache (Rolling Backup)",
        "body": (
            "Automated rolling backup of the latest WebAssembly build archives for all 15 "
            "AllCraft Studio apps. Protects `allcraft.app` deployments against GitHub Actions' "
            "90-day artifact retention expiry."
        ),
        "draft": False,
        "prerelease": True,
        "make_latest": "false",
    }
    try:
        rel = gh_request_json("POST", create_url, token, payload=payload, timeout=60)
        print(f"    [studio-cache] Created rolling backup release '{CACHE_RELEASE_TAG}' (#{rel.get('id')})")
        return rel
    except Exception as exc:
        print(f"    WARN: [studio-cache] Could not create release '{CACHE_RELEASE_TAG}': {exc}")
        return None


def replace_release_asset(
    hub_repo: str, release: dict, asset_name: str, data: bytes, content_type: str, token: str
) -> dict | None:
    """Upload or atomically replace a named asset on the 'studio-cache' release."""
    release_id = release["id"]
    assets = release.setdefault("assets", [])

    for existing in [a for a in assets if a.get("name") == asset_name]:
        del_url = f"https://api.github.com/repos/{hub_repo}/releases/assets/{existing['id']}"
        try:
            gh_request_json("DELETE", del_url, token, timeout=60)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        assets.remove(existing)

    encoded = urllib.parse.quote(asset_name)
    upload_url = f"https://uploads.github.com/repos/{hub_repo}/releases/{release_id}/assets?name={encoded}"

    def _do_upload() -> dict:
        req = urllib.request.Request(
            upload_url,
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": content_type,
                "Content-Length": str(len(data)),
                "User-Agent": "allcraft-studio-assembler",
            },
            method="POST",
        )
        with OPENER.open(req, timeout=240) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        uploaded = _do_upload()
    except urllib.error.HTTPError as exc:
        if exc.code != 422:
            raise
        fresh = get_or_create_cache_release(hub_repo, token, create_if_missing=False)
        if fresh:
            release["assets"] = fresh.get("assets") or []
            for dup in [a for a in list(release["assets"]) if a.get("name") == asset_name]:
                del_url = f"https://api.github.com/repos/{hub_repo}/releases/assets/{dup['id']}"
                gh_request_json("DELETE", del_url, token, timeout=60)
                release["assets"].remove(dup)
        uploaded = _do_upload()

    release.setdefault("assets", []).append(uploaded)
    return uploaded


def load_cache_manifest(release: dict | None, token: str) -> dict[str, dict]:
    """Read cache-manifest.json from 'studio-cache' release if present."""
    if not release:
        return {}
    for asset in release.get("assets") or []:
        if asset.get("name") == CACHE_MANIFEST_ASSET and asset.get("url"):
            try:
                raw = gh_download_release_asset(asset["url"], token)
                parsed = json.loads(raw.decode("utf-8"))
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:
                print(f"    WARN: [studio-cache] Could not parse {CACHE_MANIFEST_ASSET}: {exc}")
            break
    return {}


def pick_latest_artifact(repo: str, artifact_name: str, branch: str, token: str) -> dict | None:
    encoded_name = urllib.parse.quote(artifact_name)
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?name={encoded_name}&per_page=30"
    data = gh_get_json(url, token)
    artifacts = data.get("artifacts") or []
    valid = [a for a in artifacts if not a.get("expired")]
    if branch:
        branch_matches = [
            a for a in valid if (a.get("workflow_run") or {}).get("head_branch") == branch
        ]
        if branch_matches:
            valid = branch_matches
    if not valid:
        return None
    valid.sort(key=lambda a: a.get("created_at") or "", reverse=True)
    return valid[0]


def strip_wasm_bytes(raw: bytes) -> bytes:
    """Safely strip non-essential custom sections (name, producers, .debug*, reloc.*) in pure Python."""
    try:
        if len(raw) < 8 or raw[:8] != b"\x00asm\x01\x00\x00\x00":
            return raw
        out = bytearray(raw[:8])
        pos = 8
        n = len(raw)
        while pos < n:
            sec_id = raw[pos]
            p = pos + 1
            sec_len = 0
            shift = 0
            while True:
                if p >= n:
                    return raw
                b = raw[p]
                p += 1
                sec_len |= (b & 0x7F) << shift
                if (b & 0x80) == 0:
                    break
                shift += 7
            sec_end = p + sec_len
            if sec_end > n:
                return raw
            drop = False
            if sec_id == 0 and p < sec_end:
                np = p
                name_len = 0
                nshift = 0
                while np < sec_end:
                    nb = raw[np]
                    np += 1
                    name_len |= (nb & 0x7F) << nshift
                    if (nb & 0x80) == 0:
                        break
                    nshift += 7
                if np + name_len <= sec_end:
                    sec_name = raw[np : np + name_len].decode("utf-8", errors="replace")
                    if (
                        sec_name in ("name", "producers")
                        or sec_name.startswith(".debug")
                        or sec_name.startswith("reloc.")
                    ):
                        drop = True
            if not drop:
                out.extend(raw[pos:sec_end])
            pos = sec_end
        return bytes(out)
    except Exception:
        return raw


def build_streaming_loader_script(
    app_id: str,
    mount_path: str,
    bar_id: str,
    pct_id: str,
    chunks_map: dict,
    parts_hash: str,
    first_parts: list[str],
) -> str:
    runtime_base = f"/{mount_path.strip('/')}/"
    manifest_json = json.dumps(chunks_map, separators=(",", ":"))
    preload_links = "\n  ".join(
        f'<link rel="preload" href="{runtime_base}{p}" as="fetch" crossorigin>' for p in first_parts[:3]
    )
    return f"""{preload_links}
  <script id="ac-stream-wasm-loader">
(() => {{
  const chunks = {manifest_json};
  const DEFAULT_DIR = "{runtime_base}";
  const CACHE_NAME = "allcraft-wasm-v2";
  const APP_PREFIX = "https://allcraft.cache/wasm/{app_id}/";
  const BUILD_PREFIX = "https://allcraft.cache/wasm/{app_id}/{parts_hash}/";
  const BAR_ID = "{bar_id}";
  const PCT_ID = "{pct_id}";
  const origFetch = window.fetch.bind(window);
  const eagerReady = new Map();

  if ("caches" in window) {{
    caches.delete("allcraft-wasm-v1").catch(() => {{}});
  }}

  const setProgress = (pct) => {{
    const bar = document.getElementById(BAR_ID);
    const pctEl = document.getElementById(PCT_ID);
    if (bar) bar.style.width = Math.max(3, pct) + "%";
    if (pctEl) pctEl.textContent = pct + "%";
  }};

  const cacheInIdle = (dir, parts, cacheKey) => {{
    if (!("caches" in window) || typeof DecompressionStream === "undefined") return;
    const run = async () => {{
      try {{
        const cache = await caches.open(CACHE_NAME);
        if (await cache.match(cacheKey)) return;
        const bufs = [];
        for (const p of parts) {{
          const r = await origFetch(dir + p, {{ cache: "force-cache" }});
          if (!r.ok) return;
          bufs.push(new Uint8Array(await r.arrayBuffer()));
        }}
        const gz = new ReadableStream({{
          start(c) {{
            for (const b of bufs) c.enqueue(b);
            c.close();
          }}
        }});
        const wasmBlob = await new Response(gz.pipeThrough(new DecompressionStream("gzip"))).blob();
        await cache.put(
          cacheKey,
          new Response(wasmBlob, {{
            status: 200,
            headers: {{
              "Content-Type": "application/wasm",
              "Cross-Origin-Resource-Policy": "same-origin"
            }}
          }})
        );
        const keys = await cache.keys();
        for (const req of keys) {{
          if (req.url.startsWith(APP_PREFIX) && !req.url.startsWith(BUILD_PREFIX)) {{
            cache.delete(req);
          }}
        }}
      }} catch (_) {{}}
    }};
    const schedule = window.requestIdleCallback || ((fn) => setTimeout(fn, 2000));
    schedule(() => setTimeout(run, 1800));
  }};

  const startWasmStream = (fileName, meta, dir = DEFAULT_DIR) => {{
    const cacheKey = BUILD_PREFIX + fileName;
    const promise = (async () => {{
      if ("caches" in window) {{
        try {{
          const cache = await caches.open(CACHE_NAME);
          const hit = await cache.match(cacheKey);
          if (hit) {{
            setProgress(100);
            return hit;
          }}
        }} catch (_) {{}}
      }}

      const parts = meta.parts;
      const totalBytes = meta.total || 0;
      let loadedBytes = 0;

      const CONCURRENCY = 3;
      const started = new Array(parts.length);
      let nextToStart = 0;

      const startPart = (idx) => {{
        if (idx >= parts.length || started[idx]) return started[idx];
        started[idx] = origFetch(dir + parts[idx]).then((res) => {{
          if (!res.ok) throw new Error("Failed to fetch " + parts[idx] + " (" + res.status + ")");
          return res;
        }});
        return started[idx];
      }};

      for (let k = 0; k < Math.min(CONCURRENCY, parts.length); k++) {{
        startPart(nextToStart++);
      }}

      const gzStream = new ReadableStream({{
        async start(controller) {{
          try {{
            for (let i = 0; i < parts.length; i++) {{
              startPart(nextToStart++);
              const res = await startPart(i);
              if (res.body) {{
                const reader = res.body.getReader();
                while (true) {{
                  const {{ done, value }} = await reader.read();
                  if (done) break;
                  loadedBytes += value.byteLength;
                  if (totalBytes > 0) {{
                    setProgress(Math.min(99, Math.round((loadedBytes / totalBytes) * 100)));
                  }}
                  controller.enqueue(value);
                }}
              }} else {{
                const buf = new Uint8Array(await res.arrayBuffer());
                loadedBytes += buf.byteLength;
                if (totalBytes > 0) {{
                  setProgress(Math.min(99, Math.round((loadedBytes / totalBytes) * 100)));
                }}
                controller.enqueue(buf);
              }}
            }}
            setProgress(100);
            controller.close();
            cacheInIdle(dir, parts, cacheKey);
          }} catch (err) {{
            controller.error(err);
          }}
        }}
      }});

      return new Response(gzStream.pipeThrough(new DecompressionStream("gzip")), {{
        status: 200,
        headers: {{
          "Content-Type": "application/wasm",
          "Cross-Origin-Resource-Policy": "same-origin"
        }}
      }});
    }})();
    eagerReady.set(fileName, promise);
    return promise;
  }};

  // Eager start at 0ms in <head> using canonical runtime directory
  for (const [fn, meta] of Object.entries(chunks)) {{
    startWasmStream(fn, meta, DEFAULT_DIR);
  }}

  window.fetch = async (input, init) => {{
    const rawUrl = typeof input === "string" ? input : (input instanceof URL ? input.href : (input && input.url) || "");
    const cleanUrl = rawUrl.split("?")[0].split("#")[0];
    const slash = cleanUrl.lastIndexOf("/");
    const fileName = cleanUrl.substring(slash + 1);
    if (eagerReady.has(fileName)) {{
      const p = eagerReady.get(fileName);
      eagerReady.delete(fileName);
      return p;
    }}
    const meta = chunks[fileName];
    if (!meta) {{
      return origFetch(input, init);
    }}
    return startWasmStream(fileName, meta, DEFAULT_DIR);
  }};
}})();
</script>"""


def repack_and_optimize_app(target_dir: pathlib.Path, app_id: str, mount_path: str) -> dict:
    """Ensure <base href>, strip Wasm symbols, slice into 1.5 MiB streaming chunks, and upgrade index.html's loader script."""
    profile = SPLASH_PROFILES[app_id]
    bar_id = profile["bar_id"]
    pct_id = profile["pct_id"]
    index_path = target_dir / "index.html"
    html = index_path.read_text(encoding="utf-8")

    # CRITICAL FIX: Cloudflare Pages Pretty URLs strips trailing slashes (/runtime/<slug>/ -> 308 /runtime/<slug>).
    # Injecting <base href="/runtime/<slug>/"> ensures all relative JS, Wasm, Worker, and icon paths resolve inside /runtime/<slug>/!
    base_tag = f'<base href="/{mount_path.strip("/")}/">'
    html = re.sub(r"<base\b[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(
        r"(<head\b[^>]*>)",
        r"\1\n  " + base_tag,
        html,
        count=1,
        flags=re.IGNORECASE,
    )

    for sidecar in list(target_dir.glob("*.gz")) + list(target_dir.glob("*.br")):
        sidecar.unlink()

    old_shim_re = re.compile(
        r"<script>\s*\(\(\)\s*=>\s*\{\s*const chunks\s*=\s*(\{.*?\});.*?\}\)\(\);\s*</script>",
        re.DOTALL,
    )
    m = old_shim_re.search(html)

    new_chunks_map: dict[str, dict] = {}
    all_new_parts: list[str] = []
    primary_wasm_key: str | None = None

    if m:
        old_chunks = json.loads(m.group(1))
        for wasm_key, meta in old_chunks.items():
            old_parts = meta.get("parts", []) if isinstance(meta, dict) else list(meta)
            gz_concat = bytearray()
            for p in old_parts:
                p_file = target_dir / p
                if p_file.is_file():
                    gz_concat.extend(p_file.read_bytes())
                    p_file.unlink()
            raw_orig = gzip.decompress(bytes(gz_concat))
            raw_stripped = strip_wasm_bytes(raw_orig)
            recomp = gzip.compress(raw_stripped, compresslevel=9)
            digest = hashlib.sha256(recomp).hexdigest()[:12]
            stem = wasm_key[:-5] if wasm_key.endswith(".wasm") else wasm_key

            parts_list: list[str] = []
            for idx, off in enumerate(range(0, len(recomp), STREAM_CHUNK_BYTES)):
                part_name = f"{stem}-{digest}.wasm.part{idx}"
                (target_dir / part_name).write_bytes(recomp[off : off + STREAM_CHUNK_BYTES])
                parts_list.append(part_name)
                all_new_parts.append(part_name)

            saved_kb = (len(gz_concat) - len(recomp)) / 1024
            print(
                f"    Repacked {wasm_key}: raw {len(raw_orig)/1048576:.1f} -> {len(raw_stripped)/1048576:.1f} MiB | "
                f"gzip {len(recomp)/1048576:.2f} MiB ({saved_kb:+.0f} KiB) across {len(parts_list)} x 1.5 MiB streaming chunks"
            )
            new_chunks_map[wasm_key] = {"parts": parts_list, "total": len(recomp)}
            if primary_wasm_key is None:
                primary_wasm_key = wasm_key
    else:
        for wasm_file in sorted(target_dir.glob("*.wasm")):
            wasm_key = wasm_file.name
            raw_orig = wasm_file.read_bytes()
            raw_stripped = strip_wasm_bytes(raw_orig)
            recomp = gzip.compress(raw_stripped, compresslevel=9)
            digest = hashlib.sha256(recomp).hexdigest()[:12]
            stem = wasm_file.stem
            parts_list = []
            for idx, off in enumerate(range(0, len(recomp), STREAM_CHUNK_BYTES)):
                part_name = f"{stem}-{digest}.wasm.part{idx}"
                (target_dir / part_name).write_bytes(recomp[off : off + STREAM_CHUNK_BYTES])
                parts_list.append(part_name)
                all_new_parts.append(part_name)
            wasm_file.unlink()
            print(
                f"    Chunked raw {wasm_key}: {len(raw_orig)/1048576:.1f} MiB -> "
                f"{len(recomp)/1048576:.2f} MiB gzip across {len(parts_list)} x 1.5 MiB streaming chunks"
            )
            new_chunks_map[wasm_key] = {"parts": parts_list, "total": len(recomp)}
            if primary_wasm_key is None:
                primary_wasm_key = wasm_key

    parts_hash = hashlib.sha256(",".join(all_new_parts).encode("utf-8")).hexdigest()[:12]
    if new_chunks_map:
        html = re.sub(r'<link\b[^>]*\bhref="[^"]*\.wasm"[^>]*>', "", html)
        new_loader = build_streaming_loader_script(
            app_id, mount_path, bar_id, pct_id, new_chunks_map, parts_hash, all_new_parts
        )
        if m:
            m2 = old_shim_re.search(html)
            if m2:
                html = html[: m2.start()] + new_loader + html[m2.end() :]
            else:
                html = re.sub(r"(<base\b[^>]*>)", r"\1\n  " + new_loader, html, count=1, flags=re.IGNORECASE)
        else:
            html = re.sub(r"(<base\b[^>]*>)", r"\1\n  " + new_loader, html, count=1, flags=re.IGNORECASE)

    index_path.write_text(html, encoding="utf-8")

    js_files = [
        f"/{mount_path}/{f.name}"
        for f in sorted(target_dir.glob("*.js"))
        if f.name not in ("sw.js",)
    ]
    cache_key = (
        f"https://allcraft.cache/wasm/{app_id}/{parts_hash}/{primary_wasm_key}"
        if primary_wasm_key and all_new_parts
        else None
    )
    return {
        "js": js_files,
        "parts": [f"/{mount_path}/{p}" for p in all_new_parts],
        "parts_hash": parts_hash,
        "cache_key": cache_key,
    }


def replace_div_by_id(html: str, div_id: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"<div\b[^>]*\bid=(?:\"|')?" + re.escape(div_id) + r"(?:\"|')?(?=[\s>/])[^>]*>",
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        return html, False

    start = m.start()
    tag_re = re.compile(r"</?div\b[^>]*>", re.IGNORECASE)
    depth = 0
    for tm in tag_re.finditer(html, start):
        tok = tm.group(0)
        if tok.startswith("</"):
            depth -= 1
            if depth == 0:
                end = tm.end()
                return html[:start] + replacement + html[end:], True
        elif not tok.endswith("/>"):
            depth += 1
    return html, False


def inject_photoshop_splash(target_dir: pathlib.Path, app_id: str) -> None:
    """Inject the Photoshop-style desktop splash window and update sw.js if present."""
    profile = SPLASH_PROFILES.get(app_id)
    index_path = target_dir / "index.html"
    if not profile or not index_path.is_file():
        return

    html = index_path.read_text(encoding="utf-8")
    cid = profile["container_id"]
    bar_id = profile["bar_id"]
    pct_id = profile["pct_id"]
    extra_status = (
        f'<div id="{profile["extra_status_id"]}" class="ac-err-msg"></div>'
        if profile.get("extra_status_id")
        else ""
    )
    extra_html = profile.get("extra_html", "")
    stages_json = json.dumps(profile["stages"])

    splash_css = f"""<style id="ac-ps-splash-style">
#{cid} {{
  position: fixed !important; inset: 0 !important; z-index: 9999 !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  padding: 20px !important; background: radial-gradient(circle at 50% 35%, #23252b 0%, #141519 100%) !important;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  pointer-events: auto !important; user-select: none !important;
}}
.ac-ps-card {{
  position: relative; width: min(650px, 100%); min-height: 360px;
  display: grid; grid-template-columns: 1.28fr 0.92fr;
  background: #1c1d22; border-radius: 18px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.10);
  box-shadow: 0 32px 90px rgba(0,0,0,0.72), 0 0 0 1px rgba(0,0,0,0.5);
  animation: acSplashIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes acSplashIn {{
  from {{ opacity: 0; transform: scale(0.97) translateY(6px); }}
  to {{ opacity: 1; transform: scale(1) translateY(0); }}
}}
.ac-ps-left {{
  padding: 32px 30px 28px; display: flex; flex-direction: column; justify-content: space-between; text-align: left;
}}
.ac-ps-brand-row {{ display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }}
.ac-ps-monogram {{
  width: 54px; height: 54px; border-radius: 13px; background: {profile["badge_bg"]};
  border: 2px solid {profile["accent"]}; box-shadow: 0 8px 24px {profile["accent_soft"]};
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; letter-spacing: -0.03em; color: {profile["accent"]};
}}
.ac-ps-suite {{
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #8b92a5; margin-bottom: 3px;
}}
.ac-ps-title {{ margin: 0; font-size: 23px; font-weight: 800; letter-spacing: -0.02em; color: #f8fafc; line-height: 1.15; }}
.ac-ps-tagline {{ margin: 0 0 18px; font-size: 13.5px; line-height: 1.5; color: #9ca3af; }}
.ac-ps-pills {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }}
.ac-ps-pill {{
  font-size: 11px; font-weight: 600; padding: 4px 9px; border-radius: 6px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07); color: #cbd5e1;
}}
.ac-ps-status-wrap {{ margin-top: auto; }}
.ac-ps-status-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 9px; }}
.ac-ps-stage {{ font-size: 12.5px; font-weight: 500; color: #d1d5db; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ac-ps-pct {{ font-size: 12px; font-weight: 700; color: {profile["accent"]}; font-variant-numeric: tabular-nums; flex-shrink: 0; }}
.ac-ps-track {{ width: 100%; height: 4px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; }}
.ac-ps-fill {{
  width: 3%; height: 100%; background: {profile["accent"]}; border-radius: 999px;
  box-shadow: 0 0 12px {profile["accent"]}; transition: width 0.1s ease-out;
}}
.ac-ps-foot {{ margin-top: 14px; font-size: 10.5px; color: #64748b; letter-spacing: 0.02em; }}
.ac-ps-right {{ position: relative; background: #121318; border-left: 1px solid rgba(255,255,255,0.06); overflow: hidden; }}
.ac-err-msg:not(:empty) {{ margin-top: 10px; font-size: 12px; color: #ff8a7a; white-space: pre-wrap; max-height: 90px; overflow: auto; }}
@media (max-width: 600px) {{
  .ac-ps-card {{ grid-template-columns: 1fr; min-height: auto; }}
  .ac-ps-right {{ display: none; }}
}}
</style>"""

    splash_div = f"""<div id="{cid}">
  <div class="ac-ps-card">
    <div class="ac-ps-left">
      <div>
        <div class="ac-ps-brand-row">
          <div class="ac-ps-monogram">{profile["code"]}</div>
          <div>
            <div class="ac-ps-suite">The AllCraft Studio &bull; 2026</div>
            <h1 class="ac-ps-title">{profile["title"]}</h1>
          </div>
        </div>
        <p class="ac-ps-tagline">{profile["tagline"]}</p>
        <div class="ac-ps-pills">
          <span class="ac-ps-pill">HTTP/3 Parallel Stream</span>
          <span class="ac-ps-pill">Instant Local Cache</span>
          <span class="ac-ps-pill">Rust + Wasm</span>
        </div>
      </div>
      <div class="ac-ps-status-wrap">
        <div class="ac-ps-status-row">
          <span id="ac_stage_text" class="ac-ps-stage">{profile["stages"][0]}</span>
          <span id="ac_pct_clean" class="ac-ps-pct">Starting…</span>
        </div>
        <div class="ac-ps-track">
          <div id="{bar_id}" class="ac-ps-fill"></div>
        </div>
        <span id="{pct_id}" hidden></span>
        {extra_html}
        {extra_status}
        <div class="ac-ps-foot">&copy; 2026 The AllCraft Studio &middot; Zero Cloud Uploads</div>
      </div>
    </div>
    <div class="ac-ps-right">{profile["art_svg"]}</div>
  </div>
</div>"""

    observer_js = f"""<script>
(() => {{
  const stages = {stages_json};
  const bind = () => {{
    const rawEl = document.getElementById("{pct_id}");
    const stageEl = document.getElementById("ac_stage_text");
    const cleanEl = document.getElementById("ac_pct_clean");
    if (!rawEl || !stageEl || !cleanEl) return;
    const sync = () => {{
      const txt = rawEl.textContent || "";
      const m = txt.match(/(\\d+)\\s*%/);
      if (!m) return;
      const pct = Math.min(100, Math.max(0, parseInt(m[1], 10)));
      cleanEl.textContent = pct + "%";
      if (pct >= 100) {{
        stageEl.textContent = "Opening Workspace…";
      }} else {{
        const idx = Math.min(stages.length - 1, Math.floor((pct / 100) * stages.length));
        stageEl.textContent = stages[idx];
      }}
    }};
    sync();
    new MutationObserver(sync).observe(rawEl, {{ childList: true, characterData: true, subtree: true }});
  }};
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", bind, {{ once: true }});
  }} else {{
    bind();
  }}
}})();
</script>"""

    new_html, ok = replace_div_by_id(html, cid, splash_div)
    if not ok:
        print(f"    WARN: Could not find #{cid} in {app_id}/index.html; splash skipped")
        return

    if "</head>" in new_html:
        new_html = new_html.replace("</head>", splash_css + observer_js + "</head>", 1)
    else:
        new_html = splash_css + observer_js + new_html

    index_path.write_text(new_html, encoding="utf-8")

    sw_path = target_dir / "sw.js"
    if sw_path.is_file():
        rel_files = sorted(
            f.relative_to(target_dir).as_posix()
            for f in target_dir.rglob("*")
            if f.is_file() and f.name != "sw.js"
        )
        file_list = ["./"] + [f"./{f}" for f in rel_files]
        new_ver = hashlib.sha256((new_html + ",".join(rel_files)).encode("utf-8")).hexdigest()[:16]
        sw_txt = sw_path.read_text(encoding="utf-8")
        sw_txt = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "{new_ver}";', sw_txt, count=1)
        sw_txt = re.sub(r"const FILES = \[[^\]]*\];", f"const FILES = {json.dumps(file_list)};", sw_txt, count=1)
        sw_path.write_text(sw_txt, encoding="utf-8")

    print(f"    Injected Splash ({profile['code']}) into dist/{app_id}/index.html")


def write_building_placeholder(target_dir: pathlib.Path, app_name: str) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>Building {app_name} — AllCraft Studio</title>
  <style>
    html, body {{ margin: 0; height: 100%; background: #0b0b0c; color: #f4f4f6; font: 15px/1.55 system-ui, sans-serif; display: flex; align-items: center; justify-content: center; text-align: center; }}
    .box {{ max-width: 460px; padding: 30px; background: #141418; border: 1px solid #282830; }}
    a {{ display: inline-block; margin-top: 18px; padding: 10px 18px; background: #f5f5f7; color: #0b0b0c; text-decoration: none; font-weight: 700; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
  </style>
</head>
<body>
  <div class="box">
    <h2 style="margin:0 0 8px">⚡ Building {app_name}&hellip;</h2>
    <p style="margin:0;color:#9ca3af">First Rust &rarr; WebAssembly build is finishing on GitHub Actions. This page auto-refreshes every 15 seconds and will open automatically once deployed.</p>
    <a href="/">Back to Studio Launcher</a>
  </div>
</body>
</html>
"""
    (target_dir / "index.html").write_text(html, encoding="utf-8")


def normalize_extracted_app(target_dir: pathlib.Path) -> None:
    if not (target_dir / "index.html").is_file():
        candidates = list(target_dir.glob("*/index.html"))
        if len(candidates) == 1:
            nested = candidates[0].parent
            for item in list(nested.iterdir()):
                shutil.move(str(item), str(target_dir / item.name))
            nested.rmdir()

    for meta_file in ("_headers", ".htaccess"):
        p = target_dir / meta_file
        if p.is_file():
            p.unlink()


def main() -> None:
    token = (os.environ.get("STUDIO_PAT") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not token:
        print("ERROR: STUDIO_PAT secret is missing! Add a GitHub PAT with Actions:Read permission.", file=sys.stderr)
        sys.exit(1)

    config = json.loads(APPS_CONFIG.read_text(encoding="utf-8"))
    apps = config.get("apps") or []

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    shutil.copytree(SITE_DIR, DIST_DIR)
    generate_pages.build_all(DIST_DIR)

    cache_release = get_or_create_cache_release(HUB_REPO, token, create_if_missing=False)
    cache_manifest = load_cache_manifest(cache_release, token)
    cache_dirty = False
    synced_backups = 0

    manifest_entries = []
    prefetch_manifest: dict[str, dict] = {}
    for app in apps:
        app_id = app["id"]
        app_name = app.get("name", app_id)
        repo = app["repo"]
        artifact_name = app["artifact_name"]
        branch = app.get("branch", "main")
        mount_path = app["mount_path"].strip("/")
        required = app.get("required", True)
        target_dir = DIST_DIR / mount_path
        cache_asset_name = f"{app_id}.zip"

        print(f"\n==> Fetching '{artifact_name}' from {repo} (branch: {branch})...")
        art = None
        try:
            art = pick_latest_artifact(repo, artifact_name, branch, token)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f"    WARN: Live Actions artifact lookup failed on {repo}: {exc}")

        zip_bytes: bytes | None = None
        artifact_id: int | str = "unknown"
        sha = "unknown"
        artifact_created_at: str | None = None
        artifact_source = "actions-artifact"

        if art:
            dl_url = art["archive_download_url"]
            size_mb = (art.get("size_in_bytes") or 0) / (1024 * 1024)
            sha = (art.get("workflow_run") or {}).get("head_sha", "unknown")
            artifact_id = art["id"]
            artifact_created_at = art.get("created_at")
            print(f"    Downloading artifact #{artifact_id} ({size_mb:.2f} MiB, commit {sha[:7]})...")
            try:
                candidate_bytes = gh_download_bytes(dl_url, token)
                if zipfile.is_zipfile(io.BytesIO(candidate_bytes)):
                    zip_bytes = candidate_bytes
                else:
                    print(f"    WARN: Downloaded artifact #{artifact_id} is not a valid zip; checking '{CACHE_RELEASE_TAG}' backup...")
            except Exception as exc:
                print(f"    WARN: Live download failed for artifact #{artifact_id} ({exc}); checking '{CACHE_RELEASE_TAG}' backup...")

            if zip_bytes is not None:
                cached_entry = cache_manifest.get(app_id) or {}
                existing_asset = next(
                    (
                        a
                        for a in ((cache_release or {}).get("assets") or [])
                        if a.get("name") == cache_asset_name
                    ),
                    None,
                )
                already_current = (
                    existing_asset is not None
                    and cached_entry.get("artifact_id") == artifact_id
                    and existing_asset.get("size") == len(zip_bytes)
                )
                if already_current:
                    print(f"    [studio-cache] Backup already up-to-date ({cache_asset_name}, artifact #{artifact_id})")
                else:
                    if cache_release is None:
                        cache_release = get_or_create_cache_release(
                            HUB_REPO, token, create_if_missing=True
                        )
                    if cache_release is not None:
                        try:
                            replace_release_asset(
                                HUB_REPO,
                                cache_release,
                                cache_asset_name,
                                zip_bytes,
                                "application/zip",
                                token,
                            )
                            cache_manifest[app_id] = {
                                "app_id": app_id,
                                "repo": repo,
                                "artifact_name": artifact_name,
                                "artifact_id": artifact_id,
                                "commit_sha": sha,
                                "artifact_created_at": artifact_created_at,
                                "cached_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "size_bytes": len(zip_bytes),
                                "sha256": hashlib.sha256(zip_bytes).hexdigest(),
                            }
                            cache_dirty = True
                            synced_backups += 1
                            print(
                                f"    [studio-cache] Backed up {cache_asset_name} "
                                f"({len(zip_bytes)/1048576:.2f} MiB, commit {sha[:7]}) to permanent release"
                            )
                        except Exception as exc:
                            print(f"    WARN: [studio-cache] Failed to back up {cache_asset_name}: {exc}")

        if zip_bytes is None:
            if cache_release is None:
                cache_release = get_or_create_cache_release(HUB_REPO, token, create_if_missing=False)
                if cache_release and not cache_manifest:
                    cache_manifest = load_cache_manifest(cache_release, token)

            fallback_asset = next(
                (
                    a
                    for a in ((cache_release or {}).get("assets") or [])
                    if a.get("name") == cache_asset_name and a.get("url")
                ),
                None,
            )
            if fallback_asset is not None:
                try:
                    candidate_bytes = gh_download_release_asset(fallback_asset["url"], token)
                    if zipfile.is_zipfile(io.BytesIO(candidate_bytes)):
                        zip_bytes = candidate_bytes
                        cached_entry = cache_manifest.get(app_id) or {}
                        artifact_id = cached_entry.get("artifact_id", "cached")
                        sha = cached_entry.get("commit_sha", "cached")
                        artifact_created_at = cached_entry.get(
                            "artifact_created_at", fallback_asset.get("updated_at")
                        )
                        artifact_source = "studio-cache-fallback"
                        print(
                            f"    WARN: [studio-cache] Actions artifact expired/unavailable in {repo} — "
                            f"restored {cache_asset_name} ({len(zip_bytes)/1048576:.2f} MiB, commit {str(sha)[:7]}) "
                            f"from permanent '{CACHE_RELEASE_TAG}' release!"
                        )
                except Exception as exc:
                    print(f"    WARN: [studio-cache] Fallback download failed for {cache_asset_name}: {exc}")

        if zip_bytes is None:
            msg = (
                f"No non-expired Actions artifact '{artifact_name}' in {repo} "
                f"and no '{cache_asset_name}' backup found in '{CACHE_RELEASE_TAG}' release."
            )
            if required:
                print(f"ERROR: {msg} Run the build workflow in {repo} once first.", file=sys.stderr)
                sys.exit(1)
            print(f"WARN: {msg} (writing building placeholder for '{app_id}')")
            write_building_placeholder(target_dir, app_name)
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(target_dir)

        normalize_extracted_app(target_dir)
        if not (target_dir / "index.html").is_file():
            print(f"ERROR: dist/{mount_path}/index.html missing after extracting {artifact_name}!", file=sys.stderr)
            sys.exit(1)

        pmeta = repack_and_optimize_app(target_dir, app_id, mount_path)
        inject_photoshop_splash(target_dir, app_id)
        prefetch_manifest[f"/{mount_path}/"] = {
            "js": pmeta["js"],
            "parts": pmeta["parts"],
            "cache_key": pmeta["cache_key"],
        }

        print(f"    Extracted to dist/{mount_path}/ ({sum(1 for _ in target_dir.rglob('*') if _.is_file())} files, index.html verified)")
        manifest_entries.append(
            {
                "id": app_id,
                "name": app_name,
                "repo": repo,
                "mount": f"/{mount_path}/",
                "source": artifact_source,
                "artifact_id": artifact_id,
                "commit_sha": sha,
                "artifact_created_at": artifact_created_at,
            }
        )

    if cache_dirty and cache_release is not None:
        try:
            manifest_bytes = json.dumps(cache_manifest, indent=2, sort_keys=True).encode("utf-8")
            replace_release_asset(
                HUB_REPO,
                cache_release,
                CACHE_MANIFEST_ASSET,
                manifest_bytes,
                "application/json",
                token,
            )
            print(
                f"\n==> [studio-cache] Rolling backup manifest updated "
                f"({synced_backups} archive(s) refreshed across {len(cache_manifest)} cached app(s))."
            )
        except Exception as exc:
            print(f"\nWARN: [studio-cache] Could not update {CACHE_MANIFEST_ASSET}: {exc}")

    (DIST_DIR / "prefetch-manifest.json").write_text(
        json.dumps(prefetch_manifest, separators=(",", ":")), encoding="utf-8"
    )

    oversized = []
    total_bytes = 0
    file_count = 0
    for f in DIST_DIR.rglob("*"):
        if f.is_file():
            sz = f.stat().st_size
            total_bytes += sz
            file_count += 1
            if sz > CF_MAX_FILE_BYTES:
                oversized.append((str(f.relative_to(DIST_DIR)), sz))

    if oversized:
        for rel, sz in oversized:
            print(f"ERROR: {rel} is {sz / (1024 * 1024):.2f} MiB (exceeds Cloudflare 25 MiB limit!)", file=sys.stderr)
        sys.exit(1)

    build_manifest = {
        "assembled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_files": file_count,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "apps": manifest_entries,
    }
    (DIST_DIR / "build-manifest.json").write_text(json.dumps(build_manifest, indent=2), encoding="utf-8")
    print(f"\nSUCCESS: Assembled {len(manifest_entries)} app(s), {file_count} files ({total_bytes / (1024 * 1024):.2f} MiB total) into dist/")


if __name__ == "__main__":
    main()
