import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";


const API_BASE = process.env.NEXT_PUBLIC_API || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";


const THEME = {
  blue: "rgb(var(--hse-blue))",
  blue2: "rgb(var(--hse-blue2))",
  sky: "rgb(var(--hse-sky))",
  ink900: "rgb(var(--ink-900))",
  ink700: "rgb(var(--ink-700))",
  ink500: "rgb(var(--ink-500))",
  ink200: "rgb(var(--ink-200))",
  ink100: "rgb(var(--ink-100))",
  white: "#FFFFFF",
  dangerBg: "#FEF3F2",
  dangerBorder: "#FDA29B",
  dangerText: "#B42318",
  successBg: "#ECFDF3",
  successBorder: "#ABEFC6",
  successText: "#067647",
  warningBg: "#FFFAEB",
  warningBorder: "#FEDF89",
  warningText: "#B54708",
};


const CARD_STYLE = {
  border: `1px solid ${THEME.ink200}`,
  background: THEME.white,
  borderRadius: 18,
  boxShadow: "0 10px 30px rgba(17,24,39,0.07)",
};


function toYekaterinburgDate(dt) {
  if (!dt) return "";

  try {
    const raw = `${dt}`.trim().replace(/(\.\d{3})\d+/, "$1");
    const hasTimezone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(raw);
    const date = new Date(hasTimezone ? raw : `${raw}+05:00`);
    if (Number.isNaN(date.getTime())) return null;

    return date;
  } catch {
    return null;
  }
}


function fmtDate(dt) {
  const date = toYekaterinburgDate(dt);
  if (!date) return "";

  return date.toLocaleString("ru-RU", { timeZone: "Asia/Yekaterinburg" });
}


function fmtTime(dt) {
  const date = toYekaterinburgDate(dt);
  if (!date) return "";

  return date.toLocaleTimeString("ru-RU", {
    timeZone: "Asia/Yekaterinburg",
    hour: "2-digit",
    minute: "2-digit",
  });
}


function mergeFiles(currentFiles, nextFiles) {
  const merged = [...currentFiles];
  for (const file of nextFiles) {
    const exists = merged.some(
      (item) =>
        item.name === file.name &&
        item.size === file.size &&
        item.lastModified === file.lastModified
    );
    if (!exists) merged.push(file);
  }
  return merged;
}


