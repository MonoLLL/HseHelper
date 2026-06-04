export const STUDENT_TOKEN_KEY = "student_token";


export function getStudentToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STUDENT_TOKEN_KEY) || "";
}


export function setStudentToken(token) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STUDENT_TOKEN_KEY, token);
}


export function clearStudentToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STUDENT_TOKEN_KEY);
}


export function authHeaders(token = getStudentToken()) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
