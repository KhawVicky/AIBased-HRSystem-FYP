// Shows the Header Notifications view.
import { useEffect, useState } from "react";
import { Bell, Mail } from "lucide-react";
import { useNavigate } from "react-router";
import { Button } from "../ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "../ui/hover-card";
import { apiFetch, getStoredUser, NotificationResponse } from "../../lib/api";
import { parseDatabaseDateTime } from "../../lib/date";

// Formats relative time.
function formatRelativeTime(value: string) {
  const createdAt = parseDatabaseDateTime(value);
  if (!createdAt) return "";

  const diffMs = Date.now() - createdAt.getTime();
  if (Number.isNaN(diffMs) || diffMs < 0) return "";
  if (diffMs < 60000) return "now";

  const minutes = Math.max(1, Math.floor(diffMs / 60000));
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

// Renders the Header Notifications component.
export function HeaderNotifications() {
  const navigate = useNavigate();
  const user = getStoredUser();
  const [notifications, setNotifications] = useState<NotificationResponse>({
    items: [],
    preview: [],
    unreadCount: 0,
  });

  useEffect(() => {
    if (!user?.id) return;

    let active = true;
    // Loads notifications.
    const loadNotifications = async () => {
      try {
        const data = await apiFetch<NotificationResponse>(
          `/notifications?userId=${user.id}`,
        );
        if (active) {
          setNotifications(data);
        }
      } catch {
        if (active) {
          setNotifications({ items: [], preview: [], unreadCount: 0 });
        }
      }
    };

    loadNotifications();
    const interval = window.setInterval(loadNotifications, 30000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [user?.id]);

  return (
    <HoverCard openDelay={150}>
      <HoverCardTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/notifications")}
          className="relative h-9 w-9 p-0"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5" />
          {notifications.unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-600 px-1.5 py-0.5 text-[11px] font-bold leading-none text-white">
              {notifications.unreadCount > 99 ? "99+" : notifications.unreadCount}
            </span>
          )}
        </Button>
      </HoverCardTrigger>
      <HoverCardContent align="end" className="w-72 p-0">
        <div className="border-b border-slate-200 px-3 py-2">
          <div className="text-sm font-semibold text-slate-900">Notifications</div>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.preview.length > 0 ? (
            notifications.preview.map((notification) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => navigate("/notifications")}
                className="block w-full border-b border-slate-100 px-3 py-2 text-left hover:bg-slate-50"
              >
                <div className="flex gap-2.5">
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[#003B7A]">
                    {notification.notificationType === "email_sent" ? (
                      <Mail className="h-3.5 w-3.5" />
                    ) : (
                      <Bell className="h-3.5 w-3.5" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-sm font-medium leading-snug text-slate-900">
                        {notification.title}
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <span className="text-[11px] leading-none text-slate-400">
                          {formatRelativeTime(notification.createdAt)}
                        </span>
                        {!notification.isRead && (
                          <span className="h-2 w-2 rounded-full bg-red-600" />
                        )}
                      </div>
                    </div>
                    <div className="mt-1 line-clamp-2 text-xs leading-snug text-slate-600">
                      {notification.message}
                    </div>
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="px-3 py-5 text-center text-xs text-slate-500">
              No notifications
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => navigate("/notifications")}
          className="w-full px-3 py-2.5 text-center text-xs font-semibold text-[#003B7A] hover:bg-slate-50"
        >
          View all notifications
        </button>
      </HoverCardContent>
    </HoverCard>
  );
}
