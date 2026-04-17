import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";

const API_BASE = process.env.NEXT_PUBLIC_API ?? process.env.NEXT_PUBLIC_API_BASE ?? "";

/* ---------- utils ---------- */

function fmtDate(dt) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return "";
  }
}

function clip(s, n) {
  const t = (s || "").trim();
  if (t.length <= n) return t;
  return t.slice(0, n - 1).trim() + "…";
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

    if (!exists) {
      merged.push(file);
    }
  }

  return merged;
}

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

/* ---------- UI atoms ---------- */

function StatusPill({ status }) {
  const map = {
    new: {
      bg: THEME.sky,
      bd: THEME.sky,
      tx: THEME.blue,
      label: "Новое",
    },
    in_progress: {
      bg: THEME.warningBg,
      bd: THEME.warningBorder,
      tx: THEME.warningText,
      label: "В работе",
    },
    done: {
      bg: THEME.successBg,
      bd: THEME.successBorder,
      tx: THEME.successText,
      label: "Отвечено",
    },
  };

  const s =
    map[status] ||
    { bg: THEME.ink100, bd: THEME.ink200, tx: THEME.ink700, label: status };

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

/* ---------- page ---------- */

export default function AdminIncomingPage() {
  const router = useRouter();

  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [tab, setTab] = useState("all"); // all | new | in_progress | done
  const [loading, setLoading] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [err, setErr] = useState("");
  const [email, setEmail] = useState("admin@uni.local");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(null);

  async function markInProgress(id) {
    setErr("");
    try {
      const updated = await patchIncoming(id, { status: "in_progress" });
      setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
    } catch (e) {
      if (e?.status === 401) {
        handleLogout("Сессия истекла. Войдите снова.");
        return;
      }
      setErr(e?.message || "Не удалось взять в работу");
    }
  }

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
      const data = JSON.parse(t);
      setItems(Array.isArray(data) ? data : []);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function patchIncoming(id, payload, files = []) {
    const formData = new FormData();

    if (payload.status) formData.append("status", payload.status);
    if (payload.comment) formData.append("comment", payload.comment);
    if (payload.answer) formData.append("answer", payload.answer);

    for (const file of files) {
      formData.append("files", file);
    }

    const t = await apiText(`${API_BASE}/api/admin/incoming/${id}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    return JSON.parse(t);
  }

  async function createFaq(payload) {
    const t = await apiText(`${API_BASE}/api/admin/faq`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return JSON.parse(t);
  }

  async function answerOnly(id, answer, files = []) {
    setErr("");
    try {
      const updated = await patchIncoming(
        id,
        {
          answer,
          status: "done",
        },
        files
      );
      setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
    } catch (e) {
      if (e?.status === 401) {
        handleLogout("Сессия истекла. Войдите снова.");
        return;
      }
      setErr(e?.message || "Не удалось сохранить ответ");
    }
  }

  async function answerAsFaq(item, answer, files = []) {
    setErr("");
    try {
      const updated = await patchIncoming(
        item.id,
        {
          answer,
          status: "done",
        },
        files
      );

      await createFaq({
        question: clip(item.text, 255),
        short_answer: clip(answer, 380),
        full_answer: answer,
        tags: [],
        synonyms: [],
        faculty_ids: [],
        program_ids: [],
        status: "published",
      });

      setItems((prev) =>
        prev.map((x) => (x.id === item.id ? updated : x))
      );
    } catch (e) {
      if (e?.status === 401) {
        handleLogout("Сессия истекла. Войдите снова.");
        return;
      }
      setErr(e?.message || "Не удалось сохранить как FAQ");
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);

      const t = await apiText(`${API_BASE}/api/admin/login`, {
        method: "POST",
        body: formData,
      });
      const data = JSON.parse(t);

      if (!data?.token) {
        throw new Error("Токен не получен");
      }

      localStorage.setItem("admin_token", data.token);
      setToken(data.token);
    } catch (e) {
      setErr(e?.message || "Не удалось войти");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout(message = "") {
    if (typeof window !== "undefined") {
      localStorage.removeItem("admin_token");
    }
    setToken(null);
    setItems([]);
    setErr(message);
  }

  const filtered = useMemo(() => {
    let arr = items;

    if (tab !== "all") arr = arr.filter((x) => x.status === tab);

    const qq = q.trim().toLowerCase();
    if (qq) {
      arr = arr.filter((x) => {
        const t = `${x.text || ""} ${x.answer || ""} ${x.client_id || ""}`.toLowerCase();
        return t.includes(qq);
      });
    }

    const order = { new: 0, in_progress: 1, done: 2 };
    return [...arr].sort((a, b) => {
      const oa = order[a.status] ?? 9;
      const ob = order[b.status] ?? 9;
      if (oa !== ob) return oa - ob;
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
  }, [items, q, tab]);

  const counters = useMemo(() => {
    const c = { all: items.length, new: 0, in_progress: 0, done: 0 };
    for (const x of items) if (c[x.status] !== undefined) c[x.status]++;
    return c;
  }, [items]);

  if (!authReady) {
    return null;
  }

  if (!token) {
    return (
      <main style={{ minHeight: "100vh", background: THEME.ink100, padding: "64px 16px" }}>
        <div
          style={{
            maxWidth: 520,
            margin: "0 auto",
            padding: 24,
            ...CARD_STYLE,
          }}
        >
          <div style={{ fontSize: 12, color: THEME.ink500 }}>
            НИУ ВШЭ · учебный офис
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, margin: "8px 0 0", color: THEME.ink900 }}>
            Вход в админку
          </h1>
          <div style={{ marginTop: 8, color: THEME.ink500, fontSize: 14 }}>
            Войдите под учетной записью сотрудника, чтобы работать с обращениями.
          </div>

          <form onSubmit={handleLogin} style={{ marginTop: 20, display: "grid", gap: 12 }}>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                border: `1px solid ${THEME.ink200}`,
                outline: "none",
                background: THEME.white,
                color: THEME.ink900,
              }}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Пароль"
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                border: `1px solid ${THEME.ink200}`,
                outline: "none",
                background: THEME.white,
                color: THEME.ink900,
              }}
            />

            {err ? (
              <div
                style={{
                  padding: 12,
                  borderRadius: 14,
                  background: THEME.dangerBg,
                  border: `1px solid ${THEME.dangerBorder}`,
                  color: THEME.dangerText,
                  fontSize: 14,
                }}
              >
                {err}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                border: `1px solid ${THEME.blue}`,
                background: THEME.blue,
                color: THEME.white,
                fontWeight: 800,
                cursor: "pointer",
                opacity: loading ? 0.7 : 1,
              }}
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
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 32 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <div>
          <div style={{ fontSize: 12, color: THEME.ink500 }}>
            НИУ ВШЭ · учебный офис
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: "6px 0 0", color: THEME.ink900 }}>
            Входящие обращения
          </h1>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={load}
            style={{
              padding: "10px 14px",
              borderRadius: 14,
              border: `1px solid ${THEME.ink200}`,
              background: THEME.white,
              color: THEME.ink700,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Обновить
          </button>

          <button
            onClick={() => router.push("/")}
            style={{
              padding: "10px 14px",
              borderRadius: 14,
              border: "1px solid #E4E7EC",
              background: THEME.white,
              color: THEME.ink700,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            На главную
          </button>

          <button
            onClick={() => handleLogout()}
            style={{
              padding: "10px 14px",
              borderRadius: 14,
              border: `1px solid ${THEME.ink200}`,
              background: THEME.white,
              color: THEME.blue,
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Выйти
          </button>
        </div>
      </div>

      <div
        style={{
          padding: 14,
          ...CARD_STYLE,
          marginBottom: 14,
          display: "grid",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Tab active={tab === "all"} onClick={() => setTab("all")}>
            Все ({counters.all})
          </Tab>
          <Tab active={tab === "new"} onClick={() => setTab("new")}>
            Новые ({counters.new})
          </Tab>
          <Tab
            active={tab === "in_progress"}
            onClick={() => setTab("in_progress")}
          >
            В работе ({counters.in_progress})
          </Tab>
          <Tab active={tab === "done"} onClick={() => setTab("done")}>
            Отвечено ({counters.done})
          </Tab>
        </div>

        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Поиск (вопрос / ответ / client_id)…"
          style={{
            padding: "10px 12px",
            borderRadius: 14,
            border: `1px solid ${THEME.ink200}`,
            background: THEME.white,
            color: THEME.ink900,
            outline: "none",
          }}
        />
      </div>

      {err && (
        <div
          style={{
            padding: 12,
            borderRadius: 16,
            background: "#FEF3F2",
            border: `1px solid ${THEME.dangerBorder}`,
            color: THEME.dangerText,
            background: THEME.dangerBg,
            marginBottom: 12,
          }}
        >
          {err}
        </div>
      )}

      <div style={{ display: "grid", gap: 12 }}>
        {filtered.map((x) => (
          <IncomingCard
            key={x.id}
            item={x}
            onAnswer={answerOnly}
            onAnswerAsFaq={answerAsFaq}
            onInProgress={markInProgress}
          />
        ))}

        {!loading && filtered.length === 0 && (
          <div
            style={{
              padding: 18,
              ...CARD_STYLE,
              color: THEME.ink500,
            }}
          >
            Ничего не найдено.
          </div>
        )}
      </div>
      </div>
    </main>
  );
}

/* ---------- card ---------- */

function IncomingCard({ item: x, onAnswer, onAnswerAsFaq, onInProgress }) {
  const [answer, setAnswer] = useState(x.answer || "");
  const [saving, setSaving] = useState(false);
  const [replyFiles, setReplyFiles] = useState([]);

  useEffect(() => {
    setAnswer(x.answer || "");
  }, [x.answer]);

  async function markInProgress() {
    setSaving(true);
    await onInProgress(x.id);
    setSaving(false);
  }

  async function doAnswer() {
    setSaving(true);
    await onAnswer(x.id, answer, replyFiles);
    setReplyFiles([]);
    setSaving(false);
  }

  async function doAnswerAsFaq() {
    setSaving(true);
    await onAnswerAsFaq(x, answer, replyFiles);
    setReplyFiles([]);
    setSaving(false);
  }

  function onReplyFilesChange(e) {
    const nextFiles = Array.from(e.target.files || []);
    setReplyFiles((current) => mergeFiles(current, nextFiles));
    e.target.value = "";
  }

  function removeReplyFile(fileToRemove) {
    setReplyFiles((current) =>
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

  return (
    <div
      style={{
        padding: 16,
        ...CARD_STYLE,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <StatusPill status={x.status} />
          <div style={{ fontSize: 12, color: THEME.ink500 }}>
            {fmtDate(x.created_at)}
          </div>
          <div style={{ fontSize: 12, color: THEME.ink500 }}>
            канал: {x.channel}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {x.status === "new" && (
            <button
              onClick={markInProgress}
              disabled={saving}
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
          )}

          <button
            onClick={doAnswer}
            disabled={saving || !answer.trim()}
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              border: `1px solid ${THEME.blue}`,
              background: THEME.blue,
              color: THEME.white,
              fontWeight: 900,
              cursor: "pointer",
              opacity: saving || !answer.trim() ? 0.6 : 1,
            }}
          >
            Ответить
          </button>

          <button
            onClick={doAnswerAsFaq}
            disabled={saving || !answer.trim()}
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              border: `1px solid ${THEME.blue2}`,
              background: THEME.blue2,
              color: THEME.white,
              fontWeight: 900,
              cursor: "pointer",
              opacity: saving || !answer.trim() ? 0.6 : 1,
            }}
          >
            Ответить как FAQ
          </button>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900, marginBottom: 6 }}>Вопрос</div>
        <div style={{ whiteSpace: "pre-line", color: THEME.ink700 }}>
          {x.text}
        </div>
      </div>

      {x.attachments?.some((a) => a.uploader_role === "student") && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 900, marginBottom: 6 }}>Файлы студента</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {x.attachments
              .filter((a) => a.uploader_role === "student")
              .map((file) => (
                <li key={file.id} style={{ marginBottom: 4 }}>
                  <a
                    href={`${API_BASE}${file.url}`}
                    target="_blank"
                    rel="noreferrer"
            style={{ color: THEME.blue, textDecoration: "none" }}
                  >
                    {file.original_name}
                  </a>
                </li>
              ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900, marginBottom: 6 }}>Ответ</div>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={4}
          placeholder="Введите ответ студенту…"
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
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 900, marginBottom: 6 }}>Файлы к ответу</div>
        <input
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.webp,.pdf,.doc,.docx,.xls,.xlsx"
          onChange={onReplyFilesChange}
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 14,
            border: `1px solid ${THEME.ink200}`,
            background: THEME.white,
            color: "transparent",
          }}
        />
        {replyFiles.length > 0 && (
          <div style={{ marginTop: 6 }}>
            <div style={{ fontSize: 12, color: THEME.ink500 }}>
              Выбрано файлов: {replyFiles.length}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
              {replyFiles.map((file) => (
                <button
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  type="button"
                  onClick={() => removeReplyFile(file)}
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
          </div>
        )}
      </div>

      {x.attachments?.some((a) => a.uploader_role === "staff") && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 900, marginBottom: 6 }}>Файлы сотрудника</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {x.attachments
              .filter((a) => a.uploader_role === "staff")
              .map((file) => (
                <li key={file.id} style={{ marginBottom: 4 }}>
                  <a
                    href={`${API_BASE}${file.url}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: THEME.blue, textDecoration: "none" }}
                  >
                    {file.original_name}
                  </a>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
