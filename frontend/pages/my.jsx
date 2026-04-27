import Link from "next/link";
import { useEffect, useState } from "react";

import { getClientId } from "../lib/clientId";


const API_BASE = process.env.NEXT_PUBLIC_API || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";


function clsx(...xs) {
  return xs.filter(Boolean).join(" ");
}


function Card({ children, className }) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-[rgb(var(--ink-200))] bg-white",
        "shadow-[0_10px_30px_rgba(17,24,39,0.07)]",
        className
      )}
    >
      {children}
    </div>
  );
}


function Badge({ status }) {
  const map = {
    new: { t: "Новое", c: "bg-[rgb(var(--hse-sky))] text-[rgb(var(--hse-blue))]" },
    in_progress: { t: "В работе", c: "bg-yellow-50 text-yellow-700 border border-yellow-200" },
    done: { t: "Закрыто", c: "bg-green-50 text-green-700 border border-green-200" },
  };
  const x = map[status] || { t: status, c: "bg-gray-100 text-gray-700" };
  return <span className={clsx("inline-flex rounded-full px-3 py-1 text-xs font-semibold", x.c)}>{x.t}</span>;
}


async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`${r.status} ${t}`);
  }
  return r.json();
}


async function apiForm(url, formData) {
  const r = await fetch(url, {
    method: "POST",
    body: formData,
  });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`${r.status} ${t}`);
  }
  return r.json();
}


function MessageBubble({ message }) {
  const isStudent = message.sender_role === "student";

  return (
    <div className={clsx("flex", isStudent ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "max-w-[85%] rounded-2xl px-4 py-3 border",
          isStudent
            ? "bg-[rgb(var(--hse-sky))] border-[rgb(var(--hse-sky))]"
            : "bg-white border-[rgb(var(--ink-200))]"
        )}
      >
        <div className="text-xs font-semibold text-[rgb(var(--ink-500))]">
          {isStudent ? "Вы" : "Учебный офис"}
        </div>
        {message.text ? (
          <div className="mt-1 whitespace-pre-line text-sm text-[rgb(var(--ink-800,17_24_39))]">
            {message.text}
          </div>
        ) : null}
        {message.attachments?.length ? (
          <div className="mt-3 space-y-1">
            {message.attachments.map((file) => (
              <a
                key={file.id}
                href={`${API_BASE}${file.url}`}
                target="_blank"
                rel="noreferrer"
                className="block text-sm text-[rgb(var(--hse-blue))] hover:underline"
              >
                {file.original_name}
              </a>
            ))}
          </div>
        ) : null}
        <div className="mt-2 text-[11px] text-[rgb(var(--ink-500))]">
          {message.created_at ? new Date(message.created_at).toLocaleString() : ""}
        </div>
      </div>
    </div>
  );
}


