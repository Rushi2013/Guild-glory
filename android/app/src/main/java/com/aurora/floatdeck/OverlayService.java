package com.aurora.floatdeck;

import android.animation.ValueAnimator;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.content.res.Configuration;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.WindowManager;
import android.widget.Toast;

import java.util.Locale;

/**
 * Owns the two overlay windows:
 *
 *   bubble -> always visible, draggable, snaps to an edge, tap = open the panel
 *   panel  -> the settings card, opened by the bubble, closed with X
 *
 * Everything runs on a foreground service so Android keeps the overlay alive
 * while the user is inside other apps.
 */
public class OverlayService extends Service implements OverlayPanel.Callbacks {

    public static final String ACTION_STOP = "com.aurora.floatdeck.action.STOP";

    /** Lets the Activity show the right button state without binding. */
    public static volatile boolean isRunning;

    private static final String CHANNEL_ID = "overlay";
    private static final int NOTIFICATION_ID = 1001;
    private static final long AUTO_HIDE_MS = 20000L;

    private static OverlayService instance;

    private final Handler handler = new Handler(Looper.getMainLooper());

    private Prefs prefs;
    private WindowManager windowManager;
    private FloatingBubble bubble;
    private WindowManager.LayoutParams bubbleParams;
    private View panel;
    private WindowManager.LayoutParams panelParams;

    private int bubbleSize;
    private int touchSlop;
    private long startedAt;
    private Runnable ticker;
    private Runnable autoHide;

