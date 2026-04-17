import Link from "next/link";
import { useEffect, useState } from "react";
import { getClientId } from "../lib/clientId";

const API_BASE = process.env.NEXT_PUBLIC_API ?? "";

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
    done: { t: "Есть ответ", c: "bg-green-50 text-green-700 border border-green-200" },
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

export default function MyRequestsPage() {
  const [clientId, setClientId] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [lastAnsweredCount, setLastAnsweredCount] = useState(0);

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const cid = getClientId();
      setClientId(cid);

      const data = await apiGet(`${API_BASE}/api/incoming?client_id=${encodeURIComponent(cid)}`);
      setItems(Array.isArray(data) ? data : []);

      const answeredCount = (data || []).filter((x) => x.status === "done").length;
      // простое уведомление: если стало больше done — покажем alert/баннер
      if (!loading && answeredCount > lastAnsweredCount) {
        // можно заменить на красивый toast — позже
        alert("Появился ответ на одно из ваших обращений!");
      }
      setLastAnsweredCount(answeredCount);
    } catch (e) {
      setErr(e?.message || "Не удалось загрузить обращения");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // автообновление, чтобы студент не проверял руками
    const t = setInterval(load, 20000); // раз в 20 сек
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
              className="
                rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm text-[rgb(var(--ink-700))]
                hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                transition-colors
              "
            >
              На главную
            </Link>
            <button
              onClick={load}
              className="
                rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm font-semibold text-[rgb(var(--ink-700))]
                hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                transition-colors
                active:scale-[0.98]
              "
            >
              Обновить
            </button>
          </div>
        </div>
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Card className="p-6">
          <div className="text-sm text-[rgb(var(--ink-500))]">Ваш идентификатор (для связи без логина)</div>
          <div className="mt-1 font-mono text-xs text-[rgb(var(--ink-700))] break-all">{clientId || "—"}</div>
        </Card>

        <div className="mt-6">
          {err ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div>
          ) : null}

          {loading ? (
            <div className="mt-4 text-sm text-[rgb(var(--ink-500))]">Загружаю…</div>
          ) : items.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-5 py-6 text-sm text-[rgb(var(--ink-700))]">
              У вас пока нет обращений. Задайте вопрос на главной странице и отправьте его в учебный офис.
            </div>
          ) : (
            <div className="mt-6 grid gap-3">
              {items.map((x) => (
                <Card key={x.id} className="p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Badge status={x.status} />
                    <div className="text-xs text-[rgb(var(--ink-500))]">
                      {x.created_at ? new Date(x.created_at).toLocaleString() : ""}
                    </div>
                  </div>

                  <div className="mt-3 text-sm font-semibold text-[rgb(var(--ink-900))]">Вопрос</div>
                  <div className="mt-1 whitespace-pre-line text-[rgb(var(--ink-700))]">{x.text}</div>
                  {x.attachments?.some((a) => a.uploader_role === "student") && (
                    <div className="mt-3">
                      <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Файлы студента</div>
                      <ul className="mt-1 space-y-1">
                        {x.attachments
                          .filter((a) => a.uploader_role === "student")
                          .map((file) => (
                            <li key={file.id}>
                              <a
                                href={`${API_BASE}${file.url}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-sm text-[rgb(var(--hse-blue))] hover:underline"
                              >
                                {file.original_name}
                              </a>
                              <span className="ml-2 text-xs text-[rgb(var(--ink-500))]">
                                ({Math.round(file.file_size / 1024)} KB)
                              </span>
                            </li>
                          ))}
                      </ul>
                    </div>
                    )}

                  {x.status === "done" && x.answer ? (
                    <>
                      <div className="mt-4 text-sm font-semibold text-[rgb(var(--ink-900))]">Ответ</div>
                      <div className="mt-1 whitespace-pre-line text-[rgb(var(--ink-700))]">{x.answer}</div>
                                    
                      {x.attachments?.some((a) => a.uploader_role === "staff") && (
                        <div className="mt-3">
                          <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Файлы сотрудника</div>
                          <ul className="mt-1 space-y-1">
                            {x.attachments
                              .filter((a) => a.uploader_role === "staff")
                              .map((file) => (
                                <li key={file.id}>
                                  <a
                                    href={`${API_BASE}${file.url}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-sm text-[rgb(var(--hse-blue))] hover:underline"
                                  >
                                    {file.original_name}
                                  </a>
                                  <span className="ml-2 text-xs text-[rgb(var(--ink-500))]">
                                    ({Math.round(file.file_size / 1024)} KB)
                                  </span>
                                </li>
                              ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="mt-4 text-sm text-[rgb(var(--ink-500))]">
                      Ответ пока не готов. Страница обновляется автоматически.
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