function ThreadCard({ item, clientId, onUpdated }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  function onFilesChange(e) {
    const nextFiles = Array.from(e.target.files || []);
    setFiles((current) => [...current, ...nextFiles]);
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

  async function sendMessage() {
    setErr("");
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("client_id", clientId);
      if (text.trim()) formData.append("text", text.trim());
      for (const file of files) formData.append("files", file);

      const updated = await apiForm(`${API_BASE}/api/incoming/${item.id}/messages`, formData);
      setText("");
      setFiles([]);
      onUpdated(updated);
    } catch (e) {
      setErr(e?.message || "Не удалось отправить сообщение");
    } finally {
      setSaving(false);
    }
  }

  async function closeThread() {
    setErr("");
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("client_id", clientId);
      const updated = await apiForm(`${API_BASE}/api/incoming/${item.id}/close`, formData);
      onUpdated(updated);
    } catch (e) {
      setErr(e?.message || "Не удалось закрыть обращение");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <Badge status={item.status} />
            <div className="text-xs text-[rgb(var(--ink-500))]">
              {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
            </div>
            <div className="text-xs text-[rgb(var(--ink-500))]">
              Сообщений: {(item.messages || []).length}
            </div>
          </div>
          <div className="mt-3 rounded-2xl border border-[rgb(var(--ink-200))] bg-[rgb(var(--ink-100))] px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[rgb(var(--ink-500))]">
              Тема обращения
            </div>
            <div className="mt-1 whitespace-pre-line text-sm text-[rgb(var(--ink-900))]">
              {item.text}
            </div>
          </div>
        </div>
        {item.status !== "done" ? (
          <button
            type="button"
            onClick={closeThread}
            disabled={saving}
            className="rounded-full border border-green-200 bg-green-50 px-3 py-1.5 text-sm font-semibold text-green-700 transition-colors hover:bg-green-100 disabled:opacity-60"
          >
            Информация получена
          </button>
        ) : null}
      </div>

      <div className="mt-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[rgb(var(--ink-500))]">
          История диалога
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {(item.messages || []).map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>

      {item.status !== "done" ? (
        <div className="mt-5 rounded-2xl border border-[rgb(var(--ink-200))] bg-[rgb(var(--ink-100))] p-4">
          <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Новое сообщение</div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="Напишите уточнение или ответ..."
            className="mt-3 w-full rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3 text-sm text-[rgb(var(--ink-900))] outline-none"
          />
          <input
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.webp,.pdf,.doc,.docx,.xls,.xlsx"
            onChange={onFilesChange}
            className="mt-3 block w-full rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3 text-sm text-transparent file:mr-4 file:rounded-full file:border-0 file:bg-[rgb(var(--hse-sky))] file:px-3 file:py-2 file:text-sm file:font-semibold file:text-[rgb(var(--hse-blue))]"
          />
          {files.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {files.map((file) => (
                <button
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  type="button"
                  onClick={() => removeFile(file)}
                  className="rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1 text-xs text-[rgb(var(--ink-700))]"
                >
                  {file.name} x
                </button>
              ))}
            </div>
          ) : null}
          {err ? <div className="mt-3 text-sm text-red-700">{err}</div> : null}
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={sendMessage}
              disabled={saving || (!text.trim() && files.length === 0)}
              className="rounded-2xl bg-[rgb(var(--hse-blue))] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[rgb(var(--hse-blue2))] disabled:opacity-60"
            >
              Отправить
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-4 text-sm text-green-700">
          Диалог завершён. Если понадобится новый вопрос, создайте новое обращение на главной странице.
        </div>
      )}
    </Card>
  );
}


export default function MyRequestsPage() {
  const [clientId, setClientId] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const cid = getClientId();
      setClientId(cid);
      const data = await apiGet(`${API_BASE}/api/incoming?client_id=${encodeURIComponent(cid)}`);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setErr(e?.message || "Не удалось загрузить обращения");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  function replaceItem(updated) {
    setItems((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
  }

  return (
    <div className="min-h-screen bg-[rgb(var(--ink-100))]">
      <header className="border-b border-[rgb(var(--ink-200))] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <div className="text-xs text-[rgb(var(--ink-500))]">НИУ ВШЭ · учебный офис</div>
            <div className="text-base font-semibold text-[rgb(var(--ink-900))]">Мои обращения</div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm text-[rgb(var(--ink-700))] hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))] transition-colors"
            >
              На главную
            </Link>
            <button
              onClick={load}
              className="rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm font-semibold text-[rgb(var(--ink-700))] hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))] transition-colors"
            >
              Обновить
            </button>
          </div>
        </div>
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Card className="p-6">
          <div className="text-sm text-[rgb(var(--ink-500))]">Ваш идентификатор для сайта</div>
          <div className="mt-1 break-all font-mono text-xs text-[rgb(var(--ink-700))]">{clientId || "—"}</div>
        </Card>

        <div className="mt-6">
          {err ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div> : null}
          {loading ? (
            <div className="mt-4 text-sm text-[rgb(var(--ink-500))]">Загружаю…</div>
          ) : items.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-5 py-6 text-sm text-[rgb(var(--ink-700))]">
              У вас пока нет обращений. Создайте вопрос на главной странице, и здесь появится диалог с учебным офисом.
            </div>
          ) : (
            <div className="mt-6 grid gap-4">
              {items.map((item) => (
                <ThreadCard key={item.id} item={item} clientId={clientId} onUpdated={replaceItem} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
