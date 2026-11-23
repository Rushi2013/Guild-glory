package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;

/**
 * Single source of truth for the palette and the small drawing helpers.
 * Everything in the app reads from here, so re-skinning is a one-file change.
 */
public final class Theme {

    public static final int BG = 0xFF0B0E14;
    public static final int BG_ALT = 0xFF0E121B;
    public static final int CARD = 0xFF141A26;
    public static final int CARD_SOFT = 0xFF0F1521;
    public static final int CARD_HI = 0xFF1B2333;
    public static final int BORDER = 0xFF22293A;
    public static final int TEXT = 0xFFE6EDF3;
    public static final int MUTED = 0xFF8B97AD;
    public static final int ACCENT = 0xFF7C5CFF;
    public static final int ACCENT_HI = 0xFF9A80FF;
    public static final int CYAN = 0xFF35D6E8;
    public static final int OK = 0xFF3FB950;
    public static final int WARN = 0xFFE3B341;
    public static final int DANGER = 0xFFF85149;

    private Theme() {
    }

    public static float dp(Context context, float value) {
        return value * context.getResources().getDisplayMetrics().density;
    }

    public static int dpi(Context context, float value) {
        return Math.round(dp(context, value));
    }

    public static Paint fill(int color) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(color);
        paint.setStyle(Paint.Style.FILL);
        return paint;
    }

    public static Paint stroke(int color, float widthPx) {
        Paint paint = fill(color);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(widthPx);
        return paint;
    }

    public static Typeface regular() {
        return Typeface.create("sans-serif", Typeface.NORMAL);
    }

    public static Typeface medium() {
        return Typeface.create("sans-serif-medium", Typeface.NORMAL);
    }

    public static Typeface bold() {
        return Typeface.create("sans-serif", Typeface.BOLD);
    }

    public static Typeface mono() {
        return Typeface.MONOSPACE;
    }

    /** Linear RGB blend, used by the toggle switch while it animates. */
    public static int blend(int from, int to, float t) {
        float clamped = Math.max(0f, Math.min(1f, t));
        int a = (int) (Color.alpha(from) + (Color.alpha(to) - Color.alpha(from)) * clamped);
        int r = (int) (Color.red(from) + (Color.red(to) - Color.red(from)) * clamped);
        int g = (int) (Color.green(from) + (Color.green(to) - Color.green(from)) * clamped);
        int b = (int) (Color.blue(from) + (Color.blue(to) - Color.blue(from)) * clamped);
        return Color.argb(a, r, g, b);
    }

    public static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
