package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.widget.TextView;

/**
 * Flat rounded button with hover/press feedback, drawn with a GradientDrawable
 * instead of a Canvas because a TextView already handles text layout and clicks.
 */
public class RoundButton extends TextView {

    public enum Style {
        PRIMARY, GHOST, SUBTLE, DANGER
    }

    private Style style;
    private boolean pressed;

    public RoundButton(Context context, String text, Style style) {
        super(context);
        this.style = style;
        setText(text);
        setGravity(Gravity.CENTER);
        setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        setTypeface(Theme.medium());
        setPadding(Theme.dpi(context, 14), 0, Theme.dpi(context, 14), 0);
        setClickable(true);
        setFocusable(true);
        applyStyle();
    }

    public void setStyle(Style style) {
        this.style = style;
        applyStyle();
    }

    private void applyStyle() {
        setTextColor(textColor());
        setBackground(drawableFor(pressed));
    }

    private int textColor() {
        switch (style) {
            case PRIMARY:
                return 0xFFFFFFFF;
            case DANGER:
                return 0xFFFF8F88;
            case GHOST:
                return Theme.TEXT;
            case SUBTLE:
            default:
                return 0xFFCFD8E6;
        }
    }

    private Drawable drawableFor(boolean isPressed) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setShape(GradientDrawable.RECTANGLE);
        drawable.setCornerRadius(Theme.dp(getContext(), 12f));
        switch (style) {
            case PRIMARY:
                drawable.setColor(isPressed ? 0xFF6A4BDD : Theme.ACCENT);
                break;
            case DANGER:
                drawable.setColor(isPressed ? 0xFF4A252B : 0xFF3A1D22);
                drawable.setStroke(Math.max(1, Theme.dpi(getContext(), 1f)), 0xFF5A2D34);
                break;
            case GHOST:
                drawable.setColor(isPressed ? Theme.CARD_HI : 0x00000000);
                drawable.setStroke(Math.max(1, Theme.dpi(getContext(), 1f)), Theme.BORDER);
                break;
            case SUBTLE:
            default:
                drawable.setColor(isPressed ? 0xFF232C40 : Theme.CARD_HI);
                break;
        }
        return drawable;
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                pressed = true;
                applyStyle();
                break;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                pressed = false;
                applyStyle();
                break;
            default:
                break;
        }
        return super.onTouchEvent(event);
    }
}