    public static void refreshPreferences() {
        OverlayService service = instance;
        if (service != null) {
            service.applySettings();
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = Prefs.get(this);
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        touchSlop = ViewConfiguration.get(this).getScaledTouchSlop();
        bubbleSize = Theme.dpi(this, 58);
        startedAt = SystemClock.elapsedRealtime();

        createChannelIfNeeded();
        startForegroundCompat();

        if (!Settings.canDrawOverlays(this)) {
            toast("Display over other apps permission is missing");
            stopSelf();
            return;
        }

        instance = this;
        addBubble();
        isRunning = true;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        if (instance == this) {
            instance = null;
        }
        isRunning = false;
        handler.removeCallbacksAndMessages(null);
        hidePanel();
        if (bubble != null && windowManager != null) {
            try {
                windowManager.removeView(bubble);
            } catch (Exception ignored) {
                // the window may already be gone
            }
            bubble = null;
        }
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (bubbleParams != null) {
            bubbleParams.x = Theme.clamp(bubbleParams.x, 0, Math.max(0, screenWidth() - bubbleSize));
            bubbleParams.y = Theme.clamp(bubbleParams.y, 0, Math.max(0, screenHeight() - bubbleSize));
            updateBubbleLayout();
        }
        if (panelParams != null && panel != null) {
            panelParams.x = Theme.clamp(panelParams.x, 0, Math.max(0, screenWidth() - panelParams.width));
            panelParams.y = Theme.clamp(panelParams.y, 0, Math.max(0, screenHeight() - panelParams.height));
            updatePanelLayout();
        }
    }

    // ---------------------------------------------------------------- windows
    private void addBubble() {
        bubble = new FloatingBubble(this);
        bubble.setAlpha(prefs.bubbleAlpha() / 100f);
        bubble.setOnTouchListener(new BubbleTouchListener());

        bubbleParams = new WindowManager.LayoutParams(
                bubbleSize, bubbleSize,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT);
        bubbleParams.gravity = Gravity.TOP | Gravity.START;

        int[] start = initialBubblePosition();
        bubbleParams.x = start[0];
        bubbleParams.y = start[1];

        try {
            windowManager.addView(bubble, bubbleParams);
        } catch (Exception exception) {
            toast("Could not draw the overlay");
            bubble = null;
            stopSelf();
        }
    }

    private int[] initialBubblePosition() {
        int maxX = Math.max(0, screenWidth() - bubbleSize);
        int maxY = Math.max(0, screenHeight() - bubbleSize);
        int x = prefs.bubbleX();
        int y = prefs.bubbleY();
        if (x < 0 || y < 0) {
            x = Theme.dpi(this, 12);
            y = (int) (screenHeight() * 0.42f);
        }
        return new int[]{Theme.clamp(x, 0, maxX), Theme.clamp(y, 0, maxY)};
    }

    private void showPanel() {
        if (panel != null || bubble == null) {
            return;
        }
        OverlayPanel view = new OverlayPanel(this, prefs, this);
        panel = view;

        int width = Math.min(Theme.dpi(this, 312), Math.max(Theme.dpi(this, 240), screenWidth() - Theme.dpi(this, 24)));
        int height = Math.min(Theme.dpi(this, 470), (int) (screenHeight() * 0.76f));

        panelParams = new WindowManager.LayoutParams(
                width, height,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT);
        panelParams.gravity = Gravity.TOP | Gravity.START;
        panelParams.x = Math.max(0, (screenWidth() - width) / 2);
        panelParams.y = Math.max(Theme.dpi(this, 40), (int) (screenHeight() * 0.12f));

        try {
            windowManager.addView(panel, panelParams);
        } catch (Exception exception) {
            panel = null;
            panelParams = null;
            toast("Could not open the panel");
            return;
        }

        bubble.setActive(true);
        startTicker();
        scheduleAutoHide();

        if (!prefs.reduceMotion()) {
            panel.setAlpha(0f);
            panel.animate().alpha(prefs.panelAlpha() / 100f).setDuration(160).start();
        }
    }

    private void hidePanel() {
        stopTicker();
        cancelAutoHide();
        if (panel != null && windowManager != null) {
            try {
                windowManager.removeView(panel);
            } catch (Exception ignored) {
                // already detached
            }
        }
        panel = null;
        panelParams = null;
        if (bubble != null) {
            bubble.setActive(false);
        }
    }

    private void togglePanel() {
        if (panel == null) {
            showPanel();
        } else {
            hidePanel();
        }
    }

    private void updateBubbleLayout() {
        try {
            if (bubble != null && bubbleParams != null) {
                windowManager.updateViewLayout(bubble, bubbleParams);
            }
        } catch (Exception ignored) {
            // window disappeared mid-gesture
        }
    }

    private void updatePanelLayout() {
        try {
            if (panel != null && panelParams != null) {
                windowManager.updateViewLayout(panel, panelParams);
            }
        } catch (Exception ignored) {
            // window disappeared mid-drag
        }
    }

    private int screenWidth() {
        return getResources().getDisplayMetrics().widthPixels;
    }

    private int screenHeight() {
        return getResources().getDisplayMetrics().heightPixels;
    }

    // ------------------------------------------------------------------ touch
    private final class BubbleTouchListener implements View.OnTouchListener {

        private float downX;
        private float downY;
        private int startX;
        private int startY;
        private boolean moved;

        @Override
        public boolean onTouch(View view, MotionEvent event) {
            if (bubbleParams == null) {
                return false;
            }
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downX = event.getRawX();
                    downY = event.getRawY();
                    startX = bubbleParams.x;
                    startY = bubbleParams.y;
                    moved = false;
                    bubble.setTouched(true);
                    return true;

                case MotionEvent.ACTION_MOVE:
                    float dx = event.getRawX() - downX;
                    float dy = event.getRawY() - downY;
                    if (!moved && (Math.abs(dx) > touchSlop || Math.abs(dy) > touchSlop)) {
                        moved = true;
                    }
                    if (moved) {
                        bubbleParams.x = Theme.clamp((int) (startX + dx), 0,
                                Math.max(0, screenWidth() - bubbleSize));
                        bubbleParams.y = Theme.clamp((int) (startY + dy), 0,
                                Math.max(0, screenHeight() - bubbleSize));
                        updateBubbleLayout();
                    }
                    return true;

                case MotionEvent.ACTION_UP:
                    bubble.setTouched(false);
                    if (!moved) {
                        haptic();
                        togglePanel();
                    } else {
                        if (prefs.snapToEdge()) {
                            snapBubble();
                        }
                        prefs.setBubblePosition(bubbleParams.x, bubbleParams.y);
                    }
                    return true;

                case MotionEvent.ACTION_CANCEL:
                    bubble.setTouched(false);
                    return true;

                default:
                    return false;
            }
        }
    }

