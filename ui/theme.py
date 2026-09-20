"""
Theme definitions, color palette, and font constants for AutoPix.
Dark AMOLED Translucent Glassmorphism Design System.
Pure Black base (#000000) with frosted glass cards and specular hairline borders.
"""

# ── Base AMOLED ─────────────────────────────────────────────────────────────
BG_COLOR = "#000000"          # True Pitch Black for AMOLED shutoff
SURFACE_GLASS = "#0c0e14"     # Translucent frosted dark glass base
SURFACE_HOVER = "#151924"     # Hover glass state
SURFACE_INSET = "#050608"     # Deep recessed wells for textareas / log consoles
SURFACE_DOCK = "#080a0f"      # Floating dock / footer bar

# ── Borders & Specular Hairlines ─────────────────────────────────────────────
BORDER_GLASS = "#1e2433"      # Subtle hairline glass edge
BORDER_LIGHT = "#2f384f"      # Elevated card border highlight
BORDER_FOCUS = "#4f5f85"      # Focus state border ring

# ── High Contrast Typography ────────────────────────────────────────────────
TEXT_MAIN = "#FFFFFF"         # Apple-grade pure crisp white
TEXT_SECONDARY = "#A1A1AA"    # Muted readable slate
TEXT_TERTIARY = "#71717A"     # Secondary labels
TEXT_MUTED = "#52525B"        # Inactive / timestamps

# ── Accents & Actions ───────────────────────────────────────────────────────
# Primary Solid Action (Apple-grade high contrast)
BTN_PRIMARY_BG = "#FFFFFF"
BTN_PRIMARY_FG = "#000000"
BTN_PRIMARY_HOVER = "#E4E4E7"

# Danger / Abort Action (Deep red glass)
BTN_DANGER_BG = "#2a0c10"
BTN_DANGER_FG = "#FF6B6B"
BTN_DANGER_BORDER = "#5c1d24"
BTN_DANGER_HOVER = "#DC2626"

# Status Badges
STATUS_IDLE_BG = "#131722"
STATUS_IDLE_FG = "#94A3B8"

STATUS_RUN_BG = "#064E3B"
STATUS_RUN_FG = "#34D399"

STATUS_WARN_BG = "#451A03"
STATUS_WARN_FG = "#FBBF24"

STATUS_ERR_BG = "#450A0A"
STATUS_ERR_FG = "#F87171"

# Terminal Syntax Highlights
TERM_INFO = "#60A5FA"
TERM_SUCCESS = "#34D399"
TERM_WARN = "#FBBF24"
TERM_ERROR = "#F87171"
TERM_TEXT = "#E2E8F0"

# ── Fonts ───────────────────────────────────────────────────────────────────
FONT_MAIN = "Segoe UI"
FONT_MONO = "Consolas"
