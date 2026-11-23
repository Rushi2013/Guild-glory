package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.view.View;

/** The app mark: a gradient rounded square with a cyan status dot. */
public class LogoView extends View {

    private final Paint bodyPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = Theme.stroke(0x33FFFFFF, 1f);
    private final Paint dotPaint = Theme.fill(Theme.CYAN);

    private LinearGradient gradient;

    public LogoView(Context context) {
        super(context);
        ringPaint.setStrokeWidth(Math.max(1f, Theme.dp(context, 1f)));
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
        float inset = w * 0.04f;
        RectF bounds = new RectF(inset, inset, w - inset, h - inset);
        float radius = w * 0.28f;
        bodyPaint.setShader(gradient);
        canvas.drawRoundRect(bounds, radius, radius, bodyPaint);
        canvas.drawRoundRect(bounds, radius, radius, ringPaint);
        canvas.drawCircle(bounds.right - w * 0.26f, bounds.top + w * 0.26f, w * 0.09f, dotPaint);
    }
}
