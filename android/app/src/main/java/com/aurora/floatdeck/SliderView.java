package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

/**
 * Draggable slider. Value <-> pixel conversion is the whole widget:
 *
 *   ratio = (value - min) / (max - min)
 *   x     = padding + ratio * (width - 2 * padding)
 */
public class SliderView extends View {

    public interface OnValue {
        void onValue(int value);
    }

    private static final int TRACK = 0xFF242C3D;

    private final Paint trackPaint = Theme.fill(TRACK);
    private final Paint fillPaint = Theme.fill(Theme.ACCENT);
    private final Paint knobPaint = Theme.fill(0xFFFFFFFF);
    private final Paint knobRingPaint = Theme.stroke(Theme.ACCENT, 2f);

    private int min = 0;
    private int max = 100;
    private int step = 1;
    private int value = 50;
    private OnValue listener;

    public SliderView(Context context) {
        super(context);
        setClickable(true);
        setFocusable(true);
        knobRingPaint.setStrokeWidth(Theme.dp(context, 2f));
    }

    public void configure(int min, int max, int step, int value) {
        this.min = min;
        this.max = Math.max(max, min + 1);
        this.step = Math.max(1, step);
        this.value = snap(value);
    }

    public void setOnValueListener(OnValue listener) {
        this.listener = listener;
    }

    public int getValue() {
        return value;
    }

    public void setValue(int newValue, boolean notify) {
        int snapped = snap(newValue);
        if (snapped == value) {
            return;
        }
        value = snapped;
        invalidate();
        if (notify && listener != null) {
            listener.onValue(value);
        }
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int width = MeasureSpec.getSize(widthMeasureSpec);
        if (MeasureSpec.getMode(widthMeasureSpec) == MeasureSpec.UNSPECIFIED) {
            width = Theme.dpi(getContext(), 240);
        }
        setMeasuredDimension(width, Theme.dpi(getContext(), 30));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float w = getWidth();
        float h = getHeight();
        float pad = Theme.dp(getContext(), 10f);
        float thickness = Theme.dp(getContext(), 4f);
        float cy = h / 2f;
        float right = w - pad;
        float x = pad + (right - pad) * ratio();

        RectF track = new RectF(pad, cy - thickness / 2f, right, cy + thickness / 2f);
        canvas.drawRoundRect(track, thickness / 2f, thickness / 2f, trackPaint);

        if (x > pad + 1f) {
            RectF done = new RectF(pad, cy - thickness / 2f, x, cy + thickness / 2f);
            canvas.drawRoundRect(done, thickness / 2f, thickness / 2f, fillPaint);
        }

        float knobRadius = Theme.dp(getContext(), 7f);
        canvas.drawCircle(x, cy, knobRadius, knobPaint);
        canvas.drawCircle(x, cy, knobRadius, knobRingPaint);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_MOVE:
                updateFromTouch(event.getX());
                return true;
            case MotionEvent.ACTION_UP:
                updateFromTouch(event.getX());
                performClick();
                return true;
            default:
                return super.onTouchEvent(event);
        }
    }

    @Override
    public boolean performClick() {
        super.performClick();
        return true;
    }

    private void updateFromTouch(float x) {
        float pad = Theme.dp(getContext(), 10f);
        float usable = Math.max(1f, getWidth() - 2f * pad);
        float ratio = (x - pad) / usable;
        setValue(snap(Math.round(min + Math.max(0f, Math.min(1f, ratio)) * (max - min))), true);
    }

    private int snap(int raw) {
        int clamped = Theme.clamp(raw, min, max);
        int steps = Math.round((clamped - min) / (float) step);
        return Theme.clamp(min + steps * step, min, max);
    }

    private float ratio() {
        return (value - min) / (float) (max - min);
    }
}