    private void snapBubble() {
        if (bubbleParams == null) {
            return;
        }
        int margin = Theme.dpi(this, 10);
        int maxX = Math.max(0, screenWidth() - bubbleSize);
        int leftTarget = margin;
        int rightTarget = Math.max(0, maxX - margin);
        int target = (bubbleParams.x + bubbleSize / 2 < screenWidth() / 2) ? leftTarget : rightTarget;
        target = Theme.clamp(target, 0, maxX);

        if (prefs.reduceMotion()) {
            bubbleParams.x = target;
            updateBubbleLayout();
            prefs.setBubblePosition(bubbleParams.x, bubbleParams.y);
            return;
        }

        ValueAnimator animator = ValueAnimator.ofInt(bubbleParams.x, target);
        animator.setDuration(180);
        animator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
            @Override
            public void onAnimationUpdate(ValueAnimator animation) {
                if (bubbleParams == null) {
                    return;
                }
                bubbleParams.x = (Integer) animation.getAnimatedValue();
                updateBubbleLayout();
            }
        });
        animator.start();
        prefs.setBubblePosition(target, bubbleParams.y);
    }

    // -------------------------------------------------------------- callbacks
    @Override
    public void onCloseRequested() {
        haptic();
        hidePanel();
    }

    @Override
    public void onResetRequested() {
        prefs.reset();
        applySettings();
        hidePanel();
        showPanel();
    }

    @Override
    public void onRebuildRequested() {
        hidePanel();
        showPanel();
    }

    @Override
    public void onDrag(float dx, float dy) {
        if (panelParams == null || panel == null) {
            return;
        }
        panelParams.x = Theme.clamp(panelParams.x + Math.round(dx), 0,
                Math.max(0, screenWidth() - panelParams.width));
        panelParams.y = Theme.clamp(panelParams.y + Math.round(dy), 0,
                Math.max(0, screenHeight() - panelParams.height));
        updatePanelLayout();
    }

    @Override
    public void onSettingsChanged() {
        applySettings();
    }

    @Override
    public void onInteraction() {
        scheduleAutoHide();
    }

    private void applySettings() {
        if (bubble != null) {
            bubble.setAlpha(prefs.bubbleAlpha() / 100f);
        }
        if (panel != null) {
            panel.setAlpha(prefs.panelAlpha() / 100f);
        }
        startTicker();
        scheduleAutoHide();
    }

    // ------------------------------------------------------------ status loop
    private void startTicker() {
        stopTicker();
        if (panel == null) {
            return;
        }
        final int intervalMs = Math.max(16, 1000 / Math.max(1, prefs.updateRate()));
        ticker = new Runnable() {
            @Override
            public void run() {
                if (panel instanceof OverlayPanel) {
                    long seconds = (SystemClock.elapsedRealtime() - startedAt) / 1000L;
                    String text = String.format(Locale.US, "running  %02d:%02d",
                            seconds / 60L, seconds % 60L);
                    ((OverlayPanel) panel).setStatus(text);
                }
                handler.postDelayed(this, intervalMs);
            }
        };
        handler.post(ticker);
    }

    private void stopTicker() {
        if (ticker != null) {
            handler.removeCallbacks(ticker);
            ticker = null;
        }
    }

    private void scheduleAutoHide() {
        cancelAutoHide();
        if (panel == null || !prefs.autoHide()) {
            return;
        }
        autoHide = new Runnable() {
            @Override
            public void run() {
                hidePanel();
            }
        };
        handler.postDelayed(autoHide, AUTO_HIDE_MS);
    }

    private void cancelAutoHide() {
        if (autoHide != null) {
            handler.removeCallbacks(autoHide);
            autoHide = null;
        }
    }

    // ------------------------------------------------------------ notification
    private void createChannelIfNeeded() {
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(CHANNEL_ID,
                "Floating panel", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Keeps the floating panel available above other apps");
        channel.setShowBadge(false);
        manager.createNotificationChannel(channel);
    }

    private void startForegroundCompat() {
        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("Aurora Float")
                .setContentText("Floating panel is running")
                .setSmallIcon(R.drawable.ic_stat_aurora)
                .setOngoing(true)
                .setContentIntent(openAppIntent());
        builder.addAction(R.drawable.ic_stat_aurora, "Stop", stopIntent());
        Notification notification = builder.build();

        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private PendingIntent openAppIntent() {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return PendingIntent.getActivity(this, 0, intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private PendingIntent stopIntent() {
        Intent intent = new Intent(this, OverlayService.class);
        intent.setAction(ACTION_STOP);
        return PendingIntent.getService(this, 1, intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    // ------------------------------------------------------------------ misc
    private void haptic() {
        if (prefs.haptics() && bubble != null) {
            bubble.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }
}
