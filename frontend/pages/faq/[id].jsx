import { useRouter } from "next/router";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getClientId } from "../../lib/clientId";

const API_BASE = process.env.NEXT_PUBLIC_API || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function clsx(...xs) {
  return xs.filter(Boolean).join(" ");
}

async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`GET ${url} -> ${r.status} ${t}`);
  }
  return r.json();
}

function IconArrow(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path d="M5 12h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
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

function IconBack(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path d="M19 12H7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path
        d="M11 6l-6 6 6 6"
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
  return <div className={clsx("h-3 rounded-full bg-[rgb(var(--ink-100))] animate-pulse", w)} />;
}

export default function FaqPage() {
  const router = useRouter();
  const { id } = router.query;

  const [loading, setLoading] = useState(true);
  const [faq, setFaq] = useState(null);
  const [err, setErr] = useState("");

  const [incomingLoading, setIncomingLoading] = useState(false);
  const [incomingSent, setIncomingSent] = useState(false);
  const [incomingErr, setIncomingErr] = useState("");

  const questionText = faq?.question || "";

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    setLoading(true);
    setErr("");
    setFaq(null);

    (async () => {
      try {
        const data = await apiGet(`${API_BASE}/api/faq/${id}`);
        if (!cancelled) setFaq(data);
      } catch (e) {
        if (!cancelled) setErr(e?.message || "Не удалось загрузить FAQ");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  async function sendIncoming() {
    setIncomingErr("");
    setIncomingSent(false);

    const text = questionText?.trim();
    if (!text) return;

    setIncomingLoading(true);
    try {
      const formData = new FormData();
      formData.append("text", text);
      formData.append("channel", "site");
      formData.append("client_id", getClientId());

      const r = await fetch(`${API_BASE}/api/incoming`, {
        method: "POST",
        body: formData,
      });

      if (!r.ok) {
        const t = await r.text().catch(() => "");
        throw new Error(`POST ${API_BASE}/api/incoming -> ${r.status} ${t}`);
      }

      await r.json().catch(() => null);
      setIncomingSent(true);
    } catch (e) {
      setIncomingErr(e?.message || "Не удалось отправить вопрос");
    } finally {
      setIncomingLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[rgb(var(--ink-100))]">
      {/* HEADER */}
      <header className="sticky top-0 z-20 border-b border-[rgb(var(--ink-200))] bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-[rgb(var(--hse-blue))] shadow-sm" />
            <div className="leading-tight">
              <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">НИУ ВШЭ · учебный офис</div>
            </div>
          </div>

          <nav className="flex items-center gap-3">
            <Link
              href="/"
              className="
                inline-flex items-center gap-2 rounded-full border border-[rgb(var(--ink-200))]
                bg-white px-3 py-1.5 text-sm text-[rgb(var(--ink-700))]
                hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))]
                transition-colors
                focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                active:scale-[0.98]
              "
            >
              <IconBack className="h-4 w-4" />
              На главную
            </Link>

            <Link
              href="/admin"
              className="
                rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-sm text-[rgb(var(--ink-700))]
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
      <main className="mx-auto max-w-6xl px-6 py-10">
        {/* Breadcrumb */}
        <div className="mb-6 flex items-center gap-2 text-sm text-[rgb(var(--ink-500))]">
          <Link href="/" className="hover:text-[rgb(var(--hse-blue))] transition-colors">
            Главная
          </Link>
          <span>/</span>
          <span className="text-[rgb(var(--ink-700))]">FAQ</span>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* CONTENT */}
          <section className="lg:col-span-8 space-y-6">
            <Card className="p-8">
              <div className="flex flex-wrap items-center gap-3">
                <Pill>FAQ</Pill>
                <span className="text-xs text-[rgb(var(--ink-500))]">Полный ответ</span>
              </div>

              {loading ? (
                <div className="mt-6 space-y-4">
                  <SkeletonLine w="w-3/4" />
                  <SkeletonLine w="w-full" />
                  <SkeletonLine w="w-11/12" />
                  <SkeletonLine w="w-4/5" />
                  <div className="pt-2" />
                  <SkeletonLine w="w-full" />
                  <SkeletonLine w="w-10/12" />
                  <SkeletonLine w="w-9/12" />
                </div>
              ) : err ? (
                <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {err}
                </div>
              ) : (
                <>
                  <h1 className="mt-4 text-2xl font-semibold text-[rgb(var(--ink-900))]">
                    {faq?.question || "—"}
                  </h1>

                  <div className="mt-4 rounded-2xl border border-[rgb(var(--ink-200))] bg-white p-5">
                    <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Короткий ответ</div>
                    <div className="mt-2 whitespace-pre-line text-[rgb(var(--ink-700))]">
                      {faq?.short_answer || "—"}
                    </div>
                  </div>

                  <div className="mt-4 rounded-2xl border border-[rgb(var(--ink-200))] bg-white p-5">
                    <div className="text-sm font-semibold text-[rgb(var(--ink-900))]">Полный ответ</div>
                    <div className="mt-2 whitespace-pre-line text-[rgb(var(--ink-700))]">
                      {faq?.full_answer || faq?.short_answer || "—"}
                    </div>
                  </div>
                </>
              )}
            </Card>
          </section>

          {/* SIDEBAR */}
          <aside className="lg:col-span-4 space-y-6">
            <Card className="p-8">
              <div className="text-sm text-[rgb(var(--ink-500))]">Если ответ не подходит</div>
              <h2 className="mt-1 text-lg font-semibold text-[rgb(var(--ink-900))]">Отправить вопрос</h2>
              <p className="mt-2 text-sm text-[rgb(var(--ink-700))]">
                Мы отправим текущий вопрос в учебный офис. Сотрудник обработает обращение и
                при необходимости добавит новый FAQ.
              </p>

              {incomingErr ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {incomingErr}
                </div>
              ) : null}

              <button
                type="button"
                onClick={sendIncoming}
                disabled={!faq || incomingLoading || incomingSent}
                className={clsx(
                  "mt-5 w-full rounded-2xl px-4 py-3 text-sm font-semibold text-white",
                  "transition-all active:scale-[0.98]",
                  "focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]",
                  incomingSent
                    ? "bg-green-600"
                    : "bg-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-blue2))] shadow-[0_10px_20px_rgba(15,45,105,0.15)] hover:shadow-[0_14px_28px_rgba(15,45,105,0.18)]",
                  (!faq || incomingLoading) && "opacity-60 cursor-not-allowed"
                )}
              >
                {incomingSent ? "Отправлено ✓" : incomingLoading ? "Отправляю…" : "Отправить в учебный офис"}
              </button>

              <div className="mt-4 text-xs text-[rgb(var(--ink-500))]">
                Канал: <span className="font-semibold text-[rgb(var(--ink-700))]">site</span>
              </div>
            </Card>

            <Card className="p-8">
              <div className="text-sm text-[rgb(var(--ink-500))]">Навигация</div>
              <div className="mt-3 space-y-2">
                <Link
                  href="/"
                  className="
                    group flex items-center justify-between rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3
                    hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))]
                    transition-colors
                    focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                    active:scale-[0.99]
                  "
                >
                  <span className="text-sm font-semibold text-[rgb(var(--ink-900))]">Вернуться к поиску</span>
                  <IconArrow className="h-4 w-4 text-[rgb(var(--hse-blue))] opacity-80 group-hover:opacity-100" />
                </Link>

                <Link
                  href="/admin"
                  className="
                    group flex items-center justify-between rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-3
                    hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))]
                    transition-colors
                    focus:outline-none focus:ring-4 focus:ring-[rgb(var(--hse-sky))]
                    active:scale-[0.99]
                  "
                >
                  <span className="text-sm font-semibold text-[rgb(var(--ink-900))]">Перейти в админку</span>
                  <IconArrow className="h-4 w-4 text-[rgb(var(--hse-blue))] opacity-80 group-hover:opacity-100" />
                </Link>
              </div>
            </Card>
          </aside>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="mt-10 border-t border-[rgb(var(--ink-200))] bg-white">
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="text-sm text-[rgb(var(--ink-500))]">
            Учебный офис. Официальные документы и регламенты — на сайте университета.
          </div>
        </div>
      </footer>
    </div>
  );
}
