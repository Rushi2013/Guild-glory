package com.aurora.floatdeck;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * The foreground app: request the overlay permission, start/stop the service and
 * tweak the same preferences the floating panel edits.
 */
public class MainActivity extends Activity {

    private static final int REQUEST_NOTIFICATIONS = 101;

    private Prefs prefs;
    private TextView overlayStatus;
    private TextView notificationStatus;
    private RoundButton primaryButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = Prefs.get(this);
        setContentView(buildUi());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshState();
    }

    // -------------------------------------------------------------------- ui
    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Theme.BG);
        scroll.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = Theme.dpi(this, 18);
        root.setPadding(pad, pad, pad, Theme.dpi(this, 28));

        root.addView(buildBrand());
        root.addView(buildPermissionCard(), cardParams());
        root.addView(buildPreferencesCard(), cardParams());
        root.addView(buildAboutCard(), cardParams());

        scroll.addView(root, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return scroll;
    }

    private LinearLayout.LayoutParams cardParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = Theme.dpi(this, 14);
        return params;
    }

    private View buildBrand() {
        LinearLayout brand = new LinearLayout(this);
        brand.setOrientation(LinearLayout.HORIZONTAL);
        brand.setGravity(Gravity.CENTER_VERTICAL);
        brand.setPadding(0, Theme.dpi(this, 8), 0, Theme.dpi(this, 4));

        LogoView logo = new LogoView(this);
        brand.addView(logo, new LinearLayout.LayoutParams(
                Theme.dpi(this, 46), Theme.dpi(this, 46)));

        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        titles.addView(label("Aurora Float", 22, Theme.TEXT, TypeWeight.BOLD));
        titles.addView(label("Floating overlay panel  -  v1.0", 12, Theme.MUTED, TypeWeight.NORMAL));

        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        titleParams.setMarginStart(Theme.dpi(this, 14));
        brand.addView(titles, titleParams);
        return brand;
    }

    private View buildPermissionCard() {
        CardView card = new CardView(this);
        card.addView(Rows.sectionLabel(this, "Setup"));

        overlayStatus = statusText();
        card.addView(statusRow("Display over other apps",
                "Draw the bubble above other apps", overlayStatus, "Grant",
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        openOverlaySettings();
                    }
                }));

        notificationStatus = statusText();
        card.addView(statusRow("Notifications",
                "Keeps the running service visible", notificationStatus, "Allow",
                new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        requestNotifications();
                    }
                }));

        primaryButton = new RoundButton(this, "Show floating panel", RoundButton.Style.PRIMARY);
        primaryButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleOverlay();
            }
        });
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Theme.dpi(this, 48));
        buttonParams.topMargin = Theme.dpi(this, 12);
        card.addView(primaryButton, buttonParams);

        TextView hint = label(
                "Tap the bubble to open the panel, drag it to move it, press X to close the panel.",
                11, Theme.MUTED, TypeWeight.NORMAL);
        hint.setLineSpacing(0f, 1.3f);
        LinearLayout.LayoutParams hintParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hintParams.topMargin = Theme.dpi(this, 10);
        card.addView(hint, hintParams);
        return card;
    }

    private View buildPreferencesCard() {
        CardView card = new CardView(this);
        card.addView(Rows.sectionLabel(this, "Bubble and panel"));

        card.addView(Rows.toggleRow(this, "Snap to edge",
                "Bubble jumps to the nearest side", prefs.snapToEdge(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setSnapToEdge(value);
                        OverlayService.refreshPreferences();
                    }
                }, true));

        card.addView(Rows.toggleRow(this, "Haptic feedback",
                "Short buzz when a control is tapped", prefs.haptics(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setHaptics(value);
                        OverlayService.refreshPreferences();
                    }
                }, true));

        card.addView(Rows.toggleRow(this, "Auto-hide panel",
                "Close the panel after 20 s without input", prefs.autoHide(),
                new Rows.OnOff() {
                    @Override
                    public void onChanged(boolean value) {
                        prefs.setAutoHide(value);
                        OverlayService.refreshPreferences();
                    }
                }, true));

        card.addView(Rows.sliderRow(this, "Bubble opacity",
                "How solid the floating logo looks", 40, 100, 5, prefs.bubbleAlpha(), "%",
                new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setBubbleAlpha(value);
                        OverlayService.refreshPreferences();
                    }
                }));

        card.addView(Rows.sliderRow(this, "Panel opacity",
                "Transparency of the open panel", 60, 100, 5, prefs.panelAlpha(), "%",
                new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setPanelAlpha(value);
                        OverlayService.refreshPreferences();
                    }
                }));

        card.addView(Rows.sliderRow(this, "UI refresh rate",
                "How often the panel status line updates", 8, 60, 2, prefs.updateRate(), " Hz",
                new Rows.OnValue() {
                    @Override
                    public void onValue(int value) {
                        prefs.setUpdateRate(value);
                        OverlayService.refreshPreferences();
                    }
                }));
        return card;
    }

    private View buildAboutCard() {
        CardView card = new CardView(this);
        card.addView(Rows.sectionLabel(this, "How it works"));
        card.addView(Rows.bodyText(this,
                "Aurora Float draws its own floating window over other apps using the "
                        + "SYSTEM_ALERT_WINDOW permission - the same mechanism used by chat "
                        + "heads and screen recorders. A foreground service keeps it alive."));
        card.addView(Rows.bodyText(this,
                "The bubble and panel are ordinary Android views: a custom bubble, a "
                        + "rounded card, hand-drawn toggle switches and sliders. Every control "
                        + "here and in the panel edits the same preferences file."));
        card.addView(Rows.bodyText(this,
                "It only renders its own interface. It does not read, control or modify other "
                        + "apps, and it never asks for accessibility or usage-access permissions."));

        TextView footer = label(
                "Built with platform APIs only - no third-party libraries.",
                11, Theme.MUTED, TypeWeight.NORMAL);
        LinearLayout.LayoutParams footerParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        footerParams.topMargin = Theme.dpi(this, 12);
        card.addView(footer, footerParams);
        return card;
    }

    private LinearLayout statusRow(String title, String hint, TextView status,
                                   String actionLabel, View.OnClickListener action) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, Theme.dpi(this, 9), 0, Theme.dpi(this, 9));

        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.addView(label(title, 13, Theme.TEXT, TypeWeight.BOLD));
        column.addView(label(hint, 11, Theme.MUTED, TypeWeight.NORMAL));
        column.addView(status);

        row.addView(column, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        RoundButton button = new RoundButton(this, actionLabel, RoundButton.Style.GHOST);
        button.setOnClickListener(action);
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                Theme.dpi(this, 104), Theme.dpi(this, 36));
        buttonParams.setMarginStart(Theme.dpi(this, 10));
        row.addView(button, buttonParams);
        return row;
    }

    // ---------------------------------------------------------------- state
    private void refreshState() {
        boolean overlayGranted = Settings.canDrawOverlays(this);
        overlayStatus.setText(overlayGranted ? "Granted" : "Not granted");
        overlayStatus.setTextColor(overlayGranted ? Theme.OK : Theme.DANGER);

        boolean notifyGranted = hasNotificationPermission();
        notificationStatus.setText(notifyGranted ? "Granted" : "Not granted");
        notificationStatus.setTextColor(notifyGranted ? Theme.OK : Theme.WARN);

        boolean running = OverlayService.isRunning;
        primaryButton.setText(running ? "Hide floating panel" : "Show floating panel");
        primaryButton.setStyle(running ? RoundButton.Style.DANGER : RoundButton.Style.PRIMARY);
    }

    private void toggleOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            toast("Grant 'Display over other apps' first");
            openOverlaySettings();
            return;
        }
        Intent intent = new Intent(this, OverlayService.class);
        if (OverlayService.isRunning) {
            stopService(intent);
        } else {
            requestNotifications();
            startForegroundService(intent);
        }
        primaryButton.postDelayed(new Runnable() {
            @Override
            public void run() {
                refreshState();
            }
        }, 500);
    }

    private void openOverlaySettings() {
        Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
        try {
            startActivity(intent);
        } catch (Exception exception) {
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION));
            } catch (Exception ignored) {
                toast("Open Settings > Apps > Special access manually");
            }
        }
    }

    private boolean hasNotificationPermission() {
        if (Build.VERSION.SDK_INT < 33) {
            return true;
        }
        return checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestNotifications() {
        if (Build.VERSION.SDK_INT >= 33 && !hasNotificationPermission()) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    REQUEST_NOTIFICATIONS);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        refreshState();
    }

    // --------------------------------------------------------------- helpers
    private enum TypeWeight {
        NORMAL, BOLD
    }

    private TextView label(String text, int sizeSp, int color, TypeWeight weight) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(color);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp);
        view.setTypeface(weight == TypeWeight.BOLD ? Theme.bold() : Theme.regular());
        return view;
    }

    private TextView statusText() {
        TextView view = new TextView(this);
        view.setText("checking");
        view.setTextColor(Theme.MUTED);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        view.setTypeface(Theme.mono());
        view.setPadding(0, Theme.dpi(this, 3), 0, 0);
        return view;
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }
}
