package com.aurora.floatdeck;

import android.content.Context;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/**
 * The floating panel itself: a rounded card with a draggable header, a close (X)
 * button, scrollable settings and a footer with Reset / Hide actions.
 *
 * The panel never talks to the WindowManager directly - it only reports user
 * intent through {@link Callbacks}; the service owns the window.
 */
public class OverlayPanel extends CardView {

    public interface Callbacks {
        void onCloseRequested();

        void onResetRequested();

        void onRebuildRequested();

        void onDrag(float dx, float dy);

        void onSettingsChanged();

        void onInteraction();
    }

    private final TextView statusView;
    private final Callbacks callbacks;

    public OverlayPanel(Context context, Prefs prefs, Callbacks callbacks) {
        super(context, 20f);
        this.callbacks = callbacks;

        setOrientation(VERTICAL);
        setAlpha(prefs.panelAlpha() / 100f);
        int pad = Theme.dpi(context, 14);
        setPadding(pad, pad, pad, pad);

        statusView = new TextView(context);
        statusView.setText("starting");
        statusView.setTextColor(Theme.MUTED);
        statusView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        statusView.setTypeface(Theme.mono());

        addView(buildHeader(context, prefs, callbacks));
        addView(Rows.divider(context));

        ScrollView scroller = new ScrollView(context);
        scroller.setVerticalScrollBarEnabled(false);
        scroller.setOverScrollMode(View.OVER_SCROLL_NEVER);
        LinearLayout body = new LinearLayout(context);
        body.setOrientation(VERTICAL);
        scroller.addView(body, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        buildBody(context, body, prefs, callbacks);
        addView(scroller, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        addView(buildFooter(context, callbacks));
    }

    public void setStatus(String text) {
        statusView.setText(text);
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN && callbacks != null) {
            callbacks.onInteraction();
        }
        return super.dispatchTouchEvent(event);
    }

    // ------------------------------------------------------------------ header
    private View buildHeader(Context context, Prefs prefs, final Callbacks callbacks) {
        LinearLayout header = new LinearLayout(context);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(0, 0, 0, Theme.dpi(context, 10));

        LogoView logo = new LogoView(context);
        header.addView(logo, new LinearLayout.LayoutParams(
                Theme.dpi(context, 30), Theme.dpi(context, 30)));

        LinearLayout titles = new LinearLayout(context);
        titles.setOrientation(LinearLayout.VERTICAL);
        TextView title = new TextView(context);
        title.setText("Aurora Float");
        title.setTextColor(Theme.TEXT);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        title.setTypeface(Theme.medium());
        titles.addView(title);
        titles.addView(statusView);

        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        titleParams.setMarginStart(Theme.dpi(context, 10));
        header.addView(titles, titleParams);

        RoundButton close = new RoundButton(context, "\u2715", RoundButton.Style.SUBTLE);
        close.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        close.setPadding(0, 0, 0, 0);
        close.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                callbacks.onCloseRequested();
            }
        });
        LinearLayout.LayoutParams closeParams = new LinearLayout.LayoutParams(
                Theme.dpi(context, 32), Theme.dpi(context, 32));
        closeParams.setMarginStart(Theme.dpi(context, 6));
        header.addView(close, closeParams);

        // Dragging the header moves the whole window. Touches that land on a
        // clickable child (like the X) are consumed there and never reach this.
        header.setOnTouchListener(new View.OnTouchListener() {
            private float lastX;
            private float lastY;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        lastX = event.getRawX();
                        lastY = event.getRawY();
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        float dx = event.getRawX() - lastX;
                        float dy = event.getRawY() - lastY;
                        lastX = event.getRawX();
                        lastY = event.getRawY();
                        callbacks.onDrag(dx, dy);
                        return true;
                    case MotionEvent.ACTION_UP:
                    case MotionEvent.ACTION_CANCEL:
                        return true;
                    default:
                        return false;
                }
            }
        });

        if (!prefs.reduceMotion()) {
            logo.setAlpha(0.85f);
        }
        return header;
    }

    // ------------------------------------------------------------------- body
    private void buildBody(Context context, LinearLayout body, final Prefs prefs,
                           final Callbacks callbacks) {
        body.addView(Rows.sectionLabel(context, "Performance"));

        body.addView(Rows.toggleRow(context, "Reduce motion",
                "Skip animations and fade-ins", prefs.reduceMotion(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setReduceMotion(value);
                        callbacks.onSettingsChanged();
                    }
                }, false));

        body.addView(Rows.sliderRow(context, "UI refresh rate",
                "How fast the status line updates", 8, 60, 2, prefs.updateRate(), " Hz",
                new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setUpdateRate(value);
                        callbacks.onSettingsChanged();
                    }
                }));

        body.addView(buildPresetRow(context, prefs, callbacks));

        body.addView(Rows.sectionLabel(context, "Overlay"));

        body.addView(Rows.toggleRow(context, "Snap to edge",
                "Bubble jumps to the nearest side", prefs.snapToEdge(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setSnapToEdge(value);
                        callbacks.onSettingsChanged();
                    }
                }, !prefs.reduceMotion()));

        body.addView(Rows.toggleRow(context, "Haptic feedback",
                "Short buzz on every tap", prefs.haptics(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setHaptics(value);
                        callbacks.onSettingsChanged();
                    }
                }, !prefs.reduceMotion()));

        body.addView(Rows.toggleRow(context, "Auto-hide panel",
                "Close it after 20 s without input", prefs.autoHide(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setAutoHide(value);
                        callbacks.onSettingsChanged();
                    }
                }, !prefs.reduceMotion()));

        body.addView(Rows.sliderRow(context, "Bubble opacity", null, 40, 100, 5,
                prefs.bubbleAlpha(), "%", new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setBubbleAlpha(value);
                        callbacks.onSettingsChanged();
                    }
                }));

        body.addView(Rows.sliderRow(context, "Panel opacity", null, 60, 100, 5,
                prefs.panelAlpha(), "%", new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setPanelAlpha(value);
                        callbacks.onSettingsChanged();
                    }
                }));

        body.addView(Rows.divider(context));
        body.addView(Rows.bodyText(context,
                "Drag the header to move this panel. The X and \"Hide panel\" close the "
                        + "panel only; the bubble stays on screen until you stop the overlay "
                        + "from the app."));
    }

    private View buildPresetRow(Context context, final Prefs prefs, final Callbacks callbacks) {
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, Theme.dpi(context, 8), 0, Theme.dpi(context, 2));

        final String[] names = {"Low", "Medium", "High"};
        final RoundButton[] buttons = new RoundButton[names.length];
        for (int i = 0; i < names.length; i++) {
            final String name = names[i];
            RoundButton button = new RoundButton(context, name,
                    name.equals(prefs.preset()) ? RoundButton.Style.PRIMARY : RoundButton.Style.GHOST);
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    0, Theme.dpi(context, 36), 1f);
            if (i > 0) {
                params.setMarginStart(Theme.dpi(context, 8));
            }
            button.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    prefs.applyPreset(name);
                    for (RoundButton other : buttons) {
                        if (other == null) {
                            continue;
                        }
                        other.setStyle(name.contentEquals(other.getText())
                                ? RoundButton.Style.PRIMARY : RoundButton.Style.GHOST);
                    }
                    callbacks.onRebuildRequested();
                }
            });
            row.addView(button, params);
            buttons[i] = button;
        }
        return row;
    }

    // ----------------------------------------------------------------- footer
    private View buildFooter(Context context, final Callbacks callbacks) {
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, Theme.dpi(context, 10), 0, 0);

        RoundButton reset = new RoundButton(context, "Reset", RoundButton.Style.GHOST);
        reset.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                callbacks.onResetRequested();
            }
        });
        RoundButton hide = new RoundButton(context, "Hide panel", RoundButton.Style.DANGER);
        hide.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                callbacks.onCloseRequested();
            }
        });

        LinearLayout.LayoutParams resetParams = new LinearLayout.LayoutParams(
                0, Theme.dpi(context, 40), 1f);
        LinearLayout.LayoutParams hideParams = new LinearLayout.LayoutParams(
                0, Theme.dpi(context, 40), 1f);
        hideParams.setMarginStart(Theme.dpi(context, 8));
        row.addView(reset, resetParams);
        row.addView(hide, hideParams);
        return row;
    }
}
