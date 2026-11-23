package com.aurora.floatdeck;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.widget.LinearLayout;

/**
 * A rounded, outlined surface that groups related controls.
 *
 * Tkinter needed a Canvas behind a Frame to fake this; on Android a ViewGroup can
 * simply paint its own background before drawing its children.
 */
public class CardView extends LinearLayout {

    private final Paint fillPaint = Theme.fill(Theme.CARD);
    private final Paint borderPaint = Theme.stroke(Theme.BORDER, 1f);
    private final float radius;

    public CardView(Context context) {
        this(context, 16f);
    }

    public CardView(Context context, float radiusDp) {
        super(context);
        this.radius = Theme.dp(context, radiusDp);
        setOrientation(VERTICAL);
        setWillNotDraw(false);
        borderPaint.setStrokeWidth(Math.max(1f, Theme.dp(context, 1f)));
        int pad = Theme.dpi(context, 16);
        setPadding(pad, pad, pad, pad);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float inset = 0.5f;
        RectF bounds = new RectF(inset, inset, getWidth() - inset, getHeight() - inset);
        canvas.drawRoundRect(bounds, radius, radius, fillPaint);
        canvas.drawRoundRect(bounds, radius, radius, borderPaint);
        super.onDraw(canvas);
    }
}
