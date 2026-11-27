package com.mina.takla;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import androidx.annotation.NonNull;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Checks a few times a day whether any color/size has reached the date by which it
 * should be ordered (worked out by the app from safety stock, sales and delivery time),
 * and shows one notification per day listing them.
 */
public class StockWorker extends Worker {
    static final String CHANNEL = "planned-orders";

    public StockWorker(@NonNull Context c, @NonNull WorkerParameters p) { super(c, p); }

    static SharedPreferences prefs(Context c) { return c.getSharedPreferences("stock", Context.MODE_PRIVATE); }

    static void schedule(Context c) {
        PeriodicWorkRequest w = new PeriodicWorkRequest.Builder(StockWorker.class, 6, TimeUnit.HOURS).build();
        WorkManager.getInstance(c).enqueueUniquePeriodicWork("planned-orders", ExistingPeriodicWorkPolicy.KEEP, w);
    }

    @NonNull
    @Override
    public Result doWork() {
        try { check(getApplicationContext()); } catch (Exception ignored) { }
        return Result.success();
    }

    static void check(Context c) throws Exception {
        SharedPreferences p = prefs(c);
        String today = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
        if (today.equals(p.getString("shown", ""))) return;
        JSONArray a = new JSONArray(p.getString("alerts", "[]"));
        int count = 0, xc = 0;
        StringBuilder names = new StringBuilder(), xn = new StringBuilder();
        boolean en0 = "en".equals(prefs(c).getString("lang", "ar"));
        for (int i = 0; i < a.length(); i++) {
            JSONObject o = a.getJSONObject(i);
            if (o.optString("due", "9999").compareTo(today) > 0) continue;
            if ("exp".equals(o.optString("k"))) {
                if (++xc <= 3) { if (xn.length() > 0) xn.append(en0 ? ", " : "، "); xn.append(o.optString("title", "")); }
                continue;
            }
            count++;
            if (count <= 4) {
                if (names.length() > 0) names.append("en".equals(prefs(c).getString("lang", "ar")) ? ", " : "، ");
                names.append(o.optString("title", ""));
            }
        }
        if (xc > 0) notify(c, 2, en0 ? "Expiry dates" : "تواريخ الصلاحية",
                (en0 ? xc + " batch(es) expiring or expired: " : xc + " تشغيلة قربت تنتهي أو انتهت: ") + xn + (xc > 3 ? "…" : ""));
        if (count == 0) { if (xc > 0) p.edit().putString("shown", today).apply(); return; }
        boolean en = "en".equals(prefs(c).getString("lang", "ar"));
        String text = en ? (count == 1 ? "1 item needs ordering: " + names : count + " items need ordering: " + names + (count > 4 ? "…" : ""))
                : (count == 1 ? "صنف يحتاج طلب: " + names : count + " أصناف تحتاج طلب: " + names + (count > 4 ? "…" : ""));
        notify(c, 1, en ? "Planned orders" : "الطلبات المخططة", text);
        p.edit().putString("shown", today).apply();
    }

    static void notify(Context c, int id, String title, String text) {
        NotificationManager m = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (m == null) return;
        Notification.Builder n;
        if (Build.VERSION.SDK_INT >= 26) {
            m.createNotificationChannel(new NotificationChannel(CHANNEL, "الطلبات المخططة", NotificationManager.IMPORTANCE_DEFAULT));
            n = new Notification.Builder(c, CHANNEL);
        } else {
            n = new Notification.Builder(c);
        }
        Intent open = new Intent(c, MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(c, id, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        n.setSmallIcon(android.R.drawable.ic_popup_reminder)
                .setContentTitle(title)
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setContentIntent(pi)
                .setAutoCancel(true);
        try { m.notify(id, n.build()); } catch (SecurityException ignored) { }
    }
}
