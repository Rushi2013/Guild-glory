package com.aurora.floatdeck;

import android.content.Context;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Locale;

/**
 * Builders for the repeated row shapes (section label, toggle row, slider row,
 * divider). Both the Activity and the floating panel use these, so the two
 * surfaces stay visually identical and adding a control is a one-liner.
 */
public final class Rows {

    public interface OnOff {
        void onChanged(boolean value);
    }

    public interface OnValue {
        void onValue(int value);
    }

    private Rows() {
    }

    public static TextView sectionLabel(Context context, String text) {
        TextView view = new TextView(context);
        view.setText(text.toUpperCase(Locale.US));
        view.setTextColor(Theme.MUTED);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);
        view.setTypeface(Theme.medium());
        view.setLetterSpacing(0.09f);
        view.setPadding(0, Theme.dpi(context, 14), 0, Theme.dpi(context, 6));
        return view;
    }

    public static View divider(Context context) {
        View view = new View(context);
        view.setBackgroundColor(Theme.BORDER);
        view.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Math.max(1, Theme.dpi(context, 1f))));
        return view;
    }

    public static LinearLayout toggleRow(Context context, String title, String hint,
                                         boolean initial, final OnOff callback, boolean animate) {
        LinearLayout row = baseRow(context);
        row.addView(textColumn(context, title, hint), weightParams());

        final ToggleView toggle = new ToggleView(context, initial, animate);
        toggle.setOnToggleListener(new ToggleView.OnToggle() {
            @Override
            public void onToggle(boolean on) {
                if (callback != null) {
                    callback.onChanged(on);
                }
            }
        });
        LinearLayout.LayoutParams toggleParams =
                new LinearLayout.LayoutParams(Theme.dpi(context, 46), Theme.dpi(context, 26));
        toggleParams.gravity = Gravity.CENTER_VERTICAL;
        toggleParams.setMarginStart(Theme.dpi(context, 12));
        row.addView(toggle, toggleParams);
        return row;
    }

    public static LinearLayout sliderRow(Context context, String title, String hint,
                                         int min, int max, int step, int initial,
                                         String suffix, final OnValue callback) {
        LinearLayout wrap = new LinearLayout(context);
        wrap.setOrientation(LinearLayout.VERTICAL);
        wrap.setPadding(0, Theme.dpi(context, 10), 0, 0);

        LinearLayout head = new LinearLayout(context);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);

        head.addView(textColumn(context, title, hint), weightParams());

        final TextView valueView = new TextView(context);
        final String unit = suffix == null ? "" : suffix;
        valueView.setText(initial + unit);
        valueView.setTextColor(Theme.CYAN);
        valueView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        valueView.setTypeface(Theme.mono());
        LinearLayout.LayoutParams valueParams =
                new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT);
        valueParams.setMarginStart(Theme.dpi(context, 10));
        head.addView(valueView, valueParams);
        wrap.addView(head);

        final SliderView slider = new SliderView(context);
        slider.configure(min, max, step, initial);
        slider.setOnValueListener(new SliderView.OnValue() {
            @Override
            public void onValue(int value) {
                valueView.setText(value + unit);
                if (callback != null) {
                    callback.onValue(value);
                }
            }
        });
        wrap.addView(slider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Theme.dpi(context, 30)));
        return wrap;
    }

    public static TextView bodyText(Context context, String text) {
        TextView view = new TextView(context);
        view.setText(text);
        view.setTextColor(Theme.MUTED);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        view.setLineSpacing(0f, 1.35f);
        view.setPadding(0, Theme.dpi(context, 6), 0, 0);
        return view;
    }

    private static LinearLayout baseRow(Context context) {
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, Theme.dpi(context, 7), 0, Theme.dpi(context, 7));
        return row;
    }

    private static LinearLayout textColumn(Context context, String title, String hint) {
        LinearLayout column = new LinearLayout(context);
        column.setOrientation(LinearLayout.VERTICAL);

        TextView titleView = new TextView(context);
        titleView.setText(title);
        titleView.setTextColor(Theme.TEXT);
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        titleView.setTypeface(Theme.medium());
        column.addView(titleView);

        if (hint != null && hint.length() > 0) {
            TextView hintView = new TextView(context);
            hintView.setText(hint);
            hintView.setTextColor(Theme.MUTED);
            hintView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
            column.addView(hintView);
        }
        return column;
    }

    private static LinearLayout.LayoutParams weightParams() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }
}
