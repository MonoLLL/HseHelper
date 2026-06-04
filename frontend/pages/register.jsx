import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";

import { authHeaders, clearStudentToken, getStudentToken, setStudentToken } from "../lib/studentAuth";


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


function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-[rgb(var(--ink-700))]">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}


function inputClass(readOnly = false) {
  return clsx(
    "w-full rounded-2xl border border-[rgb(var(--ink-200))] px-4 py-3 text-[rgb(var(--ink-900))] outline-none transition",
    "placeholder:text-[rgb(var(--ink-500))]",
    readOnly
      ? "bg-[rgb(var(--ink-100))] text-[rgb(var(--ink-700))]"
      : "bg-white focus:border-[rgb(var(--hse-blue))] focus:ring-4 focus:ring-[rgb(var(--hse-sky))]"
  );
}


async function apiJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = await response.text().catch(() => "");
  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`);
  }
  return text ? JSON.parse(text) : null;
}


function AuthTabs({ mode, setMode }) {
  return (
    <div className="flex rounded-2xl border border-[rgb(var(--ink-200))] bg-[rgb(var(--ink-100))] p-1">
      {[
        ["register", "Регистрация"],
        ["login", "Вход"],
      ].map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => setMode(key)}
          className={clsx(
            "flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition-colors",
            mode === key
              ? "bg-white text-[rgb(var(--hse-blue))] shadow-sm"
              : "text-[rgb(var(--ink-700))] hover:text-[rgb(var(--hse-blue))]"
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}


export default function RegisterPage() {
  const router = useRouter();
  const [mode, setMode] = useState("register");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [profile, setProfile] = useState(null);

  const [registerForm, setRegisterForm] = useState({
    email: "",
    password: "",
    password2: "",
    full_name: "",
    course: "",
    group_name: "",
  });
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [groupName, setGroupName] = useState("");

  async function loadMe() {
    const token = getStudentToken();
    if (!token) return null;

    const user = await apiJson(`${API_BASE}/api/users/site/me`, {
      headers: authHeaders(token),
    });
    setProfile(user);
    setGroupName(user.group_name || "");
    setMode("profile");
    return user;
  }

  useEffect(() => {
    let alive = true;

    async function run() {
      setLoading(true);
      try {
        const user = await loadMe();
        if (alive && !user) setMode("register");
      } catch {
        clearStudentToken();
        if (alive) setMode("register");
      } finally {
        if (alive) setLoading(false);
      }
    }

    run();
    return () => {
      alive = false;
    };
  }, []);

  function nextPath() {
    return typeof router.query.next === "string" ? router.query.next : "";
  }

  function finishAuth(token, user) {
    setStudentToken(token);
    setProfile(user);
    setGroupName(user.group_name || "");
    const next = nextPath();
    if (next) {
      router.push(next);
    } else {
      setMode("profile");
    }
  }

  async function submitRegistration(e) {
    e.preventDefault();
    setErr("");
    setNotice("");

    const email = registerForm.email.trim().toLowerCase();
    const fullName = registerForm.full_name.trim();
    const course = registerForm.course.trim();
    const group = registerForm.group_name.trim();

    if (!email || !fullName || !course || !group) {
      setErr("Заполните email, ФИО, курс и группу.");
      return;
    }

    if (registerForm.password.length < 8) {
      setErr("Пароль должен быть не короче 8 символов.");
      return;
    }

    if (registerForm.password !== registerForm.password2) {
      setErr("Пароли не совпадают.");
      return;
    }

    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", registerForm.password);
      formData.append("full_name", fullName);
      formData.append("course", course);
      formData.append("group_name", group);

      const result = await apiJson(`${API_BASE}/api/users/site/register`, {
        method: "POST",
        body: formData,
      });

      finishAuth(result.token, result.user);
    } catch (e) {
      setErr(e?.message || "Не удалось зарегистрироваться");
    } finally {
      setSaving(false);
    }
  }

  async function submitLogin(e) {
    e.preventDefault();
    setErr("");
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("email", loginForm.email.trim().toLowerCase());
      formData.append("password", loginForm.password);

      const result = await apiJson(`${API_BASE}/api/users/site/login`, {
        method: "POST",
        body: formData,
      });
      finishAuth(result.token, result.user);
    } catch (e) {
      setErr(e?.message || "Не удалось войти");
    } finally {
      setSaving(false);
    }
  }

  async function updateGroup(e) {
    e.preventDefault();
    setErr("");
    setNotice("");
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("group_name", groupName.trim());

      const user = await apiJson(`${API_BASE}/api/users/site/group`, {
        method: "PATCH",
        headers: authHeaders(),
        body: formData,
      });
      setProfile(user);
      setGroupName(user.group_name || "");
      setNotice("Группа обновлена.");
    } catch (e) {
      setErr(e?.message || "Не удалось обновить группу");
    } finally {
      setSaving(false);
    }
  }

  function logout() {
    clearStudentToken();
    setProfile(null);
    setMode("login");
  }

  return (
    <div className="min-h-screen bg-[rgb(var(--ink-100))]">
      <header className="border-b border-[rgb(var(--ink-200))] bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-4">
          <div>
            <div className="text-xs text-[rgb(var(--ink-500))]">НИУ ВШЭ · учебный офис</div>
            <div className="text-base font-semibold text-[rgb(var(--ink-900))]">
              Аккаунт студента
            </div>
          </div>
          <nav className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end sm:gap-3">
            <Link
              href="/"
              className="flex-1 rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-center text-sm text-[rgb(var(--ink-700))] transition-colors hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))] sm:flex-none"
            >
              На главную
            </Link>
            <Link
              href="/my"
              className="flex-1 rounded-full border border-[rgb(var(--ink-200))] bg-white px-3 py-1.5 text-center text-sm font-semibold text-[rgb(var(--ink-700))] transition-colors hover:border-[rgb(var(--hse-blue))] hover:bg-[rgb(var(--hse-sky))] hover:text-[rgb(var(--hse-blue))] sm:flex-none"
            >
              Мои обращения
            </Link>
          </nav>
        </div>
        <div className="h-1 bg-[rgb(var(--hse-sky))]" />
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <Card className="p-4 sm:p-8">
          {loading ? (
            <div className="text-sm text-[rgb(var(--ink-500))]">Загружаю...</div>
          ) : mode === "profile" && profile ? (
            <>
              <div className="text-sm text-[rgb(var(--ink-500))]">Ваш профиль</div>
              <h1 className="mt-2 text-2xl font-semibold text-[rgb(var(--ink-900))]">
                {profile.full_name}
              </h1>

              <form onSubmit={updateGroup} className="mt-6 grid gap-4 sm:gap-5">
                <Field label="Email">
                  <input value={profile.email || ""} className={inputClass(true)} readOnly />
                </Field>
                <Field label="ФИО">
                  <input value={profile.full_name || ""} className={inputClass(true)} readOnly />
                </Field>
                <Field label="Курс">
                  <input value={profile.course ? `${profile.course}` : ""} className={inputClass(true)} readOnly />
                </Field>
                <Field label="Группа">
                  <input
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    className={inputClass()}
                    placeholder="БПИ221"
                    disabled={saving}
                  />
                </Field>

                {err ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div> : null}
                {notice ? <div className="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{notice}</div> : null}

                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                  <button
                    type="button"
                    onClick={logout}
                    className="w-full rounded-2xl border border-[rgb(var(--ink-200))] bg-white px-4 py-2 text-sm font-semibold text-[rgb(var(--ink-700))] transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700 sm:w-auto"
                  >
                    Выйти
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="w-full rounded-2xl bg-[rgb(var(--hse-blue))] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(15,45,105,0.15)] transition-colors hover:bg-[rgb(var(--hse-blue2))] disabled:opacity-60 sm:w-auto"
                  >
                    {saving ? "Сохраняю..." : "Сохранить группу"}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <AuthTabs mode={mode} setMode={setMode} />

              {mode === "login" ? (
                <form onSubmit={submitLogin} className="mt-6 grid gap-5">
                  <Field label="Email">
                    <input
                      type="email"
                      value={loginForm.email}
                      onChange={(e) => setLoginForm((x) => ({ ...x, email: e.target.value }))}
                      className={inputClass()}
                      placeholder="student@example.com"
                      disabled={saving}
                    />
                  </Field>
                  <Field label="Пароль">
                    <input
                      type="password"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm((x) => ({ ...x, password: e.target.value }))}
                      className={inputClass()}
                      placeholder="Введите пароль"
                      disabled={saving}
                    />
                  </Field>

                  {err ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div> : null}

                  <div className="flex justify-stretch sm:justify-end">
                    <button
                      type="submit"
                      disabled={saving}
                      className="w-full rounded-2xl bg-[rgb(var(--hse-blue))] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(15,45,105,0.15)] transition-colors hover:bg-[rgb(var(--hse-blue2))] disabled:opacity-60 sm:w-auto"
                    >
                      {saving ? "Вхожу..." : "Войти"}
                    </button>
                  </div>
                </form>
              ) : (
                <form onSubmit={submitRegistration} className="mt-6 grid gap-5">
                  <Field label="Email">
                    <input
                      type="email"
                      value={registerForm.email}
                      onChange={(e) => setRegisterForm((x) => ({ ...x, email: e.target.value }))}
                      className={inputClass()}
                      placeholder="student@example.com"
                      disabled={saving}
                    />
                  </Field>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Пароль">
                      <input
                        type="password"
                        value={registerForm.password}
                        onChange={(e) => setRegisterForm((x) => ({ ...x, password: e.target.value }))}
                        className={inputClass()}
                        placeholder="Минимум 8 символов"
                        disabled={saving}
                      />
                    </Field>
                    <Field label="Повтор пароля">
                      <input
                        type="password"
                        value={registerForm.password2}
                        onChange={(e) => setRegisterForm((x) => ({ ...x, password2: e.target.value }))}
                        className={inputClass()}
                        placeholder="Повторите пароль"
                        disabled={saving}
                      />
                    </Field>
                  </div>
                  <Field label="ФИО">
                    <input
                      value={registerForm.full_name}
                      onChange={(e) => setRegisterForm((x) => ({ ...x, full_name: e.target.value }))}
                      className={inputClass()}
                      placeholder="Иванов Иван Иванович"
                      disabled={saving}
                    />
                  </Field>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Курс">
                      <input
                        value={registerForm.course}
                        onChange={(e) => setRegisterForm((x) => ({ ...x, course: e.target.value }))}
                        className={inputClass()}
                        placeholder="2"
                        inputMode="numeric"
                        disabled={saving}
                      />
                    </Field>
                    <Field label="Группа">
                      <input
                        value={registerForm.group_name}
                        onChange={(e) => setRegisterForm((x) => ({ ...x, group_name: e.target.value }))}
                        className={inputClass()}
                        placeholder="БПИ221"
                        disabled={saving}
                      />
                    </Field>
                  </div>

                  {err ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div> : null}

                  <div className="flex justify-stretch sm:justify-end">
                    <button
                      type="submit"
                      disabled={saving}
                      className="w-full rounded-2xl bg-[rgb(var(--hse-blue))] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(15,45,105,0.15)] transition-colors hover:bg-[rgb(var(--hse-blue2))] disabled:opacity-60 sm:w-auto"
                    >
                      {saving ? "Регистрирую..." : "Зарегистрироваться"}
                    </button>
                  </div>
                </form>
              )}
            </>
          )}
        </Card>
      </main>
    </div>
  );
}
