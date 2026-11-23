package com.aurora.floatdeck;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * All persisted state. Every control in the floating panel writes here, so the
 * Activity and the overlay always agree on the current configuration.
 */
public final class Prefs {

    private static final String FILE = "aurora_float";

    private static final String KEY_RATE = "rate";
    private static final String KEY_MOTION = "motion";
    private static final String KEY_HAPTICS = "haptics";
    private static final String KEY_SNAP = "snap";
    private static final String KEY_AUTOHIDE = "autohide";
    private static final String KEY_BUBBLE_ALPHA = "bubble_alpha";
    private static final String KEY_PANEL_ALPHA = "panel_alpha";
    private static final String KEY_PRESET = "preset";
    private static final String KEY_BUBBLE_X = "bubble_x";
    private static final String KEY_BUBBLE_Y = "bubble_y";

    private final SharedPreferences sp;

    private Prefs(SharedPreferences sp) {
        this.sp = sp;
    }

    public static Prefs get(Context context) {
        SharedPreferences sp = context.getApplicationContext()
                .getSharedPreferences(FILE, Context.MODE_PRIVATE);
        return new Prefs(sp);
    }

    public int updateRate() {
        return sp.getInt(KEY_RATE, 30);
    }

    public void setUpdateRate(int value) {
        sp.edit().putInt(KEY_RATE, Theme.clamp(value, 8, 60)).apply();
    }

    public boolean reduceMotion() {
        return sp.getBoolean(KEY_MOTION, false);
    }

    public void setReduceMotion(boolean value) {
        sp.edit().putBoolean(KEY_MOTION, value).apply();
    }

    public boolean haptics() {
        return sp.getBoolean(KEY_HAPTICS, true);
    }

    public void setHaptics(boolean value) {
        sp.edit().putBoolean(KEY_HAPTICS, value).apply();
    }

    public boolean snapToEdge() {
        return sp.getBoolean(KEY_SNAP, true);
    }

    public void setSnapToEdge(boolean value) {
        sp.edit().putBoolean(KEY_SNAP, value).apply();
    }

    public boolean autoHide() {
        return sp.getBoolean(KEY_AUTOHIDE, false);
    }

    public void setAutoHide(boolean value) {
        sp.edit().putBoolean(KEY_AUTOHIDE, value).apply();
    }

    public int bubbleAlpha() {
        return sp.getInt(KEY_BUBBLE_ALPHA, 100);
    }

    public void setBubbleAlpha(int value) {
        sp.edit().putInt(KEY_BUBBLE_ALPHA, Theme.clamp(value, 40, 100)).apply();
    }

    public int panelAlpha() {
        return sp.getInt(KEY_PANEL_ALPHA, 100);
    }

    public void setPanelAlpha(int value) {
        sp.edit().putInt(KEY_PANEL_ALPHA, Theme.clamp(value, 60, 100)).apply();
    }

    public String preset() {
        return sp.getString(KEY_PRESET, "Medium");
    }

    public void setPreset(String value) {
        sp.edit().putString(KEY_PRESET, value).apply();
    }

    public int bubbleX() {
        return sp.getInt(KEY_BUBBLE_X, -1);
    }

    public int bubbleY() {
        return sp.getInt(KEY_BUBBLE_Y, -1);
    }

    public void setBubblePosition(int x, int y) {
        sp.edit().putInt(KEY_BUBBLE_X, x).putInt(KEY_BUBBLE_Y, y).apply();
    }

    /** Presets only touch values that are visible immediately. */
    public void applyPreset(String name) {
        setPreset(name);
        if ("Low".equals(name)) {
            // 16 lands on the slider's step grid (min 8, step 2) so the label and
            // the knob stay in agreement
            setUpdateRate(16);
            setBubbleAlpha(70);
            setPanelAlpha(85);
        } else if ("High".equals(name)) {
            setUpdateRate(60);
            setBubbleAlpha(100);
            setPanelAlpha(100);
        } else {
            setUpdateRate(30);
            setBubbleAlpha(85);
            setPanelAlpha(95);
        }
    }

    public void reset() {
        sp.edit().clear().apply();
    }
}