function StatusPill({ status }) {
  const map = {
    new: { bg: THEME.sky, bd: THEME.sky, tx: THEME.blue, label: "Новое" },
    in_progress: { bg: THEME.warningBg, bd: THEME.warningBorder, tx: THEME.warningText, label: "В работе" },
    done: { bg: THEME.successBg, bd: THEME.successBorder, tx: THEME.successText, label: "Закрыто" },
  };
  const s = map[status] || { bg: THEME.ink100, bd: THEME.ink200, tx: THEME.ink700, label: status };
  return (
    <span
      style={{
        padding: "4px 10px",
        borderRadius: 999,
        background: s.bg,
        border: `1px solid ${s.bd}`,
        color: s.tx,
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {s.label}
    </span>
  );
}


function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      type="button"
      style={{
        padding: "8px 12px",
        borderRadius: 999,
        border: active ? `1px solid ${THEME.blue}` : `1px solid ${THEME.ink200}`,
        background: active ? THEME.sky : THEME.white,
        color: active ? THEME.blue : THEME.ink700,
        fontWeight: 800,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}


function MessageBubble({ message }) {
  const isStudent = message.sender_role === "student";
  return (
    <div style={{ display: "flex", justifyContent: isStudent ? "flex-end" : "flex-start" }}>
      <div
        className="admin-message"
        style={{
          maxWidth: "85%",
          borderRadius: 16,
          padding: 12,
          border: `1px solid ${isStudent ? THEME.sky : THEME.ink200}`,
          background: isStudent ? THEME.sky : THEME.white,
        }}
      >
        <div style={{ fontSize: 12, color: THEME.ink500, fontWeight: 700 }}>
          {isStudent ? "Студент" : "Учебный офис"}
        </div>
        {message.text ? (
          <div style={{ marginTop: 6, whiteSpace: "pre-line", color: THEME.ink700 }}>
            {message.text}
          </div>
        ) : null}
        {message.attachments?.length ? (
          <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
            {message.attachments.map((file) => (
              <a
                key={file.id}
                href={`${API_BASE}${file.url}`}
                target="_blank"
                rel="noreferrer"
                className="admin-file-link"
                style={{ color: THEME.blue, textDecoration: "none", fontSize: 14 }}
              >
                {file.original_name}
              </a>
            ))}
          </div>
        ) : null}
        <div style={{ marginTop: 8, fontSize: 11, color: THEME.ink500 }}>{fmtTime(message.created_at)}</div>
      </div>
    </div>
  );
}


function IncomingCard({ item, token, onUpdated, onTake }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const student = item.student_user;

  async function apiText(url, init) {
    const r = await fetch(url, init);
    const t = await r.text().catch(() => "");
    if (!r.ok) {
      const error = new Error(t || `HTTP ${r.status}`);
      error.status = r.status;
      throw error;
    }
    return t;
  }

  function onFilesChange(e) {
    const nextFiles = Array.from(e.target.files || []);
    setFiles((current) => mergeFiles(current, nextFiles));
    e.target.value = "";
  }

  function removeFile(fileToRemove) {
    setFiles((current) =>
      current.filter(
        (file) =>
          !(
            file.name === fileToRemove.name &&
            file.size === fileToRemove.size &&
            file.lastModified === fileToRemove.lastModified
          )
      )
    );
  }

  async function sendMessage(publishAsFaq = false) {
    setErr("");
    setSaving(true);
    try {
      const formData = new FormData();
      if (text.trim()) formData.append("text", text.trim());
      for (const file of files) formData.append("files", file);
      if (publishAsFaq) formData.append("publish_as_faq", "true");

      const t = await apiText(`${API_BASE}/api/admin/incoming/${item.id}/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      onUpdated(JSON.parse(t));
      setText("");
      setFiles([]);
    } catch (e) {
      setErr(e?.message || "Не удалось отправить сообщение");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-card" style={{ padding: 16, ...CARD_STYLE }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <StatusPill status={item.status} />
          <div style={{ fontSize: 12, color: THEME.ink500 }}>{fmtDate(item.created_at)}</div>
          <div style={{ fontSize: 12, color: THEME.ink500 }}>канал: {item.channel}</div>
        </div>

        <div className="admin-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {item.status === "new" ? (
            <button
              className="mobile-full"
              onClick={() => onTake(item.id)}
              style={{
                padding: "8px 12px",
                borderRadius: 12,
                border: `1px solid ${THEME.ink200}`,
                background: THEME.white,
                color: THEME.ink700,
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              В работу
            </button>
          ) : null}
          <button
            className="mobile-full"
            onClick={() => sendMessage(false)}
            disabled={saving || (!text.trim() && files.length === 0) || item.status === "done"}
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              border: `1px solid ${THEME.blue}`,
              background: THEME.blue,
              color: THEME.white,
              fontWeight: 900,
              cursor: "pointer",
              opacity: saving || (!text.trim() && files.length === 0) || item.status === "done" ? 0.6 : 1,
            }}
          >
            Отправить сообщение
          </button>
          <button
            className="mobile-full"
            onClick={() => sendMessage(true)}
            disabled={saving || !text.trim() || item.status === "done"}
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              border: `1px solid ${THEME.blue2}`,
              background: THEME.blue2,
              color: THEME.white,
              fontWeight: 900,
              cursor: "pointer",
              opacity: saving || !text.trim() || item.status === "done" ? 0.6 : 1,
            }}
          >
            Отправить и сохранить как FAQ
          </button>
        </div>
      </div>

      {student ? (
        <div
          style={{
            marginTop: 12,
            padding: "10px 12px",
            borderRadius: 14,
            border: `1px solid ${THEME.ink200}`,
            background: THEME.ink100,
            display: "flex",
            gap: 10,
            flexWrap: "wrap",
            color: THEME.ink700,
            fontSize: 13,
          }}
        >
          <span style={{ fontWeight: 900, color: THEME.ink900 }}>{student.full_name}</span>
          {student.email ? <span>{student.email}</span> : null}
          {student.faculty ? <span>{student.faculty}</span> : null}
          {student.course ? <span>{student.course} курс</span> : null}
          {student.group_name ? <span>{student.group_name}</span> : null}
          {item.telegram_user_id ? <span>tg: {item.telegram_user_id}</span> : null}
        </div>
      ) : item.telegram_user_id ? (
        <div style={{ marginTop: 12, fontSize: 12, color: THEME.ink500 }}>
          Telegram ID: {item.telegram_user_id}
        </div>
      ) : null}

      <div style={{ marginTop: 14, display: "grid", gap: 12 }}>
        {(item.messages || []).map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>

      {item.status !== "done" ? (
        <div style={{ marginTop: 14, padding: 14, borderRadius: 16, border: `1px solid ${THEME.ink200}`, background: THEME.ink100 }}>
          <div style={{ fontWeight: 900, marginBottom: 8 }}>Новое сообщение</div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="Введите сообщение студенту..."
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: 14,
              border: `1px solid ${THEME.ink200}`,
              resize: "vertical",
              color: THEME.ink900,
              background: THEME.white,
            }}
          />
          <input
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.webp,.pdf,.doc,.docx,.xls,.xlsx"
            onChange={onFilesChange}
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: 14,
              border: `1px solid ${THEME.ink200}`,
              background: THEME.white,
              color: "transparent",
              marginTop: 10,
            }}
          />
          {files.length ? (
            <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 8 }}>
              {files.map((file) => (
                <button
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  type="button"
                  onClick={() => removeFile(file)}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    border: `1px solid ${THEME.ink200}`,
                    background: THEME.white,
                    color: THEME.ink700,
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  {file.name} x
                </button>
              ))}
            </div>
          ) : null}
          {err ? <div style={{ marginTop: 10, color: THEME.dangerText, fontSize: 14 }}>{err}</div> : null}
        </div>
      ) : (
        <div style={{ marginTop: 14, color: THEME.successText, fontSize: 14 }}>
          Диалог закрыт студентом.
        </div>
      )}
    </div>
  );
}


export default function AdminIncomingPage() {
  const router = useRouter();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [err, setErr] = useState("");
  const [email, setEmail] = useState("admin@uni.local");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setToken(localStorage.getItem("admin_token"));
    setAuthReady(true);
  }, []);

  async function apiText(url, init) {
    const r = await fetch(url, init);
    const t = await r.text().catch(() => "");
    if (!r.ok) {
      const error = new Error(t || `HTTP ${r.status}`);
      error.status = r.status;
      throw error;
    }
    return t;
  }

  async function load() {
    if (!token) return;
    setErr("");
    setLoading(true);
    try {
      const t = await apiText(`${API_BASE}/api/admin/incoming`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setItems(JSON.parse(t));
    } catch (e) {
      if (e?.status === 401) {
        handleLogout("Сессия истекла. Войдите снова.");
        return;
      }
      setErr(e?.message || "Не удалось загрузить обращения");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [token]);

  async function markInProgress(id) {
    try {
      const formData = new FormData();
      formData.append("status", "in_progress");
      const t = await apiText(`${API_BASE}/api/admin/incoming/${id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const updated = JSON.parse(t);
      setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
    } catch (e) {
      setErr(e?.message || "Не удалось взять обращение в работу");
    }
  }

  function replaceItem(updated) {
    setItems((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function handleLogin(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);
      const t = await apiText(`${API_BASE}/api/admin/login`, { method: "POST", body: formData });
      const data = JSON.parse(t);
      localStorage.setItem("admin_token", data.token);
      setToken(data.token);
    } catch (e) {
      setErr(e?.message || "Не удалось войти");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout(message = "") {
    if (typeof window !== "undefined") localStorage.removeItem("admin_token");
    setToken(null);
    setItems([]);
    setErr(message);
  }

  const filtered = useMemo(() => {
    let list = items;
    if (tab !== "all") list = list.filter((item) => item.status === tab);
    const qq = q.trim().toLowerCase();
    if (qq) {
      list = list.filter((item) =>
        (item.messages || []).some((message) => `${message.text || ""}`.toLowerCase().includes(qq)) ||
        `${item.text || ""} ${item.client_id || ""} ${item.student_user?.full_name || ""} ${item.student_user?.group_name || ""}`.toLowerCase().includes(qq)
      );
    }
    return [...list].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  }, [items, q, tab]);

  const counters = useMemo(() => {
    const c = { all: items.length, new: 0, in_progress: 0, done: 0 };
    for (const item of items) if (c[item.status] !== undefined) c[item.status] += 1;
    return c;
  }, [items]);

  if (!authReady) return null;

  if (!token) {
    return (
      <main style={{ minHeight: "100vh", background: THEME.ink100, padding: "64px 16px" }}>
        <div className="admin-login-card" style={{ maxWidth: 520, margin: "0 auto", padding: 24, ...CARD_STYLE }}>
          <div style={{ fontSize: 12, color: THEME.ink500 }}>НИУ ВШЭ · учебный офис</div>
          <h1 style={{ fontSize: 28, fontWeight: 800, margin: "8px 0 0", color: THEME.ink900 }}>
            Вход в админку
          </h1>
          <form onSubmit={handleLogin} style={{ marginTop: 20, display: "grid", gap: 12 }}>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              style={{ padding: "12px 14px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white }}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Пароль"
              style={{ padding: "12px 14px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white }}
            />
            {err ? (
              <div style={{ padding: 12, borderRadius: 14, background: THEME.dangerBg, border: `1px solid ${THEME.dangerBorder}`, color: THEME.dangerText, fontSize: 14 }}>
                {err}
              </div>
            ) : null}
            <button
              type="submit"
              disabled={loading}
              style={{ padding: "12px 14px", borderRadius: 14, border: `1px solid ${THEME.blue}`, background: THEME.blue, color: THEME.white, fontWeight: 800, cursor: "pointer" }}
            >
              {loading ? "Входим..." : "Войти"}
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main style={{ minHeight: "100vh", background: THEME.ink100 }}>
      <div className="admin-shell" style={{ maxWidth: 1100, margin: "0 auto", padding: 32 }}>
        <div className="admin-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: THEME.ink500 }}>НИУ ВШЭ · учебный офис</div>
            <h1 style={{ fontSize: 26, fontWeight: 800, margin: "6px 0 0", color: THEME.ink900 }}>Диалоги с обращениями</h1>
          </div>
          <div className="admin-actions" style={{ display: "flex", gap: 10 }}>
            <button onClick={load} style={{ padding: "10px 14px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white, color: THEME.ink700, fontWeight: 700, cursor: "pointer" }}>Обновить</button>
            <button onClick={() => router.push("/")} style={{ padding: "10px 14px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white, color: THEME.ink700, fontWeight: 700, cursor: "pointer" }}>На главную</button>
            <button onClick={() => handleLogout()} style={{ padding: "10px 14px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white, color: THEME.blue, fontWeight: 800, cursor: "pointer" }}>Выйти</button>
          </div>
        </div>

        <div style={{ padding: 14, ...CARD_STYLE, marginBottom: 14, display: "grid", gap: 10 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Tab active={tab === "all"} onClick={() => setTab("all")}>Все ({counters.all})</Tab>
            <Tab active={tab === "new"} onClick={() => setTab("new")}>Новые ({counters.new})</Tab>
            <Tab active={tab === "in_progress"} onClick={() => setTab("in_progress")}>В работе ({counters.in_progress})</Tab>
            <Tab active={tab === "done"} onClick={() => setTab("done")}>Закрытые ({counters.done})</Tab>
          </div>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск по сообщениям, студенту и client_id..."
            style={{ padding: "10px 12px", borderRadius: 14, border: `1px solid ${THEME.ink200}`, background: THEME.white, color: THEME.ink900 }}
          />
        </div>

        {err ? (
          <div style={{ padding: 12, borderRadius: 16, border: `1px solid ${THEME.dangerBorder}`, color: THEME.dangerText, background: THEME.dangerBg, marginBottom: 12 }}>
            {err}
          </div>
        ) : null}

        <div style={{ display: "grid", gap: 12 }}>
          {filtered.map((item) => (
            <IncomingCard key={item.id} item={item} token={token} onUpdated={replaceItem} onTake={markInProgress} />
          ))}
          {!loading && filtered.length === 0 ? (
            <div style={{ padding: 18, ...CARD_STYLE, color: THEME.ink500 }}>Ничего не найдено.</div>
          ) : null}
        </div>
      </div>
    </main>
  );
}
