package com.aurora.floatdeck;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;
import android.view.animation.DecelerateInterpolator;

/**
 * iOS-style switch drawn on a Canvas.
 *
 * The knob position is a float in [0, 1]; a ValueAnimator nudges it toward the
 * target and every frame repaints, which is what makes it feel physical instead
 * of snapping.
 */
public class ToggleView extends View {

    public interface OnToggle {
        void onToggle(boolean on);
    }

    private static final int TRACK_OFF = 0xFF2A3346;

    private final Paint trackPaint = Theme.fill(TRACK_OFF);
    private final Paint knobPaint = Theme.fill(0xFFFFFFFF);
    private final DecelerateInterpolator interpolator = new DecelerateInterpolator();

    private boolean on;
    private boolean animate;
    private float position;
    private ValueAnimator animator;
    private OnToggle listener;

    public ToggleView(Context context, boolean initial, boolean animate) {
        super(context);
        this.on = initial;
        this.animate = animate;
        this.position = initial ? 1f : 0f;
        setClickable(true);
        setFocusable(true);
    }

    public void setAnimate(boolean animate) {
        this.animate = animate;
    }

    public void setOnToggleListener(OnToggle listener) {
        this.listener = listener;
    }

    public boolean isOn() {
        return on;
    }

    public void setOn(boolean value, boolean notify) {
        if (on == value) {
            return;
        }
        on = value;
        animateTo(on ? 1f : 0f);
        if (notify && listener != null) {
            listener.onToggle(on);
        }
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        setMeasuredDimension(Theme.dpi(getContext(), 46), Theme.dpi(getContext(), 26));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float w = getWidth();
        float h = getHeight();
        float trackRadius = h / 2f;
        trackPaint.setColor(Theme.blend(TRACK_OFF, Theme.ACCENT, position));
        canvas.drawRoundRect(new RectF(0f, 0f, w, h), trackRadius, trackRadius, trackPaint);

        float pad = Theme.dp(getContext(), 3f);
        float knobDiameter = h - 2f * pad;
        float travel = (w - 2f * pad) - knobDiameter;
        float centerX = pad + knobDiameter / 2f + travel * position;
        canvas.drawCircle(centerX, h / 2f, knobDiameter / 2f, knobPaint);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_UP:
                setOn(!on, true);
                performClick();
                return true;
            case MotionEvent.ACTION_DOWN:
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

    private void animateTo(float target) {
        if (animator != null) {
            animator.cancel();
        }
        if (!animate) {
            position = target;
            invalidate();
            return;
        }
        animator = ValueAnimator.ofFloat(position, target);
        animator.setDuration(160);
        animator.setInterpolator(interpolator);
        animator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                position = (Float) animation.getAnimatedValue();
                invalidate();
            }
        });
        animator.start();
    }
}
