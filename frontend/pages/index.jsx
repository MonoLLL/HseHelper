import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { authHeaders, getStudentToken } from "../lib/studentAuth";

const API_BASE = process.env.NEXT_PUBLIC_API || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const TOPICS = [
  { key: "session", title: "Сессия", hint: "когда зимняя сессия" },
  { key: "payment", title: "Оплата", hint: "срок оплаты обучения" },
  { key: "dorm", title: "Общежитие", hint: "документы для заселения в общежитие" },
  { key: "schedule", title: "Расписание", hint: "где посмотреть расписание занятий" },
];

function clsx(...xs) {
  return xs.filter(Boolean).join(" ");
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

async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`GET ${url} -> ${r.status} ${t}`);
  }
  return r.json();
}

async function loadSiteProfile() {
  const token = getStudentToken();
  if (!token) return null;

  const r = await fetch(`${API_BASE}/api/users/site/me`, {
    headers: authHeaders(token),
  });
  if (r.status === 401 || r.status === 403) return null;
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`GET /api/users/site/me -> ${r.status} ${t}`);
  }
  return r.json();
}

// маленькие иконки без библиотек
function IconSearch(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M16.5 16.5 21 21"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconArrow(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M5 12h12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M13 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Pill({ children }) {
  return (
    <span className="inline-flex items-center rounded-full bg-[rgb(var(--hse-sky))] px-3 py-1 text-xs font-semibold text-[rgb(var(--hse-blue))]">
      {children}
    </span>
  );
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

function SkeletonLine({ w = "w-full" }) {
  return (
    <div
      className={clsx(
        "h-3 rounded-full bg-[rgb(var(--ink-100))] animate-pulse",
        w
      )}
    />
  );
}

function attachmentHref(file) {
  if (!file?.url) return "#";
  return file.url.startsWith("http") ? file.url : `${API_BASE}${file.url}`;
}

function FaqAttachments({ files, compact = false }) {
  if (!files?.length) return null;

  return (
    <div className={clsx("mt-3", compact && "mt-2")}>
      <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">
        &#1042;&#1083;&#1086;&#1078;&#1077;&#1085;&#1080;&#1103;
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {files.map((file) => (
          <a
            key={file.id || file.url || file.original_name}
            href={attachmentHref(file)}
            target="_blank"
            rel="noreferrer"
            className={clsx(
              "inline-flex max-w-full items-center rounded-full border border-[rgb(var(--ink-200))] bg-white",
              "px-3 py-1.5 text-sm font-semibold text-[rgb(var(--hse-blue))]",
              "transition-colors hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))]",
              "focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]"
            )}
          >
            <span className="truncate">{file.original_name || "file"}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);

  const top = items?.[0] || null;
  const alternatives = useMemo(() => (items || []).slice(1, 5), [items]);

  useEffect(() => {
    let alive = true;

    async function loadProfile() {
      setProfileLoading(true);
      try {
        const user = await loadSiteProfile();
        if (alive) setProfile(user);
      } catch {
        if (alive) setProfile(null);
      } finally {
        if (alive) setProfileLoading(false);
      }
    }

    loadProfile();
    return () => {
      alive = false;
    };
  }, []);

  async function search(text) {
    const query = (text ?? "").trim();
    setErr("");
    setSubmitted(false);

    if (!query) {
      setItems([]);
      return;
    }

    setLoading(true);
    try {
      const data = await apiGet(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setErr(e?.message || "Ошибка запроса");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function submitIncoming() {
    const query = (q ?? "").trim();
    if (!query) return;

    if (!profile) {
      router.push("/register?next=/");
      return;
    }

    setErr("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("text", query);
      formData.append("channel", "site");

      for (const file of selectedFiles) {
        formData.append("files", file);
      }

      const r = await fetch(`${API_BASE}/api/incoming`, {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });

      if (!r.ok) {
        const t = await r.text().catch(() => "");
        throw new Error(`POST /api/incoming -> ${r.status} ${t}`);
      }

      await r.json().catch(() => null);
      setSubmitted(true);
      setSelectedFiles([]);
    } catch (e) {
      setErr(e?.message || "Не удалось отправить вопрос");
    } finally {
      setLoading(false);
    }
  }

  function onTopic(t) {
    setQ(t.hint);
    search(t.hint);
  }

  function onFilesChange(e) {
    const nextFiles = Array.from(e.target.files || []);
    setSelectedFiles((current) => mergeFiles(current, nextFiles));
    e.target.value = "";
  }

  function removeSelectedFile(fileToRemove) {
    setSelectedFiles((current) =>
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
    <div className="min-h-screen bg-[rgb(var(--ink-100))]">
      {/* HEADER */}
      <header className="sticky top-0 z-20 border-b border-[rgb(var(--ink-200))] bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6 sm:px-6 sm:py-4">
          <div className="flex w-full min-w-0 items-center gap-3 sm:w-auto">
            <div className="h-9 w-9 flex-none rounded-full bg-[rgb(var(--hse-blue))] shadow-sm sm:h-10 sm:w-10" />
            <div className="leading-tight">
              <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">НИУ ВШЭ · учебный офис</div>
            </div>
          </div>

          <nav className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end sm:gap-3">
            <Link
              href="/register"
              className="
                flex-1 rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-center text-sm font-semibold text-[rgb(var(--ink-700))] sm:flex-none
                hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                transition-colors
                active:scale-[0.98]
                "
            >
              {profile ? "Профиль" : "Регистрация/Вход"}
            </Link>
            {profile ? (
              <Link
                href="/my"
                className="
                  flex-1 rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-center text-sm font-semibold text-[rgb(var(--ink-700))] sm:flex-none
                  hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                  transition-colors
                  active:scale-[0.98]
                  "
              >
                Мои обращения
              </Link>
            ) : null}

            <Link
              href="/admin"
              className="
                flex-1 rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-center text-sm text-[rgb(var(--ink-700))] sm:flex-none
                hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                transition-colors
                focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                active:scale-[0.98]
              "
            >
              Админка
            </Link>
          </nav>
        </div>
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
      </header>

      {/* MAIN */}
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <div className="grid grid-cols-1 gap-5 sm:gap-8 lg:grid-cols-12">
          {/* LEFT */}
          <section className="lg:col-span-7 space-y-6">
            {/* HERO + SEARCH */}
            <Card className="p-4 sm:p-8">
              <div className="mb-4 rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3">
                {profileLoading ? (
                  <div className="text-sm text-[rgb(var(--ink-500))]">Проверяю регистрацию...</div>
                ) : profile ? (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="text-xs text-[rgb(var(--ink-500))]">Вы вошли как студент</div>
                      <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">
                        {profile.full_name}
                      </div>
                    </div>
                    <Link
                      href="/register"
                      className="rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm font-semibold text-[rgb(var(--hse-blue))] transition-colors hover:bg-[rgb(var(--hse-sky))]"
                    >
                      Изменить
                    </Link>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-sm text-[rgb(var(--ink-700))]">
                      Для отправки обращений нужно зарегистрироваться.
                    </div>
                    <Link
                      href="/register"
                      className="rounded-full bg-[rgb(var(--hse-blue))] px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-[rgb(var(--hse-blue2))]"
                    >
                      Зарегистрироваться
                    </Link>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Pill>Справочник для студентов</Pill>
                <span className="text-xs text-[rgb(var(--ink-500))]">
                  Быстрые ответы без обращений в учебный офис
                </span>
              </div>

              <h1 className="mt-3 text-2xl font-semibold text-[rgb(var(--ink-900))] sm:text-3xl">
                Быстрый поиск информации
              </h1>
              <p className="mt-3 text-[rgb(var(--ink-700))]">
                Напиши вопрос - система найдёт готовый ответ. Если точного ответа нет, отправь
                обращение в учебный офис.
              </p>

              <form
                className="mt-6"
                onSubmit={(e) => {
                  e.preventDefault();
                  search(q);
                }}
              >
                <label className="block text-sm font-medium text-[rgb(var(--ink-700))]">
                  Вопрос
                </label>

                <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                  <div className="relative w-full">
                    <IconSearch className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[rgb(var(--ink-500))]" />
                    <input
                      className="
                        w-full rounded-2xl border border-[rgb(var(--ink-200))] bg-white py-3 pl-11 pr-4
                        text-[rgb(var(--ink-900))] outline-none
                        placeholder:text-[rgb(var(--ink-500))]
                        focus:border-[rgb(var(--hse-blue))] focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                        transition
                      "
                      placeholder='Например: "Когда начинается зимняя сессия?"'
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                    />
                  </div>

                  <button
                    type="submit"
                    className={clsx(
                      "inline-flex w-full items-center justify-center gap-2 whitespace-nowrap rounded-2xl px-5 py-3 text-sm font-semibold text-white sm:w-auto sm:flex-none",
                      "bg-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-blue2))]",
                      "shadow-[0_10px_20px_rgba(15,45,105,0.18)] hover:shadow-[0_14px_28px_rgba(15,45,105,0.20)]",
                      "transition-all active:scale-[0.98]",
                      "focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]",
                      loading && "opacity-60 cursor-not-allowed"
                    )}
                    disabled={loading}
                  >
                    Найти
                    <IconArrow className="h-5 w-5" />
                  </button>
                </div>

                {/* TOPIC CHIPS */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {TOPICS.map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => onTopic(t)}
                      className="
                        rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm text-[rgb(var(--ink-700))]
                        hover:border-[rgb(var(--hse-blue))] hover:text-[rgb(var(--hse-blue))]
                        hover:bg-[rgb(var(--hse-sky))]
                        transition-colors
                        active:scale-[0.98]
                        focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                      "
                    >
                      {t.title}
                    </button>
                  ))}
                </div>

                {/* FILES */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-[rgb(var(--ink-700))]">
                    Файлы к вопросу
                  </label>
                  <input
                    type="file"
                    multiple
                    accept=".png,.jpg,.jpeg,.webp,.pdf,.doc,.docx,.xls,.xlsx"
                    onChange={onFilesChange}
                    className="
                      mt-2 block w-full rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3
                      text-sm text-transparent
                      file:mr-4 file:rounded-full file:border-0
                      file:bg-[rgb(var(--hse-sky))] file:px-3 file:py-2
                      file:text-sm file:font-semibold file:text-[rgb(var(--hse-blue))]
                      hover:file:bg-[rgb(var(--ink-100))]
                      focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                    "
                  />
                  {selectedFiles.length > 0 && (
                    <div className="mt-2 space-y-2">
                      <div className="text-sm text-[rgb(var(--ink-500))]">
                        Выбрано файлов: {selectedFiles.length}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedFiles.map((file) => (
                          <button
                            key={`${file.name}-${file.size}-${file.lastModified}`}
                            type="button"
                            onClick={() => removeSelectedFile(file)}
                            className="
                              rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-xs
                              text-[rgb(var(--ink-700))] transition-colors
                              hover:border-red-300 hover:bg-red-50 hover:text-red-700
                            "
                          >
                            {file.name} x
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* ERROR */}
                {err ? (
                  <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {err}
                  </div>
                ) : null}
              </form>
            </Card>

            {/* RESULT */}
            <Card className="p-4 transition-colors hover:border-[rgb(var(--hse-blue))] sm:p-8">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                <div>
                  <div className="text-sm text-[rgb(var(--ink-500))]">Результат</div>
                  <h2 className="mt-1 text-xl font-semibold text-[rgb(var(--ink-900))]">
                    {loading ? "Ищу ответ…" : top ? "Найден ответ" : "Пока нет ответа"}
                  </h2>
                </div>
                {top ? <Pill>Совпадение</Pill> : null}
              </div>

              {/* LOADING SKELETON */}
              {loading ? (
                <div className="mt-5 space-y-3">
                  <SkeletonLine w="w-2/3" />
                  <SkeletonLine w="w-full" />
                  <SkeletonLine w="w-11/12" />
                  <SkeletonLine w="w-4/5" />
                </div>
              ) : top ? (
                <div className="mt-5">
                  <div className="text-base font-semibold text-[rgb(var(--ink-900))]">
                    {top.question}
                  </div>
                  <div className="mt-2 whitespace-pre-line text-[rgb(var(--ink-700))]">
                    {top.full_answer || top.short_answer || "-"}
                  </div>
                  <FaqAttachments files={top.attachments} />
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <span className="text-xs text-[rgb(var(--ink-500))]">
                      Если ответ не подходит - отправь вопрос в учебный офис.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="mt-5 text-[rgb(var(--ink-700))]">
                  Попробуй уточнить формулировку или выбери тему выше. Если вопрос уникальный -
                  отправь его в учебный офис.
                </div>
              )}

              {/* ALTERNATIVES */}
              {!loading && alternatives.length > 0 ? (
                <div className="mt-7">
                  <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">
                    Похожие ответы
                  </div>
                  <div className="mt-3 grid gap-3">
                    {alternatives.map((x) => (
                      <div
                        key={x.id}
                        className="
                          group rounded-2xl border border-[rgb(var(--ink-200))] bg-white p-4
                          hover:border-[rgb(var(--hse-blue))] hover:shadow-[0_10px_30px_rgba(17,24,39,0.07)]
                          transition-all
                        "
                      >
                        <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">
                          {x.question}
                        </div>
                        <div className="mt-1 whitespace-pre-line text-sm text-[rgb(var(--ink-700))]">
                          {x.full_answer || x.short_answer || ""}
                        </div>
                        <FaqAttachments files={x.attachments} compact />
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* SEND INCOMING */}
              <div className="mt-7 flex flex-col items-stretch gap-3 rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-[rgb(var(--ink-700))]">
                  Не нашёл ответ? Отправим вопрос в учебный офис.
                </div>

                <button
                  type="button"
                  onClick={submitIncoming}
                  disabled={!q.trim() || loading || submitted || profileLoading}
                  className={clsx(
                    "w-full rounded-2xl px-4 py-2 text-sm font-semibold sm:w-auto",
                    "transition-all active:scale-[0.98]",
                    "focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]",
                    submitted
                      ? "bg-green-600 text-white"
                      : "bg-[rgb(var(--hse-blue))] text-white hover:bg-[rgb(var(--hse-blue2))] shadow-[0_10px_20px_rgba(15,45,105,0.15)] hover:shadow-[0_14px_28px_rgba(15,45,105,0.18)]",
                    (!q.trim() || loading || profileLoading) && "opacity-60 cursor-not-allowed"
                  )}
                >
                  {submitted ? "Отправлено ✓" : profile ? "Отправить" : "Зарегистрироваться"}
                </button>
              </div>
            </Card>
          </section>

          {/* RIGHT */}
          <aside className="lg:col-span-5 space-y-6">
            <Card className="p-4 sm:p-8">
              <div className="text-sm text-[rgb(var(--ink-500))]">Как это работает</div>
              <h3 className="mt-1 text-xl font-semibold text-[rgb(var(--ink-900))]">
                Просто и быстро
              </h3>

              <ol className="mt-4 space-y-3 text-[rgb(var(--ink-700))]">
                {[
                  "Введи вопрос или выбери тему.",
                  "Система найдёт подходящий FAQ и покажет ответ.",
                  "Если ответа нет - вопрос уйдёт сотруднику учебного офиса и будет обработан.",
                ].map((t, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="mt-0.5 inline-flex h-7 w-7 flex-none items-center justify-center rounded-full bg-[rgb(var(--hse-sky))] text-sm font-semibold text-[rgb(var(--hse-blue))]">
                      {i + 1}
                    </span>
                    <span>{t}</span>
                  </li>
                ))}
              </ol>

              <div className="mt-6 rounded-2xl border border-[rgb(var(--ink-200))] bg-white p-4">
                <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Совет</div>
                <div className="mt-1 text-sm text-[rgb(var(--ink-700))]">
                  Формулируй коротко: <span className="font-semibold">“срок оплаты”</span>,{" "}
                  <span className="font-semibold">“зимняя сессия”</span>,{" "}
                  <span className="font-semibold">“общежитие документы”</span>.
                </div>
              </div>
            </Card>

            <Card className="p-4 sm:p-8">
              <div className="text-sm text-[rgb(var(--ink-500))]">Доступ</div>
              <div className="mt-2 text-sm text-[rgb(var(--ink-700))]">
                Для сотрудников учебного офиса предусмотрена админ-панель для пополнения базы
                “вопрос-ответ”.
              </div>

              <div className="mt-4">
                <Link
                  href="/admin"
                  className="
                    inline-flex items-center gap-2 rounded-2xl bg-white px-4 py-2 text-sm font-semibold
                    border border-[rgb(var(--ink-200))] text-[rgb(var(--hse-blue))]
                    hover:bg-[rgb(var(--hse-sky))] hover:border-[rgb(var(--hse-blue))]
                    transition-colors
                    focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                    active:scale-[0.98]
                  "
                >
                  Перейти в админку <IconArrow className="h-4 w-4" />
                </Link>
              </div>
            </Card>
          </aside>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="mt-10 border-t border-[rgb(var(--ink-200))] bg-white">
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
          <div className="text-sm text-[rgb(var(--ink-500))]">
            Учебный офис. Официальные документы и регламенты - на сайте университета.
          </div>
        </div>
      </footer>
    </div>
  );
}
