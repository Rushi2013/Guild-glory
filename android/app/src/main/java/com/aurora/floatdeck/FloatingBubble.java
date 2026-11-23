package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.view.View;

/**
 * The draggable logo that floats above other apps.
 *
 * Theme: a gradient rounded square with an "A" and a cyan status dot that gets a
 * brighter ring while the panel is open. All touches are handled by the service
 * because moving the bubble means updating WindowManager.LayoutParams.
 */
public class FloatingBubble extends View {

    private final Paint bodyPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint dotPaint = Theme.fill(Theme.CYAN);
    private final Paint letterPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint.FontMetrics metrics = new Paint.FontMetrics();

    private LinearGradient gradient;
    private boolean active;
    private boolean touched;

    public FloatingBubble(Context context) {
        super(context);
        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setColor(0x59FFFFFF);
        letterPaint.setColor(0xFFFFFFFF);
        letterPaint.setTypeface(Theme.bold());
        letterPaint.setTextAlign(Paint.Align.CENTER);
        letterPaint.setTextSize(Theme.dp(context, 22f));
    }

    public void setActive(boolean active) {
        this.active = active;
        invalidate();
    }

    public void setTouched(boolean touched) {
        this.touched = touched;
        invalidate();
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        gradient = new LinearGradient(0f, 0f, w, h, Theme.ACCENT, 0xFF22D3EE, Shader.TileMode.CLAMP);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float w = getWidth();
        float h = getHeight();
        if (w <= 0 || h <= 0 || gradient == null) {
            return;
        }
        float inset = Theme.dp(getContext(), touched ? 2f : 4f);
        float radius = w * 0.32f;
        RectF body = new RectF(inset, inset, w - inset, h - inset);

        bodyPaint.setShader(gradient);
        bodyPaint.setAlpha(touched ? 215 : 255);
        canvas.drawRoundRect(body, radius, radius, bodyPaint);

        ringPaint.setStrokeWidth(Theme.dp(getContext(), active ? 2f : 1f));
        ringPaint.setColor(active ? 0x88FFFFFF : 0x55FFFFFF);
        canvas.drawRoundRect(body, radius, radius, ringPaint);

        canvas.drawCircle(body.right - w * 0.24f, body.top + w * 0.24f, w * 0.085f, dotPaint);

        letterPaint.getFontMetrics(metrics);
        float baseline = h / 2f - (metrics.ascent + metrics.descent) / 2f;
        canvas.drawText("A", w / 2f, baseline, letterPaint);
    }
}
