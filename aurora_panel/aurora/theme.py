"""Colour tokens and type scale for the Aurora Control Panel.

One place to re-skin the whole app. Values are plain RGBA tuples so they can be
handed straight to Kivy ``Color`` instructions or ``Label.color``.
"""

# --- surfaces ---------------------------------------------------------------
BG = (0.035, 0.043, 0.066, 1.0)          # app background
BG_DEEP = (0.020, 0.026, 0.042, 1.0)     # range viewport
CARD = (0.071, 0.082, 0.118, 1.0)        # card fill
CARD_HI = (0.094, 0.108, 0.153, 1.0)     # card hover / inset
BORDER = (0.145, 0.165, 0.235, 1.0)      # 1px hairline
TRACK = (0.121, 0.137, 0.192, 1.0)       # toggle track (off), slider groove

# --- text -------------------------------------------------------------------
TEXT = (0.933, 0.949, 1.0, 1.0)
TEXT_DIM = (0.549, 0.596, 0.694, 1.0)
TEXT_FAINT = (0.373, 0.416, 0.510, 1.0)

# --- accents ----------------------------------------------------------------
ACCENT = (0.220, 0.800, 1.0, 1.0)        # aurora cyan
ACCENT_DIM = (0.137, 0.478, 0.620, 1.0)
VIOLET = (0.545, 0.443, 1.0, 1.0)
LIME = (0.412, 0.941, 0.616, 1.0)
AMBER = (1.0, 0.749, 0.353, 1.0)
DANGER = (1.0, 0.361, 0.447, 1.0)


def fade(color, alpha):
    """Return *color* with a replaced alpha channel."""
    return (color[0], color[1], color[2], alpha)


def mix(a, b, t):
    """Linear blend between two RGBA tuples."""
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))
